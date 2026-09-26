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
        all_classes = []
        top_funcs = []
        for unit in self.units:
            pkg = unit.package
            for d in unit.program.declarations:
                if isinstance(d, ast.ClassDecl):
                    fqn = f"{pkg}.{d.name}" if pkg else d.name
                    all_classes.append((fqn, d))
                elif isinstance(d, ast.FuncDecl):
                    fqn = f"{pkg}.{d.name}" if pkg else d.name
                    top_funcs.append((fqn, d))

        # 2. 占位：类表 + 方法表
        for fqn, cls in all_classes:
            name_idx = self.writer.cp.add_string(fqn)
            parent_idx = 0xFFFF
            cls_idx = self.writer.ct.add_class(name_idx, parent_idx)
            self.class_map[fqn] = cls_idx

            # 字段
            for f in cls.fields:
                fn_idx = self.writer.cp.add_string(f.name)
                ft_idx = self.writer.cp.add_string(str(f.type_node))
                self.writer.ct.add_field(cls_idx, fn_idx, ft_idx, 1)

            # 方法签名
            for m in cls.methods:
                mname_idx = self.writer.cp.add_string(m.name)
                mdesc = self._make_method_descriptor(m)
                mdesc_idx = self.writer.cp.add_string(mdesc)
                self.writer.ct.add_method(cls_idx, mname_idx, mdesc_idx,
                                           code_offset=0, code_length=0,
                                           local_count=0)

        # 3. 先占位（code_offset=0）
        for fqn, fn in top_funcs:
            name_idx = self.writer.cp.add_string(fn.name)
            desc = self._make_descriptor(fn)
            desc_idx = self.writer.cp.add_string(desc)
            func_idx = self.writer.ct.add_function(
                name_idx, desc_idx,
                code_offset=0, code_length=0, local_count=0,
            )
            self.func_map[fqn] = func_idx  # ★ 关键！

        # 4. 生成方法体
        for fqn, cls in all_classes:
                cls_idx = self.class_map[fqn]
                for mi, m in enumerate(cls.methods):
                    self._gen_method(fqn, cls_idx, mi, m)

        # 5. 逐个生成函数体，回填
        for fqn, fn in top_funcs:
            func_idx = self.func_map[fqn]
            self._gen_function(fqn, fn, func_idx)

        # 6. entry_main
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

    def _gen_method(self, cls_fqn, cls_idx, method_idx, m):
        self._reset_locals(m, is_method=True)
        code_start = self.writer.code_offset
        for st in m.body:
            self._gen_stmt(st)
        self._auto_return(m.return_type)
        code_end = self.writer.code_offset
        # 回填
        md = self.writer.ct.classes[cls_idx].methods[method_idx]
        md.code_offset = code_start
        md.code_length = code_end - code_start
        md.local_count = self.next_slot

    def _reset_locals(self, fn, is_method=False):
        self.local_slots = {}
        self.next_slot = 0
        if is_method:
            self.local_slots["self"] = 0
            self.next_slot = 1
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

    def _make_method_descriptor(self, m):
        # 和 _make_descriptor 一样，但 self 不算参数
        params = [self._type_to_desc(p.type_node) for p in m.params]
        ret = self._type_to_desc(m.return_type)
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

        if isinstance(e, ast.SelfExpr):
            self.writer.emit(Op.LOAD_LOCAL, 0)
            return

        if isinstance(e, ast.NewExpr):
            cls_idx = self.class_map.get(e.class_name)
            if cls_idx is None:
                # 尝试查找（简单名匹配）
                for k in self.class_map:
                    if k.endswith("." + e.class_name):
                        cls_idx = self.class_map[k]
                        break
            if cls_idx is None:
                raise BytecodeCodeGenError(f"未知类: {e.class_name}")

            # NEW
            self.writer.emit(Op.NEW, cls_idx)
            self.writer.emit(Op.DUP)  # 保存 obj 引用

            # 压参数
            for a in e.args:
                self._gen_expr(a)

            # 调 init
            init_ref = self._resolve_init_method_ref(cls_idx)
            if init_ref is not None:
                self.writer.emit(Op.INVOKE, init_ref)

            return

        if isinstance(e, ast.FieldAccess):
            # obj.field
            self._gen_expr(e.obj)
            field_ref = self._resolve_field_ref(e.field)
            self.writer.emit(Op.LOAD_FIELD, field_ref)
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
            # 变量赋值
            if isinstance(e.target, ast.Ident):
                self._gen_expr(e.value)
                self.writer.emit(Op.DUP)
                slot = self.local_slots.get(e.target.name)
                if slot is None:
                    raise BytecodeCodeGenError(
                        f"未定义变量: {e.target.name}")
                self.writer.emit(Op.STORE_LOCAL, slot)
                return

            # 字段赋值：obj.field = value
            if isinstance(e.target, ast.FieldAccess):
                self._gen_expr(e.target.obj)  # obj
                self._gen_expr(e.value)  # value
                field_ref = self._resolve_field_ref(e.target.field)
                self.writer.emit(Op.STORE_FIELD, field_ref)
                return

            raise BytecodeCodeGenError(
                f"不支持的赋值目标: {type(e.target).__name__}")

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
            if isinstance(e.callee, ast.FieldAccess):
                # obj.method(args)
                self._gen_expr(e.callee.obj)  # this
                for a in e.args:
                    self._gen_expr(a)
                method_ref = self._resolve_method_ref(e.callee.field, len(e.args))
                self.writer.emit(Op.INVOKE, method_ref)
                return
            self._gen_call(e)
            return

        raise BytecodeCodeGenError(
            f"阶段 3.1 暂不支持的表达式：{type(e).__name__}")

    def _resolve_method_ref(self, method_name, n_args):
        """按名字 + 参数个数找方法"""
        from .bytecode.descriptor import parse_descriptor
        for fqn, cls_idx in self.class_map.items():
            cls = self.writer.ct.classes[cls_idx]
            for m in cls.methods:
                name = self.writer.cp.resolve_string(m.name_idx)
                if name != method_name:
                    continue
                desc = self.writer.cp.resolve_string(m.descriptor_idx)
                d = parse_descriptor(desc)
                if len(d.params) == n_args:
                    return self.writer.cp.add_method_ref(fqn, method_name, desc)
        raise BytecodeCodeGenError(
            f"未知方法: {method_name}/{n_args}")

    def _resolve_field_ref(self, field_name):
        # 简化：假设 obj 是 self 或 new 的类
        # 直接从常量池找匹配的 FIELD_REF
        # 阶段 3 简化：找任意类里的同名字段
        for fqn, cls_idx in self.class_map.items():
            cls = self.writer.ct.classes[cls_idx]
            for f in cls.fields:
                fn = self.writer.cp.resolve_string(f.name_idx)
                if fn == field_name:
                    ft = self.writer.cp.resolve_string(f.type_idx)
                    return self.writer.cp.add_field_ref(fqn, field_name, ft)
        raise BytecodeCodeGenError(f"未知字段: {field_name}")

    def _resolve_init_method_ref(self, cls_idx):
        cls = self.writer.ct.classes[cls_idx]
        for m in cls.methods:
            name = self.writer.cp.resolve_string(m.name_idx)
            if name == "init":
                # 找常量池里的 METHOD_REF
                cls_name = self.writer.cp.resolve_string(cls.name_idx)
                desc = self.writer.cp.resolve_string(m.descriptor_idx)
                return self.writer.cp.add_method_ref(cls_name, "init", desc)
        return None


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