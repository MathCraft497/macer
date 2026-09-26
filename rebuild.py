# -*- coding: utf-8 -*-
"""String 全类化：print / str / __str__ / StringLit 全支持"""
from pathlib import Path
import re

# ============================================================
# 1. runtime/runtime.py
# ============================================================
p = Path("src/macer/runtime/runtime.py")
src = p.read_text(encoding="utf-8")

# 1.1 替换 print
old_print = '''def print(*args):        # noqa: A001
    builtins.print(*args)'''

new_print = '''def print(*args):        # noqa: A001
    """打印——支持 String 类实例（有 chars 属性）"""
    converted = []
    for a in args:
        if hasattr(a, "chars") and isinstance(a.chars, list):
            converted.append("".join(str(c) for c in a.chars))
        else:
            converted.append(a)
    builtins.print(*converted)'''

if old_print in src:
    src = src.replace(old_print, new_print, 1)
    print("OK  runtime.py print")
else:
    print("WARN runtime.py print 未匹配")

# 1.2 替换 str
old_str = '''def str(v):              # noqa: A001
    return builtins.str(v)'''

new_str = '''def str(v):              # noqa: A001
    """转字符串——返回 String 类实例（如果存在）"""
    s = builtins.str(v)
    cls = _get_string_class()
    if cls is not None:
        return cls(list(s))
    return s'''

if old_str in src:
    src = src.replace(old_str, new_str, 1)
    print("OK  runtime.py str")
else:
    print("WARN runtime.py str 未匹配")

# 1.3 追加辅助函数
if "_get_string_class" not in src:
    src += '''

# ============================================================
# String 类包装支持
# ============================================================
_STRING_CLASS = None


def __set_string_class(cls):
    global _STRING_CLASS
    _STRING_CLASS = cls


def _get_string_class():
    return _STRING_CLASS


def _builtins_str(v):
    return builtins.str(v)


def _str_from_chars(chars):
    cls = _get_string_class()
    if cls is not None:
        return cls(list(chars))
    return "".join(chars)


def _chars_of(v):
    if hasattr(v, "chars") and isinstance(v.chars, list):
        return list(v.chars)
    if isinstance(v, str):
        return list(v)
    return list(builtins.str(v))
'''
    print("OK  runtime.py 辅助函数")

p.write_text(src, encoding="utf-8")

# ============================================================
# 2. runtime/__init__.py
# ============================================================
p = Path("src/macer/runtime/__init__.py")
p.write_text('''"""
Macer 运行时包
"""
from .runtime import (
    print, len, str, int, float, abs,
    MacerRuntimeErr, __macer_wrap__,
    _char_toInt, _char_toString, _char_toUpper, _char_toLower,
    __set_string_class, _get_string_class, _builtins_str,
    _str_from_chars, _chars_of,
)

__all__ = [
    "print", "len", "str", "int", "float", "abs",
    "MacerRuntimeErr", "__macer_wrap__",
    "_char_toInt", "_char_toString", "_char_toUpper", "_char_toLower",
    "__set_string_class", "_get_string_class", "_builtins_str",
    "_str_from_chars", "_chars_of",
]
''', encoding="utf-8")
print("OK  runtime/__init__.py")

# ============================================================
# 3. codegen.py
# ============================================================
p = Path("src/macer/codegen.py")
src = p.read_text(encoding="utf-8")

# 3.1 加 STRING_FQN
if "STRING_FQN" not in src:
    src = src.replace(
        '    OBJECT_FQN = "macer.lang.Object"',
        '    OBJECT_FQN = "macer.lang.Object"\n    STRING_FQN = "macer.lang.String"',
        1,
    )
    print("OK  codegen.py STRING_FQN")

# 3.2 generate() 末尾注册 String 类
old_gen = '''        if main_fqn:
            self.emit("if __name__ == '__main__':")'''
new_gen = '''        # 注册 String 类
        if self.STRING_FQN in self.classes:
            self.emit(f"__set_string_class({py_name(self.STRING_FQN)})")
            self.emit()

        if main_fqn:
            self.emit("if __name__ == '__main__':")'''

if old_gen in src:
    src = src.replace(old_gen, new_gen, 1)
    print("OK  codegen.py 注册 String 类")
else:
    print("WARN codegen.py main_fqn 未匹配")

# 3.3 gen_class 里 String 生成 __str__
if "_gen_dunder_str" not in src:
    old = '''        if not has_body:
            self.emit("pass")
        self.indent -= 1

    def _gen_operator_method'''
    new = '''        # String 类生成 __str__
        if fqn == self.STRING_FQN:
            if self._gen_dunder_str(fqn, d):
                has_body = True

        if not has_body:
            self.emit("pass")
        self.indent -= 1

    def _gen_dunder_str(self, fqn, d):
        if fqn != self.STRING_FQN:
            return False
        self.emit("def __str__(self):")
        self.indent += 1
        self.emit('return "".join(str(c) for c in self.chars)')
        self.indent -= 1
        return True

    def _gen_operator_method'''
    if old in src:
        src = src.replace(old, new, 1)
        print("OK  codegen.py _gen_dunder_str")
    else:
        print("WARN codegen.py gen_class 循环未匹配")

# 3.4 expr(Call) 里 str() 特殊处理
old_call = '''        if isinstance(e, ast.Call):
            if isinstance(e.callee, ast.FieldAccess):'''
new_call = '''        if isinstance(e, ast.Call):
            # 内置 str(x) → _str_from_chars(_chars_of(x))
            if (isinstance(e.callee, ast.Ident)
                    and e.callee.name == "str"
                    and self.STRING_FQN in self.classes
                    and len(e.args) == 1):
                arg = self.expr(e.args[0])
                return f"_str_from_chars(_chars_of({arg}))"

            if isinstance(e.callee, ast.FieldAccess):'''

if old_call in src and "_str_from_chars" not in src.split("def expr")[1].split("def ")[0]:
    src = src.replace(old_call, new_call, 1)
    print("OK  codegen.py str() 特殊处理")

p.write_text(src, encoding="utf-8")

# ============================================================
# 4. type_checker.py：str 返回 String 类
# ============================================================
p = Path("src/macer/type_checker.py")
src = p.read_text(encoding="utf-8")

old = '''        for name, (params, ret) in self.basic_lib.items():
            sym = Symbol(name, ast.TypeNode("func"), False, "func")
            sym.func_sig = (params, ret)
            self.global_scope.symbols[name] = sym'''

new = '''        STRING_FQN = "macer.lang.String"
        for name, (params, ret) in self.basic_lib.items():
            if name == "str" and STRING_FQN in self.classes:
                ret = ast.TypeNode(STRING_FQN)
            sym = Symbol(name, ast.TypeNode("func"), False, "func")
            sym.func_sig = (params, ret)
            self.global_scope.symbols[name] = sym'''

if old in src:
    src = src.replace(old, new, 1)
    p.write_text(src, encoding="utf-8")
    print("OK  type_checker.py str 返回 String 类")
else:
    print("WARN type_checker.py basic_lib 注册未匹配")

print()
print("完成。请跑：")
print('  Get-ChildItem -Recurse -Filter "*.__macer__.py" | Remove-Item -Force')
print('  python -m macer run --source-root examples/multi-package/src --source-root stdlib examples/multi-package/src/com/example/app/Main.mce')