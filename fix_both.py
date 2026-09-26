# -*- coding: utf-8 -*-
"""阶段 3.2：变量 + 赋值"""
from pathlib import Path

ROOT = Path(__file__).parent
p = ROOT / "src/macer/codegen_bytecode.py"
src = p.read_text(encoding="utf-8")

# ---------- 1. 加 VarDecl ----------
if "isinstance(s, ast.VarDecl)" not in src:
    old = """        raise BytecodeCodeGenError(
            f"阶段 3.1 暂不支持的语句：{type(s).__name__}")"""
    new = """        if isinstance(s, ast.VarDecl):
            if s.init is not None:
                self._gen_expr(s.init)
            else:
                self.writer.emit(Op.LOAD_NULL)
            slot = self._alloc_local(s.name)
            self.writer.emit(Op.STORE_LOCAL, slot)
            return

        raise BytecodeCodeGenError(
            f"阶段 3.2 暂不支持的语句：{type(s).__name__}")"""
    if old in src:
        src = src.replace(old, new, 1)
        print("OK  加 VarDecl")
    else:
        print("WARN  VarDecl 未匹配（先检查 _gen_stmt）")
else:
    print("SKIP VarDecl 已存在")

# ---------- 2. 加 Ident ----------
if "self.local_slots.get(e.name)" not in src:
    old = """        # ---------- 二元运算 ----------
        if isinstance(e, ast.Binary):"""
    new = """        # ---------- 标识符 ----------
        if isinstance(e, ast.Ident):
            slot = self.local_slots.get(e.name)
            if slot is None:
                raise BytecodeCodeGenError(f"未定义变量: {e.name}")
            self.writer.emit(Op.LOAD_LOCAL, slot)
            return

        # ---------- 赋值 ----------
        if isinstance(e, ast.Assign):
            if not isinstance(e.target, ast.Ident):
                raise BytecodeCodeGenError(
                    "阶段 3.2 只支持变量赋值")
            self._gen_expr(e.value)
            self.writer.emit(Op.DUP)
            slot = self.local_slots.get(e.target.name)
            if slot is None:
                raise BytecodeCodeGenError(
                    f"未定义变量: {e.target.name}")
            self.writer.emit(Op.STORE_LOCAL, slot)
            return

        # ---------- 二元运算 ----------
        if isinstance(e, ast.Binary):"""
    if old in src:
        src = src.replace(old, new, 1)
        print("OK  加 Ident + Assign")
    else:
        print("WARN  Ident 未匹配（先检查 _gen_expr）")
else:
    print("SKIP Ident 已存在")

p.write_text(src, encoding="utf-8")
print()
print("完成。请把以下测试追加到 tests/test_codegen_bytecode.py：")
print()
print('''
def test_let():
    out = _compile_and_run("""
func main() -> Void {
    let a: Int = 1;
    let b: Int = 2;
    print(a + b);
}
""")
    assert out == "3\\n", f"输出: {out!r}"
    print("OK  test_let")


def test_var_assign():
    out = _compile_and_run("""
func main() -> Void {
    var c: Int = 10;
    c = c + 5;
    print(c);
}
""")
    assert out == "15\\n", f"输出: {out!r}"
    print("OK  test_var_assign")


def test_let_chain():
    out = _compile_and_run("""
func main() -> Void {
    let a: Int = 1;
    let b: Int = a + 1;
    let c: Int = a + b;
    print(c);
}
""")
    assert out == "3\\n", f"输出: {out!r}"
    print("OK  test_let_chain")
''')