"""调用帧"""
from .stack import Stack


class Frame:
    def __init__(self, code_offset: int, local_count: int,
                 this=None, method_ref=None):
        self.pc = code_offset              # 程序计数器
        self.code_end = None               # 代码结束位置（方法代码段）
        self.locals = [None] * local_count
        self.stack = Stack()
        self.this = this                    # self
        self.method_ref = method_ref        # 当前方法引用
        self.return_value = None

    def __repr__(self):
        return (f"Frame(pc={self.pc}, locals={self.locals}, "
                f"stack_len={len(self.stack)})")