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

        self.current_unit = None

    # ============================================================
    # 入口
    # ============================================================
    def generate(self) -> BytecodeWriter:
        # 1. 收集所有顶层函数
        top_funcs = []
        for unit in self.units:
            pkg = unit.package
            for d in unit.program.declarations:
                if isinstance(d, ast.FuncDecl):
                    fqn = f"{pkg}.{d.name}" if pkg else d.name
                    top_funcs.append((fqn, d))

        # 2. 先占位（code_offset=0）
        for fqn, fn in top_funcs:
            name_idx = self.writer.cp.add_string(fn.name)
            desc = self._make_descriptor(fn)
            desc_idx = self.writer.cp.add_string(desc)
            func_idx = self.writer.ct.add_function(
                name_idx, desc_idx,
                code_offset=0, code_length=0, local_count=0,
            )
            self.func_map[fqn] = func_idx  # ★ 关键！

        # 3. 逐个生成函数体，回填
        for fqn, fn in top_funcs:
            func_idx = self.func_map[fqn]
            self._gen_function(fqn, fn, func_idx)

        # 4. entry_main
        if "main" in self.func_map:
            self.writer.entry_main = self.func_map["main"]
        elif top_funcs:
            self.writer.entry_main = self.func_map[top_funcs[0][0]]

        return self.writer

    # ============================================================
    # 函数生成
    # ============================================================
    def _gen_function(self, fqn, fn, func_idx):
        """生成函数体，回填函数表的 code_offset"""
        self._reset_locals(fn)

        code_start = self.writer.code_offset

        # 函数体
        for st in fn.body:
            self._gen_stmt(st)

        # 自动返回
        self._auto_return(fn.return_type)

        code_end = self.writer.code_offset

        # 回填函数表
        fd = self.writer.ct.functions[func_idx]
        fd.code_offset = code_start
        fd.code_length = code_end - code_start
        fd.local_count = self.next_slot

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

        if isinstance(s, ast.IfStmt):
            self._gen_expr(s.cond)

            # JUMP_IF_FALSE → else
            jf_pos = self.writer.code_offset
            self.writer.emit(Op.JUMP_IF_FALSE, 0)  # 占位

            for st in s.then_body:
                self._gen_stmt(st)

            if s.else_body:
                # then 结束跳 end
                jend_pos = self.writer.code_offset
                self.writer.emit(Op.JUMP, 0)  # 占位

                # 回填 JUMP_IF_FALSE → else 起点
                else_start = self.writer.code_offset
                self._patch_s2(jf_pos, else_start - (jf_pos + 3))

                for st in s.else_body:
                    self._gen_stmt(st)

                # 回填 JUMP → end
                end = self.writer.code_offset
                self._patch_s2(jend_pos, end - (jend_pos + 3))
            else:
                # 无 else：JUMP_IF_FALSE 跳到 then 结束
                end = self.writer.code_offset
                self._patch_s2(jf_pos, end - (jf_pos + 3))
            return

        if isinstance(s, ast.WhileStmt):
            loop_start = self.writer.code_offset
            self._gen_expr(s.cond)

            jf_pos = self.writer.code_offset
            self.writer.emit(Op.JUMP_IF_FALSE, 0)  # 占位

            for st in s.body:
                self._gen_stmt(st)

            # 回跳
            jump_pos = self.writer.code_offset
            back = loop_start - (jump_pos + 3)
            self.writer.emit(Op.JUMP, back)

            # 回填 JUMP_IF_FALSE → 当前位置
            end = self.writer.code_offset
            self._patch_s2(jf_pos, end - (jf_pos + 3))
            return

        if isinstance(s, ast.Block):
            for st in s.body:
                self._gen_stmt(st)
            return

        raise BytecodeCodeGenError(
            f"阶段 3.2 暂不支持的语句：{type(s).__name__}")

    def _is_void_expr(self, e):
        """判断表达式是否返回 Void（如 print(...)）"""
        if isinstance(e, ast.Call) and isinstance(e.callee, ast.Ident):
            if e.callee.name == "print":
                return True
        return False

    def _patch_s2(self, pos, value):
        """回填 s2 操作数（pos 是 jump 指令起始）"""
        import struct
        struct.pack_into(">h", self.writer.code, pos + 1, value)

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

        # ---------- 用户函数 ----------
        # 拼 FQN 查找
        unit = self.current_unit
        fqn = None
        if unit and unit.package:
            candidate = f"{unit.package}.{name}"
            if candidate in self.func_map:
                fqn = candidate
        if fqn is None and name in self.func_map:
            fqn = name
        if fqn is None:
            # 遍历所有 key，找简单名匹配
            for k in self.func_map:
                if k == name or k.endswith("." + name):
                    fqn = k
                    break

        if fqn is not None:
            # 压参数
            for a in e.args:
                self._gen_expr(a)
            func_idx = self.func_map[fqn]
            self.writer.emit(Op.INVOKE_STATIC, func_idx)
            return

        raise BytecodeCodeGenError(
            f"阶段 3.1 暂不支持调用：{name}")