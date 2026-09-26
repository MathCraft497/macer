from typing import Dict, List, Optional

from . import ast_nodes as ast
from .diagnostics import (
    DiagnosticBag, MacerCompileError, Diagnostic, Span, Severity, ErrCode,
)

CHAR_METHODS = {
    "toInt": ([], "Int"),
    "toString": ([], "String"),
    "toUpper": ([], "Char"),
    "toLower": ([], "Char"),
}
PRIMITIVES = {"Int", "Float", "Bool", "Void", "Any", "Char"}
NUMERIC = {"Int", "Float"}
PSEUDO_TYPES = PRIMITIVES | {"func"}

# 运算符 key
OP_KEYS = {"opr+", "opr-", "opr*", "opr/",
           "opr==", "opr!=", "opr<", "opr>", "opr()"}
BIN_OP_MAP = {"+": "opr+", "-": "opr-", "*": "opr*", "/": "opr/",
              "==": "opr==", "!=": "opr!=", "<": "opr<", ">": "opr>"}


class Symbol:
    def __init__(self, name, type_node, mutable, kind="var",
                 owner=None, line=0):
        self.name = name
        self.type = type_node
        self.mutable = mutable
        self.kind = kind
        self.owner = owner
        self.line = line
        self.func_sig = None


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.symbols = {}

    def define(self, sym):
        self.symbols[sym.name] = sym

    def lookup(self, name):
        s = self
        while s:
            if name in s.symbols:
                return s.symbols[name]
            s = s.parent
        return None

    def lookup_local(self, name):
        return self.symbols.get(name)


class ClassInfo:
    def __init__(self, decl, package):
        self.decl = decl
        self.name = decl.name
        self.package = package
        self.fqn = f"{package}.{decl.name}" if package else decl.name
        self.parent_simple = decl.parent
        self.parent_fqn = None
        self.fields = {f.name: f for f in decl.fields}
        # name → [FuncDecl, ...]（多个同名方法）
        self.methods = {}
        for m in decl.methods:
            self.methods.setdefault(m.name, []).append(m)

        # 运算符重载
        self.operators = {}
        # overload 声明：方法名 → [FuncDecl]
        self.overloads = {}
        for m in decl.methods:
            if getattr(m, "operator", None):
                self.operators[m.operator] = m
            if getattr(m, "overload", False):
                self.overloads.setdefault(m.name, []).append(m)

    def find_field(self, name, classes):
        if name in self.fields:
            return self.fields[name]
        if self.parent_fqn and self.parent_fqn in classes:
            return classes[self.parent_fqn].find_field(name, classes)
        return None

    def find_method(self, name, classes, n_args=None):
        """找方法——按名字 + 可选参数个数"""
        candidates = self.methods.get(name, [])
        if n_args is None:
            # 不指定参数个数——返回第一个（兼容旧调用）
            if candidates:
                return candidates[0]
        else:
            # 精确匹配参数个数
            for m in candidates:
                if len(m.params) == n_args:
                    return m
        # 父类
        if self.parent_fqn and self.parent_fqn in classes:
            return classes[self.parent_fqn].find_method(
                name, classes, n_args)
        return None

    def find_operator(self, op_key, classes):
        if op_key in self.operators:
            return self.operators[op_key]
        if self.parent_fqn and self.parent_fqn in classes:
            return classes[self.parent_fqn].find_operator(op_key, classes)
        return None

    def is_subclass_of(self, fqn, classes):
        if self.fqn == fqn:
            return True
        if self.parent_fqn and self.parent_fqn in classes:
            return classes[self.parent_fqn].is_subclass_of(fqn, classes)
        return False


