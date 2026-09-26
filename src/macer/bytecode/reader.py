"""字节码反序列化（读 .mceb）"""
import struct
from pathlib import Path
from .opcodes import Op, OP_INFO
from .constant_pool import ConstantPool, Constant, ConstTag
from .class_table import ClassTable, ClassDef, FieldDef, MethodDef, FunctionDef


MAGIC = b"MCEB"


class BytecodeReader:
    def __init__(self):
        self.cp = ConstantPool()
        self.ct = ClassTable()
        self.code = b""
        self.entry_main = 0xFFFFFFFF

    def read(self, path: str):
        data = Path(path).read_bytes()
        pos = 0

        # 1. Header
        if data[:4] != MAGIC:
            raise ValueError(f"不是 Macer 字节码文件: {path}")
        pos = 4
        major, minor = struct.unpack_from(">HH", data, pos); pos += 4
        n_consts, n_classes, n_funcs, _ = struct.unpack_from(">HHHH", data, pos)
        pos += 8

        # 2. 常量池
        for _ in range(n_consts):
            tag = ConstTag(data[pos]); pos += 1
            if tag == ConstTag.INT:
                v = struct.unpack_from(">q", data, pos)[0]; pos += 8
                self.cp.constants.append(Constant(tag, v))
            elif tag == ConstTag.FLOAT:
                v = struct.unpack_from(">d", data, pos)[0]; pos += 8
                self.cp.constants.append(Constant(tag, v))
            elif tag == ConstTag.STRING:
                ln = struct.unpack_from(">I", data, pos)[0]; pos += 4
                s = data[pos:pos + ln].decode("utf-8"); pos += ln
                self.cp.constants.append(Constant(tag, s))
            elif tag == ConstTag.CHAR:
                cp_ = struct.unpack_from(">I", data, pos)[0]; pos += 4
                self.cp.constants.append(Constant(tag, chr(cp_)))
            elif tag == ConstTag.BOOL:
                v = bool(data[pos]); pos += 1
                self.cp.constants.append(Constant(tag, v))
            elif tag == ConstTag.NULL:
                self.cp.constants.append(Constant(tag))
            elif tag == ConstTag.CLASS_REF:
                v = struct.unpack_from(">H", data, pos)[0]; pos += 2
                self.cp.constants.append(Constant(tag, parts=(v,)))
            elif tag == ConstTag.FIELD_REF:
                v = struct.unpack_from(">HHH", data, pos); pos += 6
                self.cp.constants.append(Constant(tag, parts=v))
            elif tag == ConstTag.METHOD_REF:
                v = struct.unpack_from(">HHH", data, pos); pos += 6
                self.cp.constants.append(Constant(tag, parts=v))
            elif tag == ConstTag.FUNC_REF:
                v = struct.unpack_from(">HH", data, pos); pos += 4
                self.cp.constants.append(Constant(tag, parts=v))
            else:
                raise ValueError(f"未知常量 tag: {tag}")

        # 3. 类表
        for _ in range(n_classes):
            name_idx, parent_idx = struct.unpack_from(">HH", data, pos); pos += 4
            cls = ClassDef(name_idx, parent_idx)
            n_fields = struct.unpack_from(">H", data, pos)[0]; pos += 2
            for _ in range(n_fields):
                n, t, a = struct.unpack_from(">HHB", data, pos); pos += 5
                cls.fields.append(FieldDef(n, t, a))
            n_methods = struct.unpack_from(">H", data, pos)[0]; pos += 2
            for _ in range(n_methods):
                n, d, a, off, ln, lc = struct.unpack_from(">HHBIII", data, pos)
                pos += 17
                cls.methods.append(MethodDef(n, d, a, off, ln, lc))
            self.ct.classes.append(cls)

        # 4. 函数表
        for _ in range(n_funcs):
            n, d, off, ln, lc = struct.unpack_from(">HHIII", data, pos)
            pos += 16
            self.ct.functions.append(FunctionDef(n, d, off, ln, lc))

        # 5. Code Section
        code_len = struct.unpack_from(">I", data, pos)[0]; pos += 4
        self.code = data[pos:pos + code_len]; pos += code_len

        # 6. Entry point
        self.entry_main = struct.unpack_from(">I", data, pos)[0]; pos += 4