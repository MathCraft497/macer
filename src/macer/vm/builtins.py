"""VM 内置函数"""
import sys


class Builtins:
    @staticmethod
    def print(*args):
        out = []
        for a in args:
            out.append(Builtins.to_display(a))
        sys.stdout.write(" ".join(out) + "\n")

    @staticmethod
    def to_display(v):
        """把 VM 值转成显示字符串"""
        if v is None:
            return "null"
        if v is True:
            return "true"
        if v is False:
            return "false"
        return str(v)

    @staticmethod
    def len_(v):
        return len(v)