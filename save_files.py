"""整文件覆盖 codegen.py 和 runtime.py"""
from pathlib import Path

# ============================================================
# codegen.py 完整内容
# ============================================================
CODEGEN = r'''"""
Macer 代码生成器（多单元版本）
"""
from typing import List, Set

from . import ast_nodes as ast


def py_name(fqn: str) -> str:
    """把 FQN 转成合法的 Python 标识符"""
    return fqn.replace(".", "_")


class CodeGen:
    def __init__(self, units):
        self.units = units
        self.lines: List[str] = []
        self.indent = 0
        self.classes: dict = {}
        self.class_pkg: dict = {}
        self.functions = []

    def emit(self, s=""):
        self.lines.append("    " * self.indent + s)

    def generate(self):
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

        ordered = self._topo_sort_classes()
        for fqn in ordered:
            self.gen_class(fqn, self.classes[fqn])
            self.emit()

        for fqn, fn in self.functions:
            if not fn.body:
                continue
            self.gen_func(fn, fqn, indent_inside_class=False)
            self.emit()

        # 入口
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
        visited = set()
        result = []

        def visit(fqn):
            if fqn in visited:
                return
            visited.add(fqn)
            decl = self.classes[fqn]
            if decl.parent:
                parent_fqn = self._resolve_parent_fqn(
                    decl.parent, self.class_pkg[fqn])
                if parent_fqn and parent_fqn in self.classes:
                    visit(parent_fqn)
            result.append(fqn)

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

    def gen_class(self, fqn, d):
        cls_py = py_name(fqn)
        base = ""
        if d.parent:
            parent_fqn = self._resolve_parent_fqn(
                d.parent, self.class_pkg[fqn])
            base = f"({py_name(parent_fqn)})"

        self.emit(f"class {cls_py}{base}:")
        self.indent += 1

        methods = {m.name: m for m in d.methods}
        ctor = methods.get("init")

        # 有 init 或 有字段（哪怕字段无初始值），都生成 __init__
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
            self.gen_func(m, f"{fqn}.{m.name}",
                          indent_inside_class=True, class_fqn=fqn)
            has_body = True

        if not has_body:
            self.emit("pass")
        self.indent -= 1

    def _gen_ctor(self, fqn, cls, ctor):
        if ctor is not None:
            params = ", ".join(["self"] + [p.name for p in ctor.params])
        else:
            params = "self"

        self.emit(f"def __init__({params}):")
        self.indent += 1

        # 字段初始化
        for f in cls.fields:
            if f.init is not None:
                self.emit(f"self.{f.name} = {self.expr(f.init)}")
            else:
                self.emit(f"self.{f.name} = None")

        # 父类构造调用（仅在这个类显式定义了 init 时）
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

        # 用户 init 体
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
'''

# ============================================================
# runtime.py 完整内容
# ============================================================
RUNTIME = r'''"""
Macer 运行时支持
- 内置函数实现
- 运行时错误包装（绝不暴露 Python traceback）
"""
import sys
import builtins


def print(*args):        # noqa: A001
    builtins.print(*args)


def len(x):              # noqa: A001
    try:
        return builtins.len(x)
    except TypeError:
        raise MacerRuntimeErr("MCE4003",
                              f"对象不支持 len()：{type(x).__name__}")


def str(v):              # noqa: A001
    return builtins.str(v)


def int(v):              # noqa: A001
    try:
        return builtins.int(v)
    except (ValueError, TypeError):
        raise MacerRuntimeErr("MCE4099", f"无法将 {v!r} 转换为 Int")


def float(v):            # noqa: A001
    try:
        return builtins.float(v)
    except (ValueError, TypeError):
        raise MacerRuntimeErr("MCE4099", f"无法将 {v!r} 转换为 Float")


def abs(v):              # noqa: A001
    return builtins.abs(v)


class MacerRuntimeErr(Exception):
    def __init__(self, code, message, mce_line=0):
        super().__init__(message)
        self.code = code
        self.message = message
        self.mce_line = mce_line


def __macer_wrap__(entry):
    try:
        entry()
    except MacerRuntimeErr as e:
        _emit(e.code, e.message)
        sys.exit(1)
    except ZeroDivisionError:
        _emit("MCE4001", "除以零")
        sys.exit(1)
    except AttributeError as e:
        _emit("MCE4002", f"空引用访问（{e}）")
        sys.exit(1)
    except IndexError:
        _emit("MCE4003", "下标越界")
        sys.exit(1)
    except KeyError as e:
        _emit("MCE4003", f"键不存在：{e}")
        sys.exit(1)
    except AssertionError as e:
        _emit("MCE4004", f"断言失败 {e}")
        sys.exit(1)
    except RecursionError:
        _emit("MCE4005", "栈溢出（递归过深）")
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        _emit("MCE4099", f"未捕获的运行时错误：{type(e).__name__}: {e}")
        sys.exit(1)


def _emit(code, message):
    RED = "\033[1;31m" if sys.stderr.isatty() else ""
    BOLD = "\033[1m" if sys.stderr.isatty() else ""
    RESET = "\033[0m" if sys.stderr.isatty() else ""
    builtins.print(file=sys.stderr)
    builtins.print(
        f"{RED}error{RESET}{BOLD}[{code}]{RESET}: {message}",
        file=sys.stderr,
    )
'''

# ============================================================
# runtime/__init__.py
# ============================================================
RUNTIME_INIT = '''"""
Macer 运行时包
"""
from .runtime import (
    print,
    len,
    str,
    int,
    float,
    abs,
    MacerRuntimeErr,
    __macer_wrap__,
)

__all__ = [
    "print", "len", "str", "int", "float", "abs",
    "MacerRuntimeErr", "__macer_wrap__",
]
'''

# ============================================================
# 写入
# ============================================================
print("写入 codegen.py ...")
Path("src/macer/codegen.py").write_text(CODEGEN, encoding="utf-8")
print("  OK,", len(CODEGEN.splitlines()), "lines")

print("写入 runtime/runtime.py ...")
Path("src/macer/runtime/runtime.py").write_text(RUNTIME, encoding="utf-8")
print("  OK,", len(RUNTIME.splitlines()), "lines")

print("写入 runtime/__init__.py ...")
Path("src/macer/runtime/__init__.py").write_text(RUNTIME_INIT, encoding="utf-8")
print("  OK")

print()
print("完成。")