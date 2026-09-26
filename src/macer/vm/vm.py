"""Macer 虚拟机 —— 栈式执行引擎（阶段 3.4.1）"""
import struct

from ..bytecode import Op, OP_INFO, ConstTag
from ..bytecode.descriptor import parse_descriptor
from .error import (
    VMError, VMTypeError, VMDivisionByZero, VMBadOpcode, VMIndexError,
)
from .frame import Frame
from .builtins import Builtins


class VM:
    def __init__(self, bytecode_source):
        """
        bytecode_source:
          - BytecodeWriter 对象
          - 或含 .cp / .ct / .code 属性的对象
        """
        self.cp = bytecode_source.cp
        self.ct = bytecode_source.ct
        self.code = bytes(bytecode_source.code)
        self.frames = []
        self.entry_main = getattr(bytecode_source, "entry_main", 0)

    # ============================================================
    # 入口
    # ============================================================
    def run(self, method_idx=None, args=()):
        """执行 main 或指定函数"""
        if method_idx is None:
            method_idx = self.entry_main

        # 解析入口
        entry = self._resolve_entry(method_idx)
        if entry is None:
            raise VMError("MCE5006", "找不到 main 函数")

        code_start, code_len, local_count = entry

        frame = Frame(code_start, local_count)
        frame.code_end = code_start + code_len

        for i, a in enumerate(args):
            if i < local_count:
                frame.locals[i] = a

        self.frames.append(frame)
        self._exec_loop()
        return frame.return_value

    def _resolve_entry(self, method_idx):
        """返回 (code_offset, code_length, local_count)"""
        # 优先顶层函数
        if self.ct.functions:
            # 找 main
            for fd in self.ct.functions:
                name = self.cp.resolve_string(fd.name_idx)
                if name == "main":
                    return fd.code_offset, fd.code_length, fd.local_count
            # 无 main，用第一个
            fd = self.ct.functions[0]
            return fd.code_offset, fd.code_length, fd.local_count

        # 没函数，看类方法
        for cls in self.ct.classes:
            for m in cls.methods:
                name = self.cp.resolve_string(m.name_idx)
                if name == "main":
                    return m.code_offset, m.code_length, m.local_count
            if cls.methods:
                m = cls.methods[0]
                return m.code_offset, m.code_length, m.local_count

        return None

    # ============================================================
    # 主循环
    # ============================================================
    def _exec_loop(self):
        while self.frames:
            frame = self.frames[-1]

            # 到达代码尾 → 返回
            if frame.code_end is not None and frame.pc >= frame.code_end:
                self.frames.pop()
                if self.frames:
                    self.frames[-1].stack.push(None)
                continue

            if frame.pc >= len(self.code):
                self.frames.pop()
                continue

            op_val = self.code[frame.pc]
            frame.pc += 1

            try:
                op = Op(op_val)
            except ValueError:
                raise VMBadOpcode(op_val, frame.pc - 1)

            self._dispatch(op, frame)

    # ============================================================
    # 指令分发
    # ============================================================
    def _dispatch(self, op, frame):
        stack = frame.stack

        # ---------- 无操作 ----------
        if op == Op.NOP:
            pass

        # ---------- 常量 ----------
        elif op == Op.LOAD_CONST:
            idx = self._read_u2(frame)
            c = self.cp.get(idx)
            stack.push(self._const_value(c))

        elif op == Op.LOAD_TRUE:
            stack.push(True)
        elif op == Op.LOAD_FALSE:
            stack.push(False)
        elif op == Op.LOAD_NULL:
            stack.push(None)

        # ---------- 变量 ----------
        elif op == Op.LOAD_LOCAL:
            slot = self._read_u1(frame)
            if slot >= len(frame.locals):
                raise VMIndexError(f"局部变量槽越界: {slot}")
            stack.push(frame.locals[slot])

        elif op == Op.STORE_LOCAL:
            slot = self._read_u1(frame)
            if slot >= len(frame.locals):
                raise VMIndexError(f"局部变量槽越界: {slot}")
            frame.locals[slot] = stack.pop("STORE_LOCAL")

        # ---------- 算术 ----------
        elif op == Op.ADD:
            b = stack.pop("ADD"); a = stack.pop("ADD")
            stack.push(a + b)
        elif op == Op.SUB:
            b = stack.pop("SUB"); a = stack.pop("SUB")
            stack.push(a - b)
        elif op == Op.MUL:
            b = stack.pop("MUL"); a = stack.pop("MUL")
            stack.push(a * b)
        elif op == Op.DIV:
            b = stack.pop("DIV"); a = stack.pop("DIV")
            if b == 0:
                raise VMDivisionByZero()
            stack.push(a / b)
        elif op == Op.MOD:
            b = stack.pop("MOD"); a = stack.pop("MOD")
            if b == 0:
                raise VMDivisionByZero()
            stack.push(a % b)
        elif op == Op.NEG:
            a = stack.pop("NEG")
            stack.push(-a)
        elif op == Op.NOT:
            a = stack.pop("NOT")
            stack.push(not a)

        # ---------- 比较 ----------
        elif op == Op.EQ:
            b = stack.pop("EQ"); a = stack.pop("EQ")
            stack.push(a == b)
        elif op == Op.NEQ:
            b = stack.pop("NEQ"); a = stack.pop("NEQ")
            stack.push(a != b)
        elif op == Op.LT:
            b = stack.pop("LT"); a = stack.pop("LT")
            stack.push(a < b)
        elif op == Op.GT:
            b = stack.pop("GT"); a = stack.pop("GT")
            stack.push(a > b)
        elif op == Op.LE:
            b = stack.pop("LE"); a = stack.pop("LE")
            stack.push(a <= b)
        elif op == Op.GE:
            b = stack.pop("GE"); a = stack.pop("GE")
            stack.push(a >= b)

        # ---------- 分支 ----------
        elif op == Op.JUMP:
            offset = self._read_s2(frame)
            frame.pc += offset

        elif op == Op.JUMP_IF_FALSE:
            offset = self._read_s2(frame)
            cond = stack.pop("JUMP_IF_FALSE")
            if not cond:
                frame.pc += offset

        elif op == Op.JUMP_IF_TRUE:
            offset = self._read_s2(frame)
            cond = stack.pop("JUMP_IF_TRUE")
            if cond:
                frame.pc += offset

        # ---------- 栈 ----------
        elif op == Op.POP:
            stack.pop("POP")
        elif op == Op.DUP:
            stack.dup()
        elif op == Op.SWAP:
            stack.swap()

        # ---------- 函数调用 ----------
        elif op == Op.INVOKE_STATIC:
            func_idx = self._read_u2(frame)
            self._do_invoke_static(func_idx, frame)

        # ---------- 内置 ----------
        elif op == Op.PRINT:
            v = stack.pop("PRINT")
            Builtins.print(v)

        elif op == Op.TO_STRING:
            v = stack.pop("TO_STRING")
            stack.push(Builtins.to_display(v))

        # ---------- 返回 ----------
        elif op == Op.RETURN:
            frame.return_value = stack.pop("RETURN")
            self.frames.pop()
            if self.frames:
                self.frames[-1].stack.push(frame.return_value)

        elif op == Op.RETURN_VOID:
            frame.return_value = None
            self.frames.pop()
            # Void 不压栈

        else:
            raise VMError("MCE5007", f"未实现的指令: {op.name}")

    # ============================================================
    # 静态函数调用
    # ============================================================
    def _do_invoke_static(self, func_idx, caller_frame):
        if func_idx >= len(self.ct.functions):
            raise VMError("MCE5008", f"函数索引越界: {func_idx}")

        fd = self.ct.functions[func_idx]
        desc_str = self.cp.resolve_string(fd.descriptor_idx)
        desc = parse_descriptor(desc_str)

        n_params = len(desc.params) if desc.kind == "method" else 0

        # 弹参数（逆序）
        args = []
        for _ in range(n_params):
            args.append(caller_frame.stack.pop("INVOKE_STATIC"))
        args.reverse()

        # 建新帧
        new_frame = Frame(fd.code_offset, fd.local_count,
                          this=None, method_ref=fd)
        new_frame.code_end = fd.code_offset + fd.code_length
        for i, a in enumerate(args):
            if i < len(new_frame.locals):
                new_frame.locals[i] = a

        self.frames.append(new_frame)

    # ============================================================
    # 读取操作数
    # ============================================================
    def _read_u1(self, frame):
        v = self.code[frame.pc]
        frame.pc += 1
        return v

    def _read_u2(self, frame):
        v = struct.unpack_from(">H", self.code, frame.pc)[0]
        frame.pc += 2
        return v

    def _read_s2(self, frame):
        v = struct.unpack_from(">h", self.code, frame.pc)[0]
        frame.pc += 2
        return v

    # ============================================================
    # 常量值
    # ============================================================
    def _const_value(self, c):
        if c.tag == ConstTag.INT:
            return c.value
        if c.tag == ConstTag.FLOAT:
            return c.value
        if c.tag == ConstTag.STRING:
            return c.value
        if c.tag == ConstTag.CHAR:
            return c.value
        if c.tag == ConstTag.BOOL:
            return c.value
        if c.tag == ConstTag.NULL:
            return None
        return c.value