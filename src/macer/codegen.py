"""
Macer 代码生成器（多单元版本 + 运算符重载）
"""
from typing import List

from . import ast_nodes as ast


def py_name(fqn: str) -> str:
    return fqn.replace(".", "_")


class CodeGen:
    OPERATOR_DUNDER = {
        "get.opr": "__getitem__",
        "set.opr": "__setitem__",
        "opr+":    "__add__",
        "opr-":    "__sub__",
        "opr*":    "__mul__",
        "opr/":    "__truediv__",
        "opr==":   "__eq__",
        "opr!=":   "__ne__",
        "opr<":    "__lt__",
        "opr>":    "__gt__",
        "opr()":   "__call__",
    }

    def __init__(self, units):
        self.units = units
        self.lines: List[str] = []
        self.indent = 0
        self.classes: dict = {}
        self.class_pkg: dict = {}
        self.functions = []

    def emit(self, s=""):
        self.lines.append("    " * self.indent + s)

    def generate(self) -> str:
        self.emit("# 由 Macer 编译器生成 —— 请勿手动修改")
        self.emit("from __future__ import annotations")
        self.emit("import sys")
        self.emit("from macer.runtime import *")
        self.emit("from macer.runtime import __macer_wrap__")
        self.emit()

        for unit in self.units:
            pkg = unit.package
            for d in unit.program.declarations:
                if isinstance(d, ast.ClassDecl):
                    fqn = f"{pkg}.{d.name}" if pkg else d.name
                    self.classes[fqn] = d
                    self.class_pkg[fqn] = pkg
                elif isinstance(d, ast.FuncDecl):
                    fqn = f"{pkg}.{d.name}" if pkg else d.name
                    self.functions.append((fqn, d))

        for fqn in self._topo_sort_classes():
            self.gen_class(fqn, self.classes[fqn])
            self.emit()

        for fqn, fn in self.functions:
            if not fn.body:
                continue
            self.gen_func(fn, fqn, indent_inside_class=False)
            self.emit()

        main_fqn = None
        for fqn, fn in self.functions:
            if fn.name == "main" and fn.body:
                main_fqn = fqn
                break

        if main_fqn:
            self.emit("if __name__ == '__main__':")
            self.indent += 1
            self.emit("__macer_wrap__(main)")
            self.indent -= 1

        return "\n".join(self.lines)

    def _topo_sort_classes(self):
        """拓扑排序：父类先出。

        注意：类可能显式 `extends X`，也可能隐式继承 `macer.lang.Object`。
        两者都要考虑，否则子类会排在 Object 之前。
        """
        visited = set()
        result = []

        def visit(fqn):
            if fqn in visited:
                return
            visited.add(fqn)
            decl = self.classes[fqn]

            # 解析父类（显式或隐式）
            parent_fqn = None
            if decl.parent:
                parent_fqn = self._resolve_parent_fqn(
                    decl.parent, self.class_pkg[fqn])
            elif fqn != self.OBJECT_FQN and self.OBJECT_FQN in self.classes:
                # 隐式继承 macer.lang.Object
                parent_fqn = self.OBJECT_FQN

            # 递归访问父类
            if parent_fqn and parent_fqn in self.classes:
                visit(parent_fqn)

            result.append(fqn)

        # 先访问 Object（让它一定排在最前）
        if self.OBJECT_FQN in self.classes:
            visit(self.OBJECT_FQN)

        for fqn in self.classes:
            visit(fqn)
        return result

    def _resolve_parent_fqn(self, parent_name, current_pkg):
        if parent_name in self.classes:
            return parent_name
        if current_pkg:
            fqn = f"{current_pkg}.{parent_name}"
            if fqn in self.classes:
                return fqn
        for fqn in self.classes:
            if fqn.endswith("." + parent_name) or fqn == parent_name:
                return fqn
        return parent_name

    OBJECT_FQN = "macer.lang.Object"

    def gen_class(self, fqn, d):
        cls_py = py_name(fqn)
        base = ""

        # Object 自身无父类
        if fqn == self.OBJECT_FQN:
            base = ""
        elif d.parent:
            parent_fqn = self._resolve_parent_fqn(
                d.parent, self.class_pkg[fqn])
            base = f"({py_name(parent_fqn)})"
        elif self.OBJECT_FQN in self.classes:
            # 隐式继承 Object
            base = f"({py_name(self.OBJECT_FQN)})"

        self.emit(f"class {cls_py}{base}:")
        self.indent += 1

        methods = {m.name: m for m in d.methods}
        ctor = methods.get("init")

        has_body = False
        needs_init = ctor is not None or len(d.fields) > 0
        if needs_init:
            self._gen_ctor(fqn, d, ctor)
            has_body = True

        for m in d.methods:
            if m.name == "init":
                continue
            if not m.body:
                continue
            # 运算符方法
            if getattr(m, "operator", None):
                if self._gen_operator_method(fqn, m):
                    has_body = True
                continue
            self.gen_func(m, f"{fqn}.{m.name}",
                          indent_inside_class=True, class_fqn=fqn)
            has_body = True

        if not has_body:
            self.emit("pass")
        self.indent -= 1

    def _gen_operator_method(self, fqn, m):
        dunder = self.OPERATOR_DUNDER.get(m.operator)
        if dunder is None:
            return False
        params = ["self"] + [p.name for p in m.params]
        self.emit(f"def {dunder}({', '.join(params)}):")
        self.indent += 1
        if not m.body:
            self.emit("pass")
        else:
            for s in m.body:
                self.gen_stmt(s)
        self.indent -= 1
        return True

    def _gen_ctor(self, fqn, cls, ctor):
        if ctor is not None:
            params = ", ".join(["self"] + [p.name for p in ctor.params])
        else:
            params = "self"

        self.emit(f"def __init__({params}):")
        self.indent += 1

        for f in cls.fields:
            if f.init is not None:
                self.emit(f"self.{f.name} = {self.expr(f.init)}")
            else:
                self.emit(f"self.{f.name} = None")

        if cls.parent and ctor is not None:
            parent_fqn = self._resolve_parent_fqn(
                cls.parent, self.class_pkg[fqn])
            parent_decl = self.classes.get(parent_fqn)
            if parent_decl:
                parent_ctor = next(
                    (m for m in parent_decl.methods if m.name == "init"),
                    None)
                if parent_ctor:
                    args = ", ".join(p.name for p in parent_ctor.params)
                    sep = ", " if args else ""
                    self.emit(
                        f"{py_name(parent_fqn)}.__init__(self{sep}{args})")

        if ctor is not None:
            for s in ctor.body:
                self.gen_stmt(s)

        self.indent -= 1

    def gen_func(self, fn, fqn, indent_inside_class, class_fqn=None):
        prefix = "self" if indent_inside_class else ""
        params = [p.name for p in fn.params]
        if prefix:
            params = [prefix] + params

        if indent_inside_class:
            fn_name = fn.name
        else:
            if fn.name == "main":
                fn_name = "main"
            else:
                fn_name = py_name(fqn)

        self.emit(f"def {fn_name}({', '.join(params)}):")
        self.indent += 1
        if not fn.body:
            self.emit("pass")
        else:
            for s in fn.body:
                self.gen_stmt(s)
        self.indent -= 1

    def gen_stmt(self, s):
        if isinstance(s, ast.VarDecl):
            init = (self.expr(s.init) if s.init is not None
                    else self.default_value(s.type_node))
            self.emit(f"{s.name} = {init}")
        elif isinstance(s, ast.ExprStmt):
            self.emit(self.expr(s.expr))
        elif isinstance(s, ast.ReturnStmt):
            if s.value is None:
                self.emit("return")
            else:
                self.emit(f"return {self.expr(s.value)}")
        elif isinstance(s, ast.IfStmt):
            self.emit(f"if {self.expr(s.cond)}:")
            self.indent += 1
            for st in s.then_body:
                self.gen_stmt(st)
            if not s.then_body:
                self.emit("pass")
            self.indent -= 1
            if s.else_body is not None:
                self.emit("else:")
                self.indent += 1
                for st in s.else_body:
                    self.gen_stmt(st)
                if not s.else_body:
                    self.emit("pass")
                self.indent -= 1
        elif isinstance(s, ast.WhileStmt):
            self.emit(f"while {self.expr(s.cond)}:")
            self.indent += 1
            for st in s.body:
                self.gen_stmt(st)
            if not s.body:
                self.emit("pass")
            self.indent -= 1
        elif isinstance(s, ast.Block):
            for st in s.body:
                self.gen_stmt(st)
        else:
            raise NotImplementedError(f"未实现的语句 {type(s).__name__}")

    def default_value(self, t):
        mapping = {"Int": "0", "Float": "0.0", "String": '""',
                   "Bool": "False", "Any": "None"}
        return mapping.get(t.name, "None")

    def expr(self, e):
        if isinstance(e, ast.IntLit):
            return str(e.value)
        if isinstance(e, ast.FloatLit):
            return repr(e.value)
        if isinstance(e, ast.StringLit):
            return repr(e.value)
        if isinstance(e, ast.BoolLit):
            return "True" if e.value else "False"
        if isinstance(e, ast.NullLit):
            return "None"
        if isinstance(e, ast.Ident):
            return e.name
        if isinstance(e, ast.SelfExpr):
            return "self"
        if isinstance(e, ast.SliceStringExpr):
            # 作为字符串字面量
            return repr(e.raw)
        if isinstance(e, ast.NewExpr):
            args = ", ".join(self.expr(a) for a in e.args)
            fqn = self._resolve_class_fqn(e.class_name)
            return f"{py_name(fqn)}({args})"
        if isinstance(e, ast.Binary):
            op = e.op
            if op == "&&":
                op = " and "
            elif op == "||":
                op = " or "
            return f"({self.expr(e.left)} {op} {self.expr(e.right)})"
        if isinstance(e, ast.Unary):
            op = "not " if e.op == "!" else e.op
            return f"({op}{self.expr(e.operand)})"
        if isinstance(e, ast.Assign):
            return f"{self.expr(e.target)} = {self.expr(e.value)}"

        # 索引读：obj[xxx] → obj["xxx"]（字符串）
        if isinstance(e, ast.IndexExpr):
            if isinstance(e.index, ast.SliceStringExpr):
                key = repr(e.index.raw)
            else:
                key = self.expr(e.index)
            return f"{self.expr(e.obj)}[{key}]"

        # 索引写：obj[xxx] = v → obj["xxx"] = v
        if isinstance(e, ast.IndexAssign):
            if isinstance(e.index, ast.SliceStringExpr):
                key = repr(e.index.raw)
            else:
                key = self.expr(e.index)
            return (f"{self.expr(e.obj)}[{key}] = "
                    f"{self.expr(e.value)}")

        if isinstance(e, ast.FieldAccess):
            return f"{self.expr(e.obj)}.{e.field}"
        if isinstance(e, ast.Call):
            args = ", ".join(self.expr(a) for a in e.args)
            return f"{self.expr(e.callee)}({args})"
        raise NotImplementedError(f"未实现的表达式 {type(e).__name__}")

    def _resolve_class_fqn(self, name):
        if name in self.classes:
            return name
        for fqn in self.classes:
            if fqn.endswith("." + name):
                return fqn
        return name