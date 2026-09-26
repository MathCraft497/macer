"""VM 运行时错误"""


class VMError(Exception):
    """VM 通用错误"""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class VMStackUnderflow(VMError):
    def __init__(self, op_name: str):
        super().__init__("MCE5001",
                         f"栈下溢：指令 '{op_name}' 需要更多操作数")


class VMTypeError(VMError):
    def __init__(self, message: str):
        super().__init__("MCE5002", message)


class VMDivisionByZero(VMError):
    def __init__(self):
        super().__init__("MCE5003", "除以零")


class VMBadOpcode(VMError):
    def __init__(self, op_val: int, pc: int):
        super().__init__("MCE5004",
                         f"未知操作码 0x{op_val:02X} at pc={pc}")


class VMIndexError(VMError):
    def __init__(self, message: str):
        super().__init__("MCE5005", message)