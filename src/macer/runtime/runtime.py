"""
Macer 运行时支持
- 内置函数实现
- 运行时错误包装（绝不暴露 Python traceback）
"""
import sys
import builtins


def print(*args):
    converted = []
    for a in args:
        if hasattr(a, "chars") and isinstance(a.chars, list):
            chars = []
            for c in a.chars:
                if hasattr(c, "chars") and isinstance(c.chars, list):
                    # 嵌套 String，递归
                    chars.append("".join(str(x) for x in c.chars))
                else:
                    chars.append(str(c))
            converted.append("".join(chars))
        else:
            converted.append(a)
    builtins.print(*converted)


def len(x):              # noqa: A001
    try:
        return builtins.len(x)
    except TypeError:
        raise MacerRuntimeErr("MCE4003",
                              f"对象不支持 len()：{type(x).__name__}")


def str(v):              # noqa: A001
    """转字符串——返回 String 类实例（如果存在）"""
    s = builtins.str(v)
    cls = _get_string_class()
    if cls is not None:
        return cls(list(s))
    return s


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





# ============================================================
# Char 方法实现
# ============================================================
def _char_toInt(c):
    """Char -> Int（码点）"""
    return ord(c)


def _char_toString(c):
    """Char -> String（单字符字符串）"""
    return c


def _char_toUpper(c):
    """Char -> Char（大写）"""
    return c.upper()


def _char_toLower(c):
    """Char -> Char（小写）"""
    return c.lower()




# ============================================================
# String 类包装支持
# ============================================================
_STRING_CLASS = None


def __set_string_class(cls):
    global _STRING_CLASS
    _STRING_CLASS = cls


def _get_string_class():
    return _STRING_CLASS


def _builtins_str(v):
    return builtins.str(v)


def _str_from_chars(chars):
    cls = _get_string_class()
    if cls is not None:
        return cls(list(chars))
    return "".join(chars)


def _chars_of(v):
    if hasattr(v, "chars") and isinstance(v.chars, list):
        return list(v.chars)
    if isinstance(v, str):
        return list(v)
    return list(builtins.str(v))
