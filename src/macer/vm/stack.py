"""操作数栈"""
from .error import VMStackUnderflow


class Stack:
    def __init__(self):
        self.items = []

    def push(self, v):
        self.items.append(v)

    def pop(self, op_name="?"):
        if not self.items:
            raise VMStackUnderflow(op_name)
        return self.items.pop()

    def peek(self, offset=0):
        if offset < 0 or offset >= len(self.items):
            raise VMStackUnderflow("peek")
        return self.items[-(offset + 1)]

    def dup(self):
        if not self.items:
            raise VMStackUnderflow("DUP")
        self.items.append(self.items[-1])

    def swap(self):
        if len(self.items) < 2:
            raise VMStackUnderflow("SWAP")
        self.items[-1], self.items[-2] = self.items[-2], self.items[-1]

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        return f"Stack({self.items})"