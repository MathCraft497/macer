"""阶段 2 测试：最小 VM"""
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from macer.bytecode import Op, BytecodeWriter
from macer.vm import VM


def _make_writer_with_main(emits):
    """构造一个 writer，把 emits 写进 main 方法"""
    w = BytecodeWriter()

    name_idx = w.cp.add_string("Main")
    cls_idx = w.ct.add_class(name_idx)

    m_name = w.cp.add_string("main")
    m_desc = w.cp.add_string("()V")
    code_start = w.code_offset

    for emit in emits:
        emit(w)

    code_end = w.code_offset
    w.ct.add_method(cls_idx, m_name, m_desc,
                    code_offset=code_start,
                    code_length=code_end - code_start,
                    local_count=4)
    w.entry_main = 0
    return w


def _capture_run(w):
    """跑 VM 并捕获 stdout"""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        vm = VM(w)
        vm.run()
        out = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    return out


def test_print_hello():
    def emit(w):
        c = w.cp.add_string("hello")
        w.emit(Op.LOAD_CONST, c)
        w.emit(Op.PRINT)
        w.emit(Op.RETURN_VOID)

    w = _make_writer_with_main([emit])
    out = _capture_run(w)
    assert out == "hello\n", f"输出不对: {out!r}"
    print("OK  test_print_hello")


def test_add():
    def emit(w):
        c1 = w.cp.add_int(3)
        c2 = w.cp.add_int(4)
        w.emit(Op.LOAD_CONST, c1)
        w.emit(Op.LOAD_CONST, c2)
        w.emit(Op.ADD)
        w.emit(Op.PRINT)
        w.emit(Op.RETURN_VOID)

    w = _make_writer_with_main([emit])
    out = _capture_run(w)
    assert out == "7\n", f"输出不对: {out!r}"
    print("OK  test_add")


def test_local_var():
    """let x = 10; let y = 20; print(x + y);"""
    def emit(w):
        c10 = w.cp.add_int(10)
        c20 = w.cp.add_int(20)
        w.emit(Op.LOAD_CONST, c10)
        w.emit(Op.STORE_LOCAL, 0)
        w.emit(Op.LOAD_CONST, c20)
        w.emit(Op.STORE_LOCAL, 1)
        w.emit(Op.LOAD_LOCAL, 0)
        w.emit(Op.LOAD_LOCAL, 1)
        w.emit(Op.ADD)
        w.emit(Op.PRINT)
        w.emit(Op.RETURN_VOID)

    w = _make_writer_with_main([emit])
    out = _capture_run(w)
    assert out == "30\n", f"输出不对: {out!r}"
    print("OK  test_local_var")


def test_if():
    """if true { print("yes") } else { print("no") }"""
    def emit(w):
        c_yes = w.cp.add_string("yes")
        c_no = w.cp.add_string("no")
        w.emit(Op.LOAD_TRUE)
        # JUMP_IF_FALSE 跳过 then
        # 0: LOAD_TRUE
        # 1: JUMP_IF_FALSE +?    → else_start
        # 4: LOAD_CONST yes
        # 7: PRINT
        # 8: JUMP +?              → end
        # 11: LOAD_CONST no       ← else_start
        # 14: PRINT
        # 15: RETURN_VOID          ← end
        w.emit(Op.JUMP_IF_FALSE, 7)   # 跳到 pc=11
        w.emit(Op.LOAD_CONST, c_yes)
        w.emit(Op.PRINT)
        w.emit(Op.JUMP, 4)             # 跳到 pc=15
        w.emit(Op.LOAD_CONST, c_no)
        w.emit(Op.PRINT)
        w.emit(Op.RETURN_VOID)

    w = _make_writer_with_main([emit])
    out = _capture_run(w)
    assert out == "yes\n", f"输出不对: {out!r}"
    print("OK  test_if")


def test_while_count():
    """var i = 0; while i < 3 { print(i); i = i + 1 }"""
    def emit(w):
        c0 = w.cp.add_int(0)
        c1 = w.cp.add_int(1)
        c3 = w.cp.add_int(3)

        # 局部变量：0 = i
        # pc 指令起始
        #  0: LOAD_CONST 0      (3B)
        #  3: STORE_LOCAL 0     (2B)
        #  5: LOAD_LOCAL 0      (2B) ← loop_start
        #  7: LOAD_CONST 3      (3B)
        # 10: LT                (1B)
        # 11: JUMP_IF_FALSE +14 (3B)  → pc=28
        # 14: LOAD_LOCAL 0      (2B)
        # 16: PRINT             (1B)
        # 17: LOAD_LOCAL 0      (2B)
        # 19: LOAD_CONST 1      (3B)
        # 22: ADD               (1B)
        # 23: STORE_LOCAL 0     (2B)
        # 25: JUMP -23          (3B)  → pc=5
        # 28: RETURN_VOID       (1B)

        w.emit(Op.LOAD_CONST, c0)
        w.emit(Op.STORE_LOCAL, 0)
        w.emit(Op.LOAD_LOCAL, 0)
        w.emit(Op.LOAD_CONST, c3)
        w.emit(Op.LT)
        w.emit(Op.JUMP_IF_FALSE, 14)     # ← 从 11 改成 14
        w.emit(Op.LOAD_LOCAL, 0)
        w.emit(Op.PRINT)
        w.emit(Op.LOAD_LOCAL, 0)
        w.emit(Op.LOAD_CONST, c1)
        w.emit(Op.ADD)
        w.emit(Op.STORE_LOCAL, 0)
        w.emit(Op.JUMP, -23)              # ← 从 -25 改成 -23
        w.emit(Op.RETURN_VOID)

    w = _make_writer_with_main([emit])
    out = _capture_run(w)
    assert out == "0\n1\n2\n", f"输出不对: {out!r}"
    print("OK  test_while_count")


if __name__ == "__main__":
    tests = [
        test_print_hello,
        test_add,
        test_local_var,
        test_if,
        test_while_count,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERR   {t.__name__}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    if failed:
        print(f"❌ {failed} / {len(tests)} 失败")
        sys.exit(1)
    print(f"✅ {len(tests)} / {len(tests)} 通过")