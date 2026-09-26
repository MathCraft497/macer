"""字节码反汇编"""
import struct
from .opcodes import Op, OP_INFO
from .constant_pool import ConstantPool, ConstTag
from .class_table import ClassTable


class Disassembler:
    def __init__(self, cp: ConstantPool, ct: ClassTable, code: bytes):
        self.cp = cp
        self.ct = ct
        self.code = code

    def disassemble(self) -> str:
        lines = []

        # 常量池
        lines.append("; === 常量池 ===")
        for i, c in enumerate(self.cp.constants):
            lines.append(f"  #{i}  {c.tag.name:12}  {self._const_str(c)}")
        lines.append("")

        # 类表
        lines.append("; === 类表 ===")
        for i, cls in enumerate(self.ct.classes):
            name = self.cp.resolve_string(cls.name_idx)
            parent = ("<无>" if cls.parent_idx == 0xFFFF
                      else self.cp.resolve_string(cls.parent_idx))
            lines.append(f"class {name}  extends {parent}:")
            for f in cls.fields:
                fn = self.cp.resolve_string(f.name_idx)
                ft = self.cp.resolve_string(f.type_idx)
                lines.append(f"    field {fn}: {ft}")
            for m in cls.methods:
                mn = self.cp.resolve_string(m.name_idx)
                md = self.cp.resolve_string(m.descriptor_idx)
                lines.append(f"    method {mn} {md}  "
                             f"(offset={m.code_offset}, len={m.code_length})")
            lines.append("")
        lines.append("")

        # 函数
        lines.append("; === 函数表 ===")
        for i, fn in enumerate(self.ct.functions):
            name = self.cp.resolve_string(fn.name_idx)
            d = self.cp.resolve_string(fn.descriptor_idx)
            lines.append(f"function {name} {d}  "
                         f"(offset={fn.code_offset}, len={fn.code_length})")
        lines.append("")

        # 代码段
        lines.append("; === 代码段 ===")
        lines.extend(self._disasm_code())
        return "\n".join(lines)

    def _const_str(self, c) -> str:
        if c.tag == ConstTag.STRING:
            return repr(c.value)
        if c.tag == ConstTag.INT:
            return str(c.value)
        if c.tag == ConstTag.FLOAT:
            return repr(c.value)
        if c.tag == ConstTag.BOOL:
            return str(c.value)
        if c.tag == ConstTag.CHAR:
            return repr(c.value)
        if c.tag == ConstTag.CLASS_REF:
            return f"class -> #{c.parts[0]} ({self.cp.resolve_string(c.parts[0])})"
        if c.tag == ConstTag.FIELD_REF:
            cls = self.cp.resolve_string(c.parts[0])
            n = self.cp.resolve_string(c.parts[1])
            t = self.cp.resolve_string(c.parts[2])
            return f"field {cls}.{n}: {t}"
        if c.tag == ConstTag.METHOD_REF:
            cls = self.cp.resolve_string(c.parts[0])
            n = self.cp.resolve_string(c.parts[1])
            d = self.cp.resolve_string(c.parts[2])
            return f"method {cls}.{n} {d}"
        if c.tag == ConstTag.FUNC_REF:
            n = self.cp.resolve_string(c.parts[0])
            d = self.cp.resolve_string(c.parts[1])
            return f"func {n} {d}"
        return str(c.value)

    def _disasm_code(self):
        lines = []
        pos = 0
        while pos < len(self.code):
            start = pos
            op_val = self.code[pos]; pos += 1
            try:
                op = Op(op_val)
            except ValueError:
                lines.append(f"  {start:04X}: <未知指令 0x{op_val:02X}>")
                continue
            info = OP_INFO[op]
            operands = []
            for fmt in info.operand_sizes:
                if fmt == "u1":
                    v = self.code[pos]; pos += 1
                elif fmt == "u2":
                    v = struct.unpack_from(">H", self.code, pos)[0]; pos += 2
                elif fmt == "s2":
                    v = struct.unpack_from(">h", self.code, pos)[0]; pos += 2
                else:
                    v = None
                operands.append(v)

            ops_str = "  ".join(str(v) for v in operands)
            comment = self._op_comment(op, operands)
            line = f"  {start:04X}: {info.name:20} {ops_str}"
            if comment:
                line += f"    ; {comment}"
            lines.append(line)
        return lines

    def _op_comment(self, op, operands):
        if op == Op.LOAD_CONST and operands:
            idx = operands[0]
            try:
                c = self.cp.get(idx)
                return self._const_str(c)
            except Exception:
                return ""
        if op == Op.INVOKE and operands:
            idx = operands[0]
            try:
                c = self.cp.get(idx)
                return self._const_str(c)
            except Exception:
                return ""
        if op == Op.JUMP and operands:
            return f"-> {operands[0]:+d}"
        if op == Op.JUMP_IF_FALSE and operands:
            return f"-> {operands[0]:+d}"
        return ""