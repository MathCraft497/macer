"""Macer 字节码指令集定义"""
from enum import IntEnum
from dataclasses import dataclass
from typing import Tuple


class Op(IntEnum):
    # 无操作
    NOP = 0x00

    # 常量
    LOAD_CONST = 0x02      # u2 index
    LOAD_TRUE = 0x03
    LOAD_FALSE = 0x04
    LOAD_NULL = 0x05

    # 变量
    LOAD_LOCAL = 0x10      # u1 slot
    STORE_LOCAL = 0x11     # u1 slot
    LOAD_FIELD = 0x12      # u2 field_idx
    STORE_FIELD = 0x13     # u2 field_idx
    LOAD_GLOBAL = 0x14     # u2 name_idx
    STORE_GLOBAL = 0x15    # u2 name_idx

    # 对象 / 数组
    NEW = 0x20             # u2 class_idx
    NEW_ARRAY = 0x21       # u1 elem_type
    CHECK_CAST = 0x22      # u2 class_idx

    # 调用
    INVOKE = 0x30          # u2 method_ref
    INVOKE_STATIC = 0x31   # u2 func_ref
    INVOKE_OP = 0x32       # u1 op_code
    INVOKE_INDEX_GET = 0x33
    INVOKE_INDEX_SET = 0x34
    RETURN = 0x35
    RETURN_VOID = 0x36

    # 分支
    JUMP = 0x40            # s2 offset
    JUMP_IF_FALSE = 0x41   # s2 offset
    JUMP_IF_TRUE = 0x42    # s2 offset

    # 算术
    ADD = 0x50
    SUB = 0x51
    MUL = 0x52
    DIV = 0x53
    MOD = 0x54
    NEG = 0x55
    NOT = 0x56

    # 比较
    EQ = 0x60
    NEQ = 0x61
    LT = 0x62
    GT = 0x63
    LE = 0x64
    GE = 0x65

    # 栈
    POP = 0x70
    DUP = 0x71
    SWAP = 0x72

    # 内置
    PRINT = 0x80


@dataclass(frozen=True)
class OpInfo:
    """指令元数据"""
    name: str
    operand_sizes: Tuple[str, ...] = ()   # ("u1",) / ("u2",) / ("s2",)
    stack_pop: int = 0
    stack_push: int = 0


# 指令元数据表（用于反汇编 / 校验）
OP_INFO = {
    Op.NOP:            OpInfo("NOP"),

    Op.LOAD_CONST:     OpInfo("LOAD_CONST", ("u2",), 0, 1),
    Op.LOAD_TRUE:      OpInfo("LOAD_TRUE", (), 0, 1),
    Op.LOAD_FALSE:     OpInfo("LOAD_FALSE", (), 0, 1),
    Op.LOAD_NULL:      OpInfo("LOAD_NULL", (), 0, 1),

    Op.LOAD_LOCAL:     OpInfo("LOAD_LOCAL", ("u1",), 0, 1),
    Op.STORE_LOCAL:    OpInfo("STORE_LOCAL", ("u1",), 1, 0),
    Op.LOAD_FIELD:     OpInfo("LOAD_FIELD", ("u2",), 1, 1),
    Op.STORE_FIELD:    OpInfo("STORE_FIELD", ("u2",), 2, 0),
    Op.LOAD_GLOBAL:    OpInfo("LOAD_GLOBAL", ("u2",), 0, 1),
    Op.STORE_GLOBAL:   OpInfo("STORE_GLOBAL", ("u2",), 1, 0),

    Op.NEW:            OpInfo("NEW", ("u2",), 0, 1),
    Op.NEW_ARRAY:      OpInfo("NEW_ARRAY", ("u1",), 1, 1),
    Op.CHECK_CAST:     OpInfo("CHECK_CAST", ("u2",), 1, 1),

    Op.INVOKE:         OpInfo("INVOKE", ("u2",), -1, 1),        # 变长参数
    Op.INVOKE_STATIC:  OpInfo("INVOKE_STATIC", ("u2",), -1, 1),
    Op.INVOKE_OP:      OpInfo("INVOKE_OP", ("u1",), -1, 1),
    Op.INVOKE_INDEX_GET: OpInfo("INVOKE_INDEX_GET", (), 2, 1),
    Op.INVOKE_INDEX_SET: OpInfo("INVOKE_INDEX_SET", (), 3, 0),
    Op.RETURN:         OpInfo("RETURN", (), 1, 0),
    Op.RETURN_VOID:    OpInfo("RETURN_VOID", (), 0, 0),

    Op.JUMP:           OpInfo("JUMP", ("s2",), 0, 0),
    Op.JUMP_IF_FALSE:  OpInfo("JUMP_IF_FALSE", ("s2",), 1, 0),
    Op.JUMP_IF_TRUE:   OpInfo("JUMP_IF_TRUE", ("s2",), 1, 0),

    Op.ADD:            OpInfo("ADD", (), 2, 1),
    Op.SUB:            OpInfo("SUB", (), 2, 1),
    Op.MUL:            OpInfo("MUL", (), 2, 1),
    Op.DIV:            OpInfo("DIV", (), 2, 1),
    Op.MOD:            OpInfo("MOD", (), 2, 1),
    Op.NEG:            OpInfo("NEG", (), 1, 1),
    Op.NOT:            OpInfo("NOT", (), 1, 1),

    Op.EQ:             OpInfo("EQ", (), 2, 1),
    Op.NEQ:            OpInfo("NEQ", (), 2, 1),
    Op.LT:             OpInfo("LT", (), 2, 1),
    Op.GT:             OpInfo("GT", (), 2, 1),
    Op.LE:             OpInfo("LE", (), 2, 1),
    Op.GE:             OpInfo("GE", (), 2, 1),

    Op.POP:            OpInfo("POP", (), 1, 0),
    Op.DUP:            OpInfo("DUP", (), 1, 2),
    Op.SWAP:           OpInfo("SWAP", (), 2, 2),

    Op.PRINT:          OpInfo("PRINT", (), 1, 0),
}


# 运算符重载映射（用于 INVOKE_OP 的操作数）
class OpOverload(IntEnum):
    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4
    MOD = 5
    EQ = 6
    NEQ = 7
    LT = 8
    GT = 9
    LE = 10
    GE = 11
    NEG = 12
    NOT = 13


OP_OVERLOAD_TO_NAME = {
    OpOverload.ADD: "opr+",
    OpOverload.SUB: "opr-",
    OpOverload.MUL: "opr*",
    OpOverload.DIV: "opr/",
    OpOverload.MOD: "opr%",
    OpOverload.EQ: "opr==",
    OpOverload.NEQ: "opr!=",
    OpOverload.LT: "opr<",
    OpOverload.GT: "opr>",
    OpOverload.LE: "opr<=",
    OpOverload.GE: "opr>=",
    OpOverload.NEG: "opr-",       # 一元
    OpOverload.NOT: "opr!",       # 一元
}