"""Macer 虚拟机 —— 栈式执行引擎（阶段 2 最小版）"""
import struct

from ..bytecode import Op, OP_INFO, ConstTag
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
        """执行 main 或指定方法"""
        if method_idx is None:
            method_idx = self.entry_main

        # 找方法
        method, code_start, code_len, local_count = self._resolve_entry(method_idx)
        if method is None:
            raise VMError("MCE5006", "找不到 main 方法")

        frame = Frame(code_start, local_count, this=None, method_ref=method)
        frame.code_end = code_start + code_len

        # 参数放局部变量
        for i, a in enumerate(args):
            if i < local_count:
                frame.locals[i] = a

        self.frames.append(frame)
        self._exec_loop()
        return frame.return_value

    def _resolve_entry(self, method_idx):
        """找 main 方法（第一个类里的第 method_idx 个方法）"""
        # 简单策略：找所有类里的第一个方法（或 main）
        for cls in self.ct.classes:
            for i, m in enumerate(cls.methods):
                name = self.cp.resolve_string(m.name_idx)
                if name == "main":
                    return m, m.code_offset, m.code_length, m.local_count
        # 没有 main，用第一个方法
        for cls in self.ct.classes:
            if cls.methods:
                m = cls.methods[0]
                return m, m.code_offset, m.code_length, m.local_count
        # 顶层函数
        for fn in self.ct.functions:
            name = self.cp.resolve_string(fn.name_idx)
            if name == "main":
                return fn, fn.code_offset, fn.code_length, fn.local_count
        if self.ct.functions:
            fn = self.ct.functions[0]
            return fn, fn.code_offset, fn.code_length, fn.local_count
        return None, 0, 0, 0

    # ============================================================
    # 主循环
    # ============================================================
    def _exec_loop(self):
        while self.frames:
            frame = self.frames[-1]

            # 到达代码尾 → 返回
            if frame.code_end is not None and frame.pc >= frame.code_end:
                self.frames.pop()
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
            b = stack.pop("ADD")
            a = stack.pop("ADD")
            stack.push(self._op_add(a, b))

        elif op == Op.SUB:
            b = stack.pop("SUB")
            a = stack.pop("SUB")
            stack.push(self._op_sub(a, b))

        elif op == Op.MUL:
            b = stack.pop("MUL")
            a = stack.pop("MUL")
            stack.push(self._op_mul(a, b))

        elif op == Op.DIV:
            b = stack.pop("DIV")
            a = stack.pop("DIV")
            stack.push(self._op_div(a, b))

        elif op == Op.MOD:
            b = stack.pop("MOD")
            a = stack.pop("MOD")
            stack.push(self._op_mod(a, b))

        elif op == Op.NEG:
            a = stack.pop("NEG")
            stack.push(-a)

        elif op == Op.NOT:
            a = stack.pop("NOT")
            stack.push(not a)

        # ---------- 比较 ----------
        elif op == Op.EQ:
            b = stack.pop("EQ"); a = stack.pop("EQ")
            stack.push(self._op_eq(a, b))
        elif op == Op.NEQ:
            b = stack.pop("NEQ"); a = stack.pop("NEQ")
            stack.push(not self._op_eq(a, b))
        elif op == Op.LT:
            b = stack.pop("LT"); a = stack.pop("LT")
            stack.push(self._op_lt(a, b))
        elif op == Op.GT:
            b = stack.pop("GT"); a = stack.pop("GT")
            stack.push(self._op_lt(b, a))
        elif op == Op.LE:
            b = stack.pop("LE"); a = stack.pop("LE")
            stack.push(not self._op_lt(b, a))
        elif op == Op.GE:
            b = stack.pop("GE"); a = stack.pop("GE")
            stack.push(not self._op_lt(a, b))

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

        # ---------- 内置 ----------
        elif op == Op.PRINT:
            v = stack.pop("PRINT")
            Builtins.print(v)

        # ---------- 返回 ----------
        elif op == Op.RETURN:
            frame.return_value = stack.pop("RETURN")
            self.frames.pop()
            if self.frames:
                self.frames[-1].stack.push(frame.return_value)
            else:
                return

        elif op == Op.RETURN_VOID:
            frame.return_value = None
            self.frames.pop()
            if self.frames:
                self.frames[-1].stack.push(None)

        else:
            raise VMError("MCE5007", f"未实现的指令: {op.name}")

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
        # CLASS_REF / METHOD_REF 等——先不管
        return c.value

    # ============================================================
    # 算术辅助
    # ============================================================
    def _op_add(self, a, b):
        return a + b

    def _op_sub(self, a, b):
        return a - b

    def _op_mul(self, a, b):
        return a * b

    def _op_div(self, a, b):
        if b == 0:
            raise VMDivisionByZero()
        return a / b

    def _op_mod(self, a, b):
        if b == 0:
            raise VMDivisionByZero()
        return a % b

    def _op_eq(self, a, b):
        return a == b

    def _op_lt(self, a, b):
        return a < b