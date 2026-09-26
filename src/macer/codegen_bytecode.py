"""
AST → 字节码（阶段 3.1）

支持：
- 字面量：Int / Float / Bool / String / Null
- 二元运算：+ - * / % == != < > <= >=
- 一元运算：- !
- 内置函数：print / str
- 顶层函数：func main() -> Void { ... }
"""

from . import ast_nodes as ast
from .bytecode import (
    Op, BytecodeWriter,
)
from .bytecode.descriptor import Descriptor


class BytecodeCodeGenError(Exception):
    pass


class BytecodeCodeGen:
    def __init__(self, units):
        self.units = units
        self.writer = BytecodeWriter()

        # 索引表
        self.class_map = {}          # FQN → class_idx
        self.func_map = {}           # FQN → func_idx（函数表索引）

        # 当前上下文
        self.current_func = None
        self.local_slots = {}
        self.next_slot = 0

    # ============================================================
    # 入口
    # ============================================================
    def generate(self) -> BytecodeWriter:
        # 1. 收集所有函数（阶段 3.1 只处理顶层函数）
        top_funcs = []
        for unit in self.units:
            pkg = unit.package
            for d in unit.program.declarations:
                if isinstance(d, ast.FuncDecl):
                    fqn = f"{pkg}.{d.name}" if pkg else d.name
                    top_funcs.append((fqn, d))

        # 2. 先占位（函数表按顺序加，code_offset 后填）
        # 简化：直接生成，边生成边加函数表
        for fqn, fn in top_funcs:
            self._gen_function(fqn, fn)

        # 3. 设置 entry_main
        if "main" in self.func_map:
            self.writer.entry_main = self.func_map["main"]
        elif top_funcs:
            self.writer.entry_main = self.func_map[top_funcs[0][0]]

        return self.writer

    # ============================================================
    # 函数生成
    # ============================================================
    def _gen_function(self, fqn, fn):
        self._reset_locals(fn)

        code_start = self.writer.code_offset

        # 函数体
        for st in fn.body:
            self._gen_stmt(st)

        # 自动返回
        self._auto_return(fn.return_type)

        code_end = self.writer.code_offset

        # 加函数表项
        name_idx = self.writer.cp.add_string(fn.name)
        desc = self._make_descriptor(fn)
        desc_idx = self.writer.cp.add_string(desc)

        func_idx = self.writer.ct.add_function(
            name_idx, desc_idx,
            code_offset=code_start,
            code_length=code_end - code_start,
            local_count=self.next_slot,
        )
        self.func_map[fqn] = func_idx

    def _reset_locals(self, fn):
        self.local_slots = {}
        self.next_slot = 0
        for p in fn.params:
            self.local_slots[p.name] = self.next_slot
            self.next_slot += 1

    def _alloc_local(self, name):
        if name in self.local_slots:
            return self.local_slots[name]
        slot = self.next_slot
        self.local_slots[name] = slot
        self.next_slot += 1
        return slot

    def _auto_return(self, return_type):
        if return_type.name == "Void":
            self.writer.emit(Op.RETURN_VOID)

    def _make_descriptor(self, fn):
        params = [self._type_to_desc(p.type_node) for p in fn.params]
        ret = self._type_to_desc(fn.return_type)
        return str(Descriptor.method(params, ret))

    def _type_to_desc(self, t):
        if t.is_array:
            elem = ast.TypeNode(t.name, t.generics)
            return Descriptor.array(self._type_to_desc(elem))
        if t.name in ("Int", "Float", "Bool", "Char", "Void", "Any"):
            return Descriptor.primitive(t.name)
        return Descriptor.class_(t.name)

    # ============================================================
    # 语句
    # ============================================================
    def _gen_stmt(self, s):
        if isinstance(s, ast.ExprStmt):
            self._gen_expr(s.expr)
            # 非 Void 表达式需要 POP
            if not self._is_void_expr(s.expr):
                self.writer.emit(Op.POP)
            return

        if isinstance(s, ast.ReturnStmt):
            if s.value is None:
                self.writer.emit(Op.RETURN_VOID)
            else:
                self._gen_expr(s.value)
                self.writer.emit(Op.RETURN)
            return

        if isinstance(s, ast.VarDecl):
            if s.init is not None:
                self._gen_expr(s.init)
            else:
                self.writer.emit(Op.LOAD_NULL)
            slot = self._alloc_local(s.name)
            self.writer.emit(Op.STORE_LOCAL, slot)
            return

        raise BytecodeCodeGenError(
            f"阶段 3.2 暂不支持的语句：{type(s).__name__}")

    def _is_void_expr(self, e):
        """判断表达式是否返回 Void（如 print(...)）"""
        if isinstance(e, ast.Call) and isinstance(e.callee, ast.Ident):
            if e.callee.name == "print":
                return True
        return False

    # ============================================================
    # 表达式
    # ============================================================
    def _gen_expr(self, e):
        # ---------- 字面量 ----------
        if isinstance(e, ast.IntLit):
            idx = self.writer.cp.add_int(e.value)
            self.writer.emit(Op.LOAD_CONST, idx)
            return

        if isinstance(e, ast.FloatLit):
            idx = self.writer.cp.add_float(e.value)
            self.writer.emit(Op.LOAD_CONST, idx)
            return

        if isinstance(e, ast.StringLit):
            idx = self.writer.cp.add_string(e.value)
            self.writer.emit(Op.LOAD_CONST, idx)
            return

        if isinstance(e, ast.BoolLit):
            self.writer.emit(Op.LOAD_TRUE if e.value else Op.LOAD_FALSE)
            return

        if isinstance(e, ast.NullLit):
            self.writer.emit(Op.LOAD_NULL)
            return

        if isinstance(e, ast.CharLit):
            idx = self.writer.cp.add_char(e.value)
            self.writer.emit(Op.LOAD_CONST, idx)
            return

        # ---------- 标识符 ----------
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
        if isinstance(e, ast.Binary):
            self._gen_expr(e.left)
            self._gen_expr(e.right)
            self._emit_bin_op(e.op, e)
            return

        # ---------- 一元运算 ----------
        if isinstance(e, ast.Unary):
            self._gen_expr(e.operand)
            if e.op == "-":
                self.writer.emit(Op.NEG)
            elif e.op == "!":
                self.writer.emit(Op.NOT)
            else:
                raise BytecodeCodeGenError(f"未知一元运算符: {e.op}")
            return

        # ---------- 调用 ----------
        if isinstance(e, ast.Call):
            self._gen_call(e)
            return

        raise BytecodeCodeGenError(
            f"阶段 3.1 暂不支持的表达式：{type(e).__name__}")

    def _emit_bin_op(self, op, node):
        table = {
            "+": Op.ADD, "-": Op.SUB, "*": Op.MUL,
            "/": Op.DIV, "%": Op.MOD,
            "==": Op.EQ, "!=": Op.NEQ,
            "<": Op.LT, ">": Op.GT,
            "<=": Op.LE, ">=": Op.GE,
        }
        if op in table:
            self.writer.emit(table[op])
            return
        raise BytecodeCodeGenError(
            f"阶段 3.1 暂不支持的运算符：{op}")

    # ============================================================
    # 函数调用
    # ============================================================
    def _gen_call(self, e):
        # 只支持 Ident 调用（顶层函数 / 内置）
        if not isinstance(e.callee, ast.Ident):
            raise BytecodeCodeGenError(
                "阶段 3.1 只支持 Ident 调用")

        name = e.callee.name

        # ---------- 内置 print ----------
        if name == "print":
            if len(e.args) != 1:
                raise BytecodeCodeGenError(
                    "阶段 3.1 print 只接受 1 个参数")
            self._gen_expr(e.args[0])
            self.writer.emit(Op.PRINT)
            return

        # ---------- 内置 str ----------
        if name == "str":
            if len(e.args) != 1:
                raise BytecodeCodeGenError(
                    "阶段 3.1 str 只接受 1 个参数")
            self._gen_expr(e.args[0])
            self.writer.emit(Op.TO_STRING)
            return

        raise BytecodeCodeGenError(
            f"阶段 3.1 暂不支持调用：{name}")