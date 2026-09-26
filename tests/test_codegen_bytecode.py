"""阶段 3.1 测试：AST → 字节码"""
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from macer.bytecode.compiler import compile_source_to_bytecode
from macer.vm import VM


def _compile_and_run(source):
    writer, bag = compile_source_to_bytecode(source, "<test>")
    if writer is None or bag.has_errors():
        msgs = "\n".join(d.message for d in bag.diagnostics)
        raise RuntimeError(f"编译失败:\n{msgs}")

    # 捕获 stdout
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        vm = VM(writer)
        vm.run()
        out = sys.stdout.getvalue()
    finally:
        sys.stdout = old
    return out


def test_print_int():
    out = _compile_and_run("""
func main() -> Void {
    print(1);
}
""")
    assert out == "1\n", f"输出: {out!r}"
    print("OK  test_print_int")


def test_print_add():
    out = _compile_and_run("""
func main() -> Void {
    print(1 + 2);
}
""")
    assert out == "3\n", f"输出: {out!r}"
    print("OK  test_print_add")


def test_print_expr():
    out = _compile_and_run("""
func main() -> Void {
    print((1 + 2) * 3 - 4 / 2);
}
""")
    assert out == "7.0\n" or out == "7\n", f"输出: {out!r}"
    print("OK  test_print_expr")


def test_print_str():
    out = _compile_and_run("""
func main() -> Void {
    print("hello");
}
""")
    assert out == "hello\n", f"输出: {out!r}"
    print("OK  test_print_str")


def test_str_builtin():
    out = _compile_and_run("""
func main() -> Void {
    print(str(42));
}
""")
    assert out == "42\n", f"输出: {out!r}"
    print("OK  test_str_builtin")


def test_compare():
    out = _compile_and_run("""
func main() -> Void {
    print(1 < 2);
    print(1 > 2);
    print(1 == 1);
}
""")
    assert out == "true\nfalse\ntrue\n", f"输出: {out!r}"
    print("OK  test_compare")


def test_unary():
    out = _compile_and_run("""
func main() -> Void {
    print(-5);
    print(!true);
}
""")
    assert out == "-5\nfalse\n", f"输出: {out!r}"
    print("OK  test_unary")

def test_let():
    out = _compile_and_run("""
func main() -> Void {
    let a: Int = 1;
    let b: Int = 2;
    print(a + b);
}
""")
    assert out == "3\n", f"输出: {out!r}"
    print("OK  test_let")


def test_var_assign():
    out = _compile_and_run("""
func main() -> Void {
    var c: Int = 10;
    c = c + 5;
    print(c);
}
""")
    assert out == "15\n", f"输出: {out!r}"
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
    assert out == "3\n", f"输出: {out!r}"
    print("OK  test_let_chain")

def test_if_then():
    out = _compile_and_run("""
func main() -> Void {
    let a: Int = 5;
    if a > 3 {
        print(100);
    }
}
""")
    assert out == "100\n", f"输出: {out!r}"
    print("OK  test_if_then")


def test_if_else():
    out = _compile_and_run("""
func main() -> Void {
    let a: Int = 2;
    if a > 3 {
        print(100);
    } else {
        print(200);
    }
}
""")
    assert out == "200\n", f"输出: {out!r}"
    print("OK  test_if_else")


def test_if_else_chain():
    out = _compile_and_run("""
func main() -> Void {
    let a: Int = 5;
    if a > 10 {
        print(1);
    } else {
        if a > 3 {
            print(2);
        } else {
            print(3);
        }
    }
}
""")
    assert out == "2\n", f"输出: {out!r}"
    print("OK  test_if_else_chain")


def test_while():
    out = _compile_and_run("""
func main() -> Void {
    var i: Int = 0;
    while i < 3 {
        print(i);
        i = i + 1;
    }
}
""")
    assert out == "0\n1\n2\n", f"输出: {out!r}"
    print("OK  test_while")


def test_while_sum():
    out = _compile_and_run("""
func main() -> Void {
    var sum: Int = 0;
    var i: Int = 1;
    while i <= 5 {
        sum = sum + i;
        i = i + 1;
    }
    print(sum);
}
""")
    assert out == "15\n", f"输出: {out!r}"
    print("OK  test_while_sum")


if __name__ == "__main__":
    tests = [
        test_print_int,
        test_print_add,
        test_print_expr,
        test_print_str,
        test_str_builtin,
        test_compare,
        test_unary,
        test_let,
        test_var_assign,
        test_let_chain,
        test_if_then,
        test_if_else,
        test_if_else_chain,
        test_while,
        test_while_sum,
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