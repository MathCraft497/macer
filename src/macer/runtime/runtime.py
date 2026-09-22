"""
Macer 运行时支持
- 内置函数实现
- 运行时错误包装（绝不暴露 Python traceback）
"""
import sys
import builtins


def print(*args):        # noqa: A001
    builtins.print(*args)


def len(x):              # noqa: A001
    try:
        return builtins.len(x)
    except TypeError:
        raise MacerRuntimeErr("MCE4003",
                              f"对象不支持 len()：{type(x).__name__}")


def str(v):              # noqa: A001
    return builtins.str(v)


def int(v):              # noqa: A001
    try:
        return builtins.int(v)
    except (ValueError, TypeError):
        raise MacerRuntimeErr("MCE4099", f"无法将 {v!r} 转换为 Int")


def float(v):            # noqa: A001
    try:
        return builtins.float(v)
    except (ValueError, TypeError):
        raise MacerRuntimeErr("MCE4099", f"无法将 {v!r} 转换为 Float")


def abs(v):              # noqa: A001
    return builtins.abs(v)


class MacerRuntimeErr(Exception):
    def __init__(self, code, message, mce_line=0):
        super().__init__(message)
        self.code = code
        self.message = message
        self.mce_line = mce_line


def __macer_wrap__(entry):
    try:
        entry()
    except MacerRuntimeErr as e:
        _emit(e.code, e.message)
        sys.exit(1)
    except ZeroDivisionError:
        _emit("MCE4001", "除以零")
        sys.exit(1)
    except AttributeError as e:
        _emit("MCE4002", f"空引用访问（{e}）")
        sys.exit(1)
    except IndexError:
        _emit("MCE4003", "下标越界")
        sys.exit(1)
    except KeyError as e:
        _emit("MCE4003", f"键不存在：{e}")
        sys.exit(1)
    except AssertionError as e:
        _emit("MCE4004", f"断言失败 {e}")
        sys.exit(1)
    except RecursionError:
        _emit("MCE4005", "栈溢出（递归过深）")
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        _emit("MCE4099", f"未捕获的运行时错误：{type(e).__name__}: {e}")
        sys.exit(1)


def _emit(code, message):
    RED = "\033[1;31m" if sys.stderr.isatty() else ""
    BOLD = "\033[1m" if sys.stderr.isatty() else ""
    RESET = "\033[0m" if sys.stderr.isatty() else ""
    builtins.print(file=sys.stderr)
    builtins.print(
        f"{RED}error{RESET}{BOLD}[{code}]{RESET}: {message}",
        file=sys.stderr,
    )