class TypeChecker:
    def __init__(self, units, basic_lib=None, filename="<source>", bag=None):
        self.units = units
        self.filename = filename
        self.bag = bag if bag is not None else DiagnosticBag()
        self.basic_lib = basic_lib or {}
        self.classes = {}
        self.functions = {}
        self.global_scope = Scope()
        self.current_unit = None
        self.current_class = None
        self.current_func = None
        self.return_type_stack = []

    def _err(self, code, msg, node=None, note=None, note_node=None):
        span = None
        note_span = None
        if node is not None:
            line = getattr(node, "line", 0) or 1
            col = getattr(node, "col", 0) or 1
            span = Span(line, col, line, col + 1)
        diag = Diagnostic(
            code=code, severity=Severity.ERROR, message=msg,
            span=span, filename=self.filename,
            note=note, note_span=note_span,
        )
        self.bag.add(diag)
        raise MacerCompileError(diag)

    def _normalize_type(self, t):
        if t is None:
            return ast.TypeNode("Any")
        if t.name in PSEUDO_TYPES:
            return t
        if t.is_array:
            # 元素类型归一化，数组本身保留
            inner = self._normalize_type(
                ast.TypeNode(t.name, t.generics))
            return ast.TypeNode(inner.name, inner.generics,
                                is_array=True, array_dims=t.array_dims)
        if t.name in self.classes:
            return ast.TypeNode(t.name, t.generics)
        ci = self._resolve_class(t.name, self.current_unit)
        if ci is not None:
            return ast.TypeNode(ci.fqn, t.generics)
        return t

    def is_assignable(self, target, source):
        target = self._normalize_type(target)
        source = self._normalize_type(source)
        # 数组：元素类型相容，且维度相同
        if target.is_array or source.is_array:
            if target.is_array != source.is_array:
                return False
            if target.array_dims != source.array_dims:
                return False
            t_elem = ast.TypeNode(target.name, target.generics)
            s_elem = ast.TypeNode(source.name, source.generics)
            return self.is_assignable(t_elem, s_elem)
        t, s = str(target), str(source)
        if t == s or t == "Any" or s == "Any":
            return True
        if t == "Float" and s == "Int":
            return True
        if s in self.classes and t in self.classes:
            return self.classes[s].is_subclass_of(t, self.classes)
        return False

    def _resolve_class(self, name, unit):
        if unit and name in unit.symbol_table:
            entry = unit.symbol_table[name]
            if isinstance(entry, ClassInfo):
                return entry
        if name in self.classes:
            return self.classes[name]
        if unit and unit.package:
            fqn = f"{unit.package}.{name}"
            if fqn in self.classes:
                return self.classes[fqn]
        return None

    def _resolve_function(self, name, unit):
        if unit and unit.package:
            fqn = f"{unit.package}.{name}"
            if fqn in self.functions:
                return self.functions[fqn]
        if name in self.functions:
            return self.functions[name]
        for fqn, fn in self.functions.items():
            if fqn.endswith("." + name) or fqn == name:
                return fn
        return None

    def _resolve_parent(self, parent_name, ci):
        if parent_name in self.classes:
            return self.classes[parent_name]
        if ci.package:
            fqn = f"{ci.package}.{parent_name}"
            if fqn in self.classes:
                return self.classes[fqn]
        candidates = [c for c in self.classes.values() if c.name == parent_name]
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _find_symbol_in_package(self, name, package, unit):
        fqn = f"{package}.{name}"
        if fqn in self.classes:
            return self.classes[fqn]
        if fqn in self.functions:
            return self.functions[fqn]
        for u in self.units:
            if u.package != package:
                continue
            for d in u.program.declarations:
                if isinstance(d, ast.ClassDecl) and d.name == name:
                    fq = f"{package}.{d.name}"
                    if fq in self.classes:
                        return self.classes[fq]
                elif isinstance(d, ast.FuncDecl) and d.name == name:
                    fq = f"{package}.{d.name}"
                    if fq in self.functions:
                        return self.functions[fq]
        candidates = [c for c in self.classes.values() if c.name == name]
        candidates += [f for f in self.functions.values() if f.name == name]
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _import_package_all(self, package, table, unit):
        prefix = package + "."
        found = False
        for fqn, ci in self.classes.items():
            if fqn.startswith(prefix) and "." not in fqn[len(prefix):]:
                table[ci.name] = ci
                found = True
        for fqn, fn in self.functions.items():
            if fqn.startswith(prefix) and "." not in fqn[len(prefix):]:
                table[fn.name] = fn
                found = True
        if not found:
            self._err(ErrCode.PKG_NOT_FOUND,
                      f"包 '{package}' 中没有任何声明", None)

    def check(self):
        # 收集
        for unit in self.units:
            pkg = unit.package
            for d in unit.program.declarations:
                if isinstance(d, ast.ClassDecl):
                    ci = ClassInfo(d, pkg)
                    if ci.fqn in self.classes:
                        self._err(ErrCode.PKG_DUPLICATE_CLASS,
                                  f"重复定义的类 '{ci.fqn}'", d)
                    self.classes[ci.fqn] = ci
                elif isinstance(d, ast.FuncDecl):
                    fqn = f"{pkg}.{d.name}" if pkg else d.name
                    self.functions[fqn] = d

        # 2. 解析父类 FQN；无父类的类隐式继承 macer.lang.Object
        OBJECT_FQN = "macer.lang.Object"

        # 先确认 Object 存在
        has_object = OBJECT_FQN in self.classes

        for ci in self.classes.values():
            # Object 自己不继承任何类
            if ci.fqn == OBJECT_FQN:
                ci.parent_fqn = None
                continue

            if ci.parent_simple:
                parent = self._resolve_parent(ci.parent_simple, ci)
                if parent is None:
                    self._err(
                        ErrCode.TYPE_NOT_CLASS,
                        f"类 '{ci.fqn}' 的父类 '{ci.parent_simple}' 不存在",
                        ci.decl,
                    )
                ci.parent_fqn = parent.fqn
            elif has_object:
                # 隐式继承
                ci.parent_fqn = OBJECT_FQN

        for unit in self.units:
            self._register_unit_symbols(unit)

        STRING_FQN = "macer.lang.String"
        for name, (params, ret) in self.basic_lib.items():
            if name == "str" and STRING_FQN in self.classes:
                ret = ast.TypeNode(STRING_FQN)
            sym = Symbol(name, ast.TypeNode("func"), False, "func")
            sym.func_sig = (params, ret)
            self.global_scope.symbols[name] = sym

        for unit in self.units:
            self._check_unit(unit)

    def _register_unit_symbols(self, unit):
        table = {}

        # 0. ★ 自动注入 macer.lang.* 的所有符号
        LANG_PREFIX = "macer.lang."
        for fqn, ci in self.classes.items():
            if fqn.startswith(LANG_PREFIX):
                rest = fqn[len(LANG_PREFIX):]
                if "." not in rest:
                    table[ci.name] = ci
        for fqn, fn in self.functions.items():
            if fqn.startswith(LANG_PREFIX):
                rest = fqn[len(LANG_PREFIX):]
                if "." not in rest:
                    table[fn.name] = fn

        # 1. 本包内的类与函数
        for d in unit.program.declarations:
            if isinstance(d, ast.ClassDecl):
                fqn = f"{unit.package}.{d.name}" if unit.package else d.name
                if fqn in self.classes:
                    table[d.name] = self.classes[fqn]
            elif isinstance(d, ast.FuncDecl):
                fqn = f"{unit.package}.{d.name}" if unit.package else d.name
                if fqn in self.functions:
                    table[d.name] = self.functions[fqn]

        for imp in unit.program.imports:
            if imp.names:
                for name in imp.names:
                    fqn = f"{imp.module}.{name}"
                    if fqn in self.classes:
                        table[name] = self.classes[fqn]
                    elif fqn in self.functions:
                        table[name] = self.functions[fqn]
                    else:
                        resolved = self._find_symbol_in_package(
                            name, imp.module, unit)
                        if resolved is not None:
                            table[name] = resolved
                        else:
                            self._err(ErrCode.PKG_BAD_IMPORT,
                                      f"导入的 '{fqn}' 不存在", imp)
            elif imp.is_wildcard:
                self._import_package_all(imp.module, table, unit)
            else:
                module = imp.module
                if module in self.classes:
                    ci = self.classes[module]
                    table[imp.alias or ci.name] = ci
                    continue
                if module in self.functions:
                    fn = self.functions[module]
                    table[imp.alias or fn.name] = fn
                    continue
                prefix = module + "."
                found_any = False
                for fqn, ci in self.classes.items():
                    if fqn.startswith(prefix) and "." not in fqn[len(prefix):]:
                        table[ci.name] = ci
                        found_any = True
                for fqn, fn in self.functions.items():
                    if fqn.startswith(prefix) and "." not in fqn[len(prefix):]:
                        table[fn.name] = fn
                        found_any = True
                if not found_any:
                    parts = module.split(".")
                    if len(parts) >= 2:
                        parent = ".".join(parts[:-1])
                        leaf = parts[-1]
                        resolved = self._find_symbol_in_package(
                            leaf, parent, unit)
                        if resolved is not None:
                            table[imp.alias or leaf] = resolved
                            found_any = True
                if not found_any:
                    self._err(ErrCode.PKG_NOT_FOUND,
                              f"导入的 '{module}' 既不是类也不是包", imp)
        unit.symbol_table = table

    def _check_unit(self, unit):
        prev = self.current_unit
        self.current_unit = unit
        for d in unit.program.declarations:
            if isinstance(d, ast.ClassDecl):
                fqn = f"{unit.package}.{d.name}" if unit.package else d.name
                if fqn in self.classes:
                    self._check_class(self.classes[fqn])
            elif isinstance(d, ast.FuncDecl):
                self._check_func(d, owner=None)
        self.current_unit = prev

    def _check_char_method(self, name, args, scope, node):
        if name not in CHAR_METHODS:
            self._err(ErrCode.TYPE_NO_METHOD,
                      f"Char 没有方法 '{name}'", node)
        param_types, ret = CHAR_METHODS[name]
        if len(param_types) != len(args):
            self._err(ErrCode.TYPE_ARG_COUNT,
                      f"Char.{name} 需要 {len(param_types)} 个参数", node)
        return ast.TypeNode(ret)

    def _check_class(self, cls):
        prev = self.current_class
        self.current_class = cls
        for f in cls.decl.fields:
            if f.init is not None:
                scope = Scope(self.global_scope)
                for field in cls.decl.fields:
                    scope.define(Symbol(
                        field.name,
                        self._normalize_type(field.type_node),
                        True, "field", line=field.line))
                scope.define(Symbol("self", ast.TypeNode(cls.fqn), False, "self"))
                it = self.infer(f.init, scope)
                declared = self._normalize_type(f.type_node)
                if not self.is_assignable(declared, it):
                    self._err(ErrCode.TYPE_MISMATCH,
                              f"字段 '{cls.fqn}.{f.name}' 初始化类型不匹配："
                              f"{it} 无法赋给 {f.type_node}", f)
        for m in cls.decl.methods:
            self._check_func(m, owner=cls)
        self.current_class = prev

    def _check_func(self, fn, owner):
        # 声明式函数跳过
        if not fn.body:
            return

        # 运算符方法特殊检查
        if getattr(fn, "operator", None):
            self._check_operator_func(fn, owner)

        seen = set()
        for p in fn.params:
            if p.name in seen:
                self._err(ErrCode.TYPE_DUPLICATE,
                          f"函数 '{fn.name}' 参数 '{p.name}' 重复", fn)
            seen.add(p.name)

        scope = Scope(self.global_scope)
        if owner is not None:
            scope.define(Symbol("self", ast.TypeNode(owner.fqn), False, "self"))
        for p in fn.params:
            scope.define(Symbol(p.name,
                                self._normalize_type(p.type_node),
                                False, "param", line=fn.line))

        prev_func = self.current_func
        self.current_func = fn
        self.return_type_stack.append(self._normalize_type(fn.return_type))
        try:
            self._check_block(fn.body, scope)
        finally:
            self.return_type_stack.pop()
            self.current_func = prev_func

    def _check_operator_func(self, fn, owner):
        """校验运算符方法的签名"""
        op = fn.operator
        if op in ("get.opr", "set.opr"):
            if len(fn.params) < 1:
                self._err(ErrCode.TYPE_ARG_COUNT,
                          f"'{op}' 至少需要 1 个参数（索引字符串）", fn)
            p0 = self._normalize_type(fn.params[0].type_node)
            # 接受 Any / String / macer.lang.String
            is_string = (
                    p0.name in ("Any", "String") or
                    p0.name == "macer.lang.String" or
                    (p0.name in self.classes and
                     self.classes[p0.name].name == "String")
            )
            if not is_string:
                self._err(ErrCode.TYPE_MISMATCH,
                          f"'{op}' 的第一个参数必须是 String", fn)
            if op == "set.opr" and len(fn.params) != 2:
                self._err(ErrCode.TYPE_ARG_COUNT,
                          f"set.opr 需要 2 个参数", fn)
        elif op in OP_KEYS:
            if len(fn.params) != 1:
                self._err(ErrCode.TYPE_ARG_COUNT,
                          f"运算符 '{op}' 需要 1 个参数", fn)

    def _check_block(self, stmts, scope):
        for s in stmts:
            self._check_stmt(s, scope)

    def _check_stmt(self, s, scope):
        if isinstance(s, ast.VarDecl):
            declared_type = self._normalize_type(s.type_node)
            if s.init is not None:
                it = self.infer(s.init, scope)
                if not self.is_assignable(declared_type, it):
                    self._err(ErrCode.TYPE_MISMATCH,
                              f"变量 '{s.name}' 初始化类型不匹配："
                              f"{it} 无法赋给 {s.type_node}", s)
            elif declared_type.name not in ("Any",):
                self._err(ErrCode.TYPE_MISMATCH,
                          f"变量 '{s.name}' 需要初始化"
                          f"（类型 {s.type_node} 不允许默认值）", s)
            existing = scope.lookup_local(s.name)
            if existing:
                self._err(ErrCode.TYPE_DUPLICATE,
                          f"重复定义 '{s.name}'", s,
                          note=f"'{s.name}' 上一次声明在第 {existing.line} 行",
                          note_node=ast.IntLit(0, existing.line, 1))
            scope.define(Symbol(s.name, declared_type, s.mutable, "var",
                                line=s.line))
        elif isinstance(s, ast.ExprStmt):
            self.infer(s.expr, scope)
        elif isinstance(s, ast.ReturnStmt):
            want = self.return_type_stack[-1]
            if s.value is None:
                if want.name != "Void":
                    self._err(ErrCode.TYPE_RETURN_MISMATCH,
                              f"函数 '{self.current_func.name}' 应返回 {want}，"
                              f"但 return 没有值", s)
            else:
                it = self.infer(s.value, scope)
                if not self.is_assignable(want, it):
                    self._err(ErrCode.TYPE_RETURN_MISMATCH,
                              f"函数 '{self.current_func.name}' 返回类型不匹配："
                              f"{it} 无法赋给 {want}", s)
        elif isinstance(s, ast.IfStmt):
            it = self.infer(s.cond, scope)
            self._expect_bool(it, s.cond)
            self._check_block(s.then_body, Scope(scope))
            if s.else_body:
                self._check_block(s.else_body, Scope(scope))
        elif isinstance(s, ast.WhileStmt):
            it = self.infer(s.cond, scope)
            self._expect_bool(it, s.cond)
            self._check_block(s.body, Scope(scope))
        elif isinstance(s, ast.Block):
            self._check_block(s.body, Scope(scope))
        else:
            self._err(ErrCode.TYPE_MISMATCH,
                      f"未知语句类型: {type(s).__name__}", s)

    def _expect_bool(self, t, node):
        t = self._normalize_type(t)
        if t.name not in ("Bool", "Any"):
            self._err(ErrCode.TYPE_COND_NOT_BOOL,
                      f"条件表达式必须为 Bool，实际为 {t}", node)

    def infer(self, e, scope):
        if isinstance(e, ast.IntLit):
            return ast.TypeNode("Int")
        if isinstance(e, ast.FloatLit):
            return ast.TypeNode("Float")
        if isinstance(e, ast.StringLit):
            # 返回 macer.lang.String 类的 FQN
            ci = self._resolve_class("String", self.current_unit)
            if ci is not None:
                return ast.TypeNode(ci.fqn)
            return ast.TypeNode("String")
        if isinstance(e, ast.BoolLit):
            return ast.TypeNode("Bool")
        if isinstance(e, ast.NullLit):
            return ast.TypeNode("Any")

        if isinstance(e, ast.CharLit):
            return ast.TypeNode("Char")

        if isinstance(e, ast.ArrayLit):
            if not e.elements:
                return ast.TypeNode("Any", is_array=True, array_dims=1)
            elem_t = self.infer(e.elements[0], scope)
            for el in e.elements[1:]:
                et = self.infer(el, scope)
                if not (self.is_assignable(elem_t, et) or
                        self.is_assignable(et, elem_t)):
                    self._err(ErrCode.TYPE_MISMATCH,
                              f"数组元素类型不一致：{elem_t} vs {et}", e)
                if et.name == "Float" and elem_t.name == "Int":
                    elem_t = ast.TypeNode("Float")
            return ast.TypeNode(elem_t.name, elem_t.generics,
                                is_array=True, array_dims=1)

        if isinstance(e, ast.Ident):
            sym = scope.lookup(e.name)
            if sym is not None:
                if sym.kind == "func":
                    return ast.TypeNode("func")
                return self._normalize_type(sym.type)
            unit = self.current_unit
            if unit and e.name in unit.symbol_table:
                entry = unit.symbol_table[e.name]
                if isinstance(entry, ClassInfo):
                    return ast.TypeNode(entry.fqn)
                if isinstance(entry, ast.FuncDecl):
                    return ast.TypeNode("func")
            fn = self._resolve_function(e.name, unit)
            if fn is not None:
                return ast.TypeNode("func")
            self._err(ErrCode.TYPE_UNDEFINED,
                      f"未定义的标识符 '{e.name}'", e)

        if isinstance(e, ast.SelfExpr):
            if self.current_class is None:
                self._err(ErrCode.TYPE_UNDEFINED,
                          "'self' 只能在方法中使用", e)
            return ast.TypeNode(self.current_class.fqn)

        if isinstance(e, ast.NewExpr):
            ci = self._resolve_class(e.class_name, self.current_unit)
            if ci is None:
                self._err(ErrCode.TYPE_NOT_CLASS,
                          f"未知的类 '{e.class_name}'", e)
            ctor = ci.find_method("init", self.classes, n_args=len(e.args))
            expected = ctor.params if ctor else []
            if len(expected) != len(e.args):
                self._err(ErrCode.TYPE_ARG_COUNT,
                          f"类 '{ci.fqn}' 构造函数需要 {len(expected)} 个参数，"
                          f"实际传入 {len(e.args)} 个", e)
            for p, a in zip(expected, e.args):
                at = self.infer(a, scope)
                pt = self._normalize_type(p.type_node)
                if not self.is_assignable(pt, at):
                    self._err(ErrCode.TYPE_MISMATCH,
                              f"构造函数参数 '{p.name}' 类型不匹配："
                              f"{at} 无法赋给 {p.type_node}", a)
            return ast.TypeNode(ci.fqn)

        if isinstance(e, ast.Binary):
            lt = self.infer(e.left, scope)
            rt = self.infer(e.right, scope)
            op = e.op

            # 1. 尝试运算符重载
            op_key = BIN_OP_MAP.get(op)
            if op_key:
                left_ci = self.classes.get(lt.name)
                if left_ci is not None:
                    m = left_ci.find_operator(op_key, self.classes)
                    if m is not None:
                        if len(m.params) != 1:
                            self._err(ErrCode.TYPE_ARG_COUNT,
                                      f"运算符 '{op_key}' 需要 1 个参数", e)
                        p0 = self._normalize_type(m.params[0].type_node)
                        if not self.is_assignable(p0, rt):
                            self._err(ErrCode.TYPE_MISMATCH,
                                      f"运算符 '{op_key}' 参数类型不匹配："
                                      f"{rt} 无法赋给 {p0}", e)
                        return self._normalize_type(m.return_type)

            # 2. 内建运算
            if op in ("==", "!="):
                if not (self.is_assignable(lt, rt) or
                        self.is_assignable(rt, lt)):
                    self._err(ErrCode.TYPE_BAD_OPERATOR,
                              f"无法比较不同类型: {lt} {op} {rt}", e)
                return ast.TypeNode("Bool")
            if op in ("<", ">", "<=", ">="):
                if lt.name not in NUMERIC and lt.name != "Any":
                    self._err(ErrCode.TYPE_BAD_OPERATOR,
                              f"比较运算 '{op}' 需要数值类型，左侧是 {lt}", e)
                if rt.name not in NUMERIC and rt.name != "Any":
                    self._err(ErrCode.TYPE_BAD_OPERATOR,
                              f"比较运算 '{op}' 需要数值类型，右侧是 {rt}", e)
                return ast.TypeNode("Bool")
            if op in ("&&", "||"):
                self._expect_bool(lt, e.left)
                self._expect_bool(rt, e.right)
                return ast.TypeNode("Bool")
            if op in ("+", "-", "*", "/", "%"):
                if op == "+" and lt.name == "String" and rt.name == "String":
                    return ast.TypeNode("String")
                if lt.name == "Any" or rt.name == "Any":
                    return ast.TypeNode("Any")
                if lt.name not in NUMERIC or rt.name not in NUMERIC:
                    self._err(ErrCode.TYPE_MISMATCH,
                              f"算术运算符 '{op}' 需要数值类型，"
                              f"但左侧是 {lt}，右侧是 {rt}", e)
                if lt.name == "Float" or rt.name == "Float":
                    return ast.TypeNode("Float")
                return ast.TypeNode("Int")
            self._err(ErrCode.TYPE_BAD_OPERATOR,
                      f"未知运算符 '{op}'", e)

        if isinstance(e, ast.Unary):
            t = self.infer(e.operand, scope)
            if e.op == "-":
                if t.name not in NUMERIC and t.name != "Any":
                    self._err(ErrCode.TYPE_MISMATCH,
                              f"一元 '-' 需要数值类型，实际 {t}", e)
                return t
            if e.op == "!":
                self._expect_bool(t, e.operand)
                return ast.TypeNode("Bool")
            self._err(ErrCode.TYPE_BAD_OPERATOR,
                      f"未知一元运算符 '{e.op}'", e)

        if isinstance(e, ast.Assign):
            if isinstance(e.target, ast.Ident):
                sym = scope.lookup(e.target.name)
                if sym is None:
                    self._err(ErrCode.TYPE_UNDEFINED,
                              f"未定义变量 '{e.target.name}'", e.target)
                if not sym.mutable:
                    self._err(ErrCode.TYPE_IMMUTABLE,
                              f"不可变变量 '{e.target.name}' 无法赋值", e.target)
                target_type = self._normalize_type(sym.type)
            elif isinstance(e.target, ast.FieldAccess):
                obj_t = self.infer(e.target.obj, scope)
                ci = self.classes.get(obj_t.name)
                if ci is None:
                    self._err(ErrCode.TYPE_NOT_CLASS,
                              f"'{obj_t}' 不是类实例，无法访问字段 "
                              f"'{e.target.field}'", e.target)
                f = ci.find_field(e.target.field, self.classes)
                if f is None:
                    self._err(ErrCode.TYPE_NO_MEMBER,
                              f"类 '{obj_t}' 没有字段 "
                              f"'{e.target.field}'", e.target)
                target_type = self._normalize_type(f.type_node)
            else:
                self._err(ErrCode.TYPE_MISMATCH, "非法赋值目标", e)
            vt = self.infer(e.value, scope)
            if not self.is_assignable(target_type, vt):
                self._err(ErrCode.TYPE_MISMATCH,
                          f"赋值类型不匹配：{vt} 无法赋给 {target_type}", e)
            return target_type

        if isinstance(e, ast.FieldAccess):
            obj_t = self.infer(e.obj, scope)

            # 数组的 length
            if obj_t.is_array and e.field == "length":
                return ast.TypeNode("Int")

            ci = self.classes.get(obj_t.name)
            if ci is None:
                self._err(ErrCode.TYPE_NOT_CLASS,
                          f"'{obj_t}' 不是类实例，无法访问字段 '{e.field}'", e)
            f = ci.find_field(e.field, self.classes)
            if f is None:
                self._err(ErrCode.TYPE_NO_MEMBER,
                          f"类 '{obj_t}' 没有字段 '{e.field}'", e)
            return self._normalize_type(f.type_node)

        # ---------- 索引读取：obj[xxx] → get.opr("xxx") ----------
        if isinstance(e, ast.IndexExpr):
            obj_t = self.infer(e.obj, scope)

            if obj_t.is_array:
                # 数组：用 expr 索引
                e.is_array_index = True
                idx_t = self.infer(e.index, scope)
                if idx_t.name not in ("Int", "Any"):
                    self._err(ErrCode.TYPE_MISMATCH,
                              f"数组索引必须是 Int，实际 {idx_t}", e)
                return ast.TypeNode(obj_t.name, obj_t.generics)

            # 类：用 raw_text 走 get.opr
            ci = self.classes.get(obj_t.name)
            if ci is None:
                self._err(ErrCode.TYPE_NOT_CLASS,
                          f"'{obj_t}' 不支持索引访问", e)
            m = ci.find_operator("get.opr", self.classes)
            if m is None:
                self._err(ErrCode.TYPE_NO_MEMBER,
                          f"类 '{obj_t}' 没有定义 'calc.get.opr'", e)
            return self._normalize_type(m.return_type)

        # ---------- 索引赋值：obj[xxx] = v → set.opr("xxx", v) ----------
        if isinstance(e, ast.IndexAssign):
            obj_t = self.infer(e.obj, scope)
            ci = self.classes.get(obj_t.name)
            if ci is None:
                self._err(ErrCode.TYPE_NOT_CLASS,
                          f"'{obj_t}' 不支持索引赋值", e)
            m = ci.find_operator("set.opr", self.classes)
            if m is None:
                self._err(ErrCode.TYPE_NO_MEMBER,
                          f"类 '{obj_t}' 没有定义 'calc.set.opr'", e)
            if len(m.params) != 2:
                self._err(ErrCode.TYPE_ARG_COUNT,
                          f"'{obj_t}.set.opr' 需要 2 个参数", e)
            p1 = self._normalize_type(m.params[1].type_node)
            vt = self.infer(e.value, scope)
            if not self.is_assignable(p1, vt):
                self._err(ErrCode.TYPE_MISMATCH,
                          f"set.opr 值类型不匹配：{vt} 无法赋给 {p1}", e)
            return ast.TypeNode("Void")

        if isinstance(e, ast.SliceStringExpr):
            return ast.TypeNode("String")

        # ---------- 调用 ----------
        if isinstance(e, ast.Call):
            if isinstance(e.callee, ast.FieldAccess):
                obj_t = self.infer(e.callee.obj, scope)

                # 数组方法
                if obj_t.is_array:
                    elem_t = ast.TypeNode(obj_t.name, obj_t.generics)
                    if e.callee.field == "push":
                        if len(e.args) != 1:
                            self._err(ErrCode.TYPE_ARG_COUNT,
                                      "push 需要 1 个参数", e)
                        at = self.infer(e.args[0], scope)
                        if not self.is_assignable(elem_t, at):
                            self._err(ErrCode.TYPE_MISMATCH,
                                      f"push 参数类型不匹配："
                                      f"{at} 无法赋给 {elem_t}", e)
                        return ast.TypeNode("Void")
                    if e.callee.field == "pop":
                        if len(e.args) != 0:
                            self._err(ErrCode.TYPE_ARG_COUNT,
                                      "pop 不需要参数", e)
                        return elem_t


                if obj_t.name == "Char":
                    return self._check_char_method(
                        e.callee.field, e.args, scope, e)

                # 类方法
                ci = self.classes.get(obj_t.name)
                if ci is None:
                    self._err(ErrCode.TYPE_NOT_CLASS,
                              f"'{obj_t}' 不是类，无法调用方法 "
                              f"'{e.callee.field}'", e.callee)
                m = ci.find_method(e.callee.field, self.classes,
                                   n_args=len(e.args))
                if m is None:
                    # 报更具体的错
                    avail = ci.methods.get(e.callee.field, [])
                    if avail:
                        counts = [len(a.params) for a in avail]
                        self._err(
                            ErrCode.TYPE_ARG_COUNT,
                            f"方法 '{e.callee.field}' 没有接受 "
                            f"{len(e.args)} 个参数的重载"
                            f"（可用：{counts}）",
                            e.callee)
                    self._err(ErrCode.TYPE_NO_METHOD,
                              f"类 '{obj_t}' 没有方法 "
                              f"'{e.callee.field}'", e.callee)
                return self._check_call_args(
                    m.params, self._normalize_type(m.return_type),
                    e.args, scope, f"{obj_t}.{e.callee.field}")
            if isinstance(e.callee, ast.Ident):
                name = e.callee.name
                sym = scope.lookup(name)
                if sym and sym.kind == "func" and sym.func_sig:
                    params, ret = sym.func_sig
                    return self._check_call_args(params, ret, e.args,
                                                 scope, name)
                unit = self.current_unit
                if unit and name in unit.symbol_table:
                    entry = unit.symbol_table[name]
                    if isinstance(entry, ast.FuncDecl):
                        fname = (f"{unit.package}.{name}"
                                 if unit.package else name)
                        return self._check_call_args(
                            entry.params,
                            self._normalize_type(entry.return_type),
                            e.args, scope, fname)
                fn = self._resolve_function(name, unit)
                if fn is not None:
                    return self._check_call_args(
                        fn.params,
                        self._normalize_type(fn.return_type),
                        e.args, scope, name)
                self._err(ErrCode.TYPE_UNDEFINED,
                          f"未定义的函数 '{name}'", e.callee)

            self._err(ErrCode.TYPE_NOT_CALLABLE, "不支持的调用目标", e.callee)

        self._err(ErrCode.TYPE_MISMATCH,
                  f"未知表达式类型: {type(e).__name__}", e)

    def _check_call_args(self, params, ret_type, args, scope, fname):
        if len(params) != len(args):
            self._err(ErrCode.TYPE_ARG_COUNT,
                      f"函数 '{fname}' 需要 {len(params)} 个参数，"
                      f"实际传入 {len(args)} 个",
                      args[0] if args else None)
        for p, a in zip(params, args):
            at = self.infer(a, scope)
            pt = p.type_node if hasattr(p, "type_node") else p
            pt = self._normalize_type(pt)
            if not self.is_assignable(pt, at):
                self._err(ErrCode.TYPE_MISMATCH,
                          f"调用 '{fname}' 参数 "
                          f"'{getattr(p, 'name', '?')}' 类型不匹配："
                          f"{at} 无法赋给 {pt}", a)
        return self._normalize_type(ret_type)