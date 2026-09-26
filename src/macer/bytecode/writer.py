"""字节码序列化（写 .mceb）"""
import struct
from pathlib import Path
from .opcodes import Op, OP_INFO
from .constant_pool import ConstantPool, ConstTag
from .class_table import ClassTable


MAGIC = b"MCEB"
MAJOR = 1
MINOR = 0


class BytecodeWriter:
    def __init__(self):
        self.cp = ConstantPool()
        self.ct = ClassTable()
        self.code = bytearray()
        self.entry_main = 0xFFFFFFFF

    # ---------- 写指令 ----------
    def emit(self, op: Op, *operands):
        self.code.append(op.value)
        info = OP_INFO[op]
        for (fmt, val) in zip(info.operand_sizes, operands):
            if fmt == "u1":
                self.code.extend(struct.pack(">B", val & 0xFF))
            elif fmt == "u2":
                self.code.extend(struct.pack(">H", val & 0xFFFF))
            elif fmt == "s2":
                self.code.extend(struct.pack(">h", val))

    @property
    def code_offset(self) -> int:
        return len(self.code)

    # ---------- 序列化 ----------
    def write(self, path: str):
        data = bytearray()

        # 1. Header
        data.extend(MAGIC)
        data.extend(struct.pack(">HH", MAJOR, MINOR))
        data.extend(struct.pack(">HHHH",
                                len(self.cp), len(self.ct.classes),
                                len(self.ct.functions), 0))

        # 2. 常量池
        for c in self.cp.constants:
            data.append(c.tag.value)
            if c.tag == ConstTag.INT:
                data.extend(struct.pack(">q", c.value))
            elif c.tag == ConstTag.FLOAT:
                data.extend(struct.pack(">d", c.value))
            elif c.tag == ConstTag.STRING:
                b = c.value.encode("utf-8")
                data.extend(struct.pack(">I", len(b)))
                data.extend(b)
            elif c.tag == ConstTag.CHAR:
                data.extend(struct.pack(">I", ord(c.value)))
            elif c.tag == ConstTag.BOOL:
                data.append(1 if c.value else 0)
            elif c.tag == ConstTag.NULL:
                pass
            elif c.tag in (ConstTag.CLASS_REF,):
                data.extend(struct.pack(">H", c.parts[0]))
            elif c.tag == ConstTag.FIELD_REF:
                data.extend(struct.pack(">HHH", *c.parts))
            elif c.tag == ConstTag.METHOD_REF:
                data.extend(struct.pack(">HHH", *c.parts))
            elif c.tag == ConstTag.FUNC_REF:
                data.extend(struct.pack(">HH", *c.parts))

        # 3. 类表
        for cls in self.ct.classes:
            data.extend(struct.pack(">HH", cls.name_idx, cls.parent_idx))
            data.extend(struct.pack(">H", len(cls.fields)))
            for f in cls.fields:
                data.extend(struct.pack(">HHB",
                                        f.name_idx, f.type_idx, f.access))
            data.extend(struct.pack(">H", len(cls.methods)))
            for m in cls.methods:
                data.extend(struct.pack(">HHBIII",
                                        m.name_idx, m.descriptor_idx,
                                        m.access, m.code_offset,
                                        m.code_length, m.local_count))

        # 4. 函数表
        for fn in self.ct.functions:
            data.extend(struct.pack(">HHIII",
                                    fn.name_idx, fn.descriptor_idx,
                                    fn.code_offset, fn.code_length,
                                    fn.local_count))

        # 5. Code Section
        data.extend(struct.pack(">I", len(self.code)))
        data.extend(self.code)

        # 6. Entry point
        data.extend(struct.pack(">I", self.entry_main))

        Path(path).write_bytes(data)