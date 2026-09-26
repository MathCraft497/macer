"""阶段 1 测试：字节码定义 + 序列化 + 反汇编"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from macer.bytecode import (
    Op, ConstantPool, ConstTag, ClassTable,
    BytecodeWriter, BytecodeReader, Disassembler,
)


def test_constant_pool():
    cp = ConstantPool()
    i1 = cp.add_int(42)
    i2 = cp.add_int(42)     # 去重
    assert i1 == i2, "常量池应去重"

    s1 = cp.add_string("hello")
    assert cp.resolve_string(s1) == "hello"

    c1 = cp.add_char("A")
    assert cp.get(c1).value == "A"

    cr = cp.add_class_ref("macer.lang.String")
    assert cp.get(cr).tag == ConstTag.CLASS_REF

    print("OK  test_constant_pool")


def test_write_read_roundtrip():
    """写字节码 → 读回 → 内容一致"""
    w = BytecodeWriter()

    # 常量
    c_int = w.cp.add_int(42)
    c_str = w.cp.add_string("hello")
    c_cls = w.cp.add_class_ref("com.example.App")

    # 类
    name_idx = w.cp.add_string("com.example.App")
    cls_idx = w.ct.add_class(name_idx)

    # 方法
    m_name = w.cp.add_string("main")
    m_desc = w.cp.add_string("()V")
    code_start = w.code_offset

    # 字节码：print("hello"); return
    w.emit(Op.LOAD_CONST, c_str)
    w.emit(Op.PRINT)
    w.emit(Op.RETURN_VOID)

    code_end = w.code_offset
    w.ct.add_method(cls_idx, m_name, m_desc,
                    code_offset=code_start,
                    code_length=code_end - code_start,
                    local_count=0)

    # 写文件
    tmp = Path("_test_roundtrip.mceb")
    w.write(str(tmp))

    # 读回
    r = BytecodeReader()
    r.read(str(tmp))

    # 校验
    assert len(r.cp) == len(w.cp), f"常量数不一致: {len(r.cp)} vs {len(w.cp)}"
    assert len(r.ct.classes) == 1
    assert r.cp.resolve_string(r.ct.classes[0].name_idx) == "com.example.App"
    assert len(r.ct.classes[0].methods) == 1
    assert r.cp.resolve_string(r.ct.classes[0].methods[0].name_idx) == "main"
    assert r.code == bytes(w.code)

    tmp.unlink()
    print("OK  test_write_read_roundtrip")


def test_disassembler():
    """反汇编输出"""
    w = BytecodeWriter()
    c_str = w.cp.add_string("hello")

    name_idx = w.cp.add_string("Test")
    cls_idx = w.ct.add_class(name_idx)

    w.emit(Op.LOAD_CONST, c_str)
    w.emit(Op.PRINT)
    w.emit(Op.RETURN_VOID)

    dis = Disassembler(w.cp, w.ct, bytes(w.code))
    text = dis.disassemble()

    assert "LOAD_CONST" in text
    assert "PRINT" in text
    assert "hello" in text
    assert "Test" in text

    print("OK  test_disassembler")
    print("--- 反汇编输出 ---")
    print(text)
    print("--- 结束 ---")


def test_op_info():
    """指令元数据"""
    from macer.bytecode import OP_INFO
    assert OP_INFO[Op.LOAD_CONST].operand_sizes == ("u2",)
    assert OP_INFO[Op.ADD].stack_pop == 2
    assert OP_INFO[Op.ADD].stack_push == 1
    print("OK  test_op_info")


if __name__ == "__main__":
    tests = [
        test_constant_pool,
        test_op_info,
        test_write_read_roundtrip,
        test_disassembler,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL  {t.__name__}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    print()
    print(f"✅ {len(tests)} / {len(tests)} 通过")