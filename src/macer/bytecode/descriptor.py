"""类型描述符（JVM 风格）"""
from dataclasses import dataclass, field
from typing import List, Optional


# 基础类型标签
PRIMITIVE_TAGS = {
    "I": "Int",
    "F": "Float",
    "B": "Bool",
    "C": "Char",
    "V": "Void",
    "A": "Any",       # Any
}


@dataclass
class Descriptor:
    """类型描述符"""
    kind: str              # "primitive" / "class" / "array" / "method"
    name: str = ""         # 类名 / 基础类型名
    elem: Optional["Descriptor"] = None     # 数组元素类型
    params: List["Descriptor"] = field(default_factory=list)   # 方法参数
    ret: Optional["Descriptor"] = None      # 方法返回类型

    def __str__(self):
        if self.kind == "primitive":
            for k, v in PRIMITIVE_TAGS.items():
                if v == self.name:
                    return k
            return "?"
        if self.kind == "class":
            return f"L{self.name};"
        if self.kind == "array":
            return f"[{self.elem}"
        if self.kind == "method":
            ps = "".join(str(p) for p in self.params)
            return f"({ps}){self.ret}"
        return "?"

    @staticmethod
    def primitive(name: str) -> "Descriptor":
        return Descriptor("primitive", name)

    @staticmethod
    def class_(name: str) -> "Descriptor":
        return Descriptor("class", name)

    @staticmethod
    def array(elem: "Descriptor") -> "Descriptor":
        return Descriptor("array", elem=elem)

    @staticmethod
    def method(params: List["Descriptor"], ret: "Descriptor") -> "Descriptor":
        return Descriptor("method", params=params, ret=ret)


def parse_descriptor(s: str) -> Descriptor:
    """解析描述符字符串"""
    d, pos = _parse_one(s, 0)
    if pos != len(s):
        raise ValueError(f"描述符未完全解析: {s} at {pos}")
    return d


def _parse_one(s: str, pos: int) -> (Descriptor, int):
    if pos >= len(s):
        raise ValueError(f"描述符提前结束: {s}")

    c = s[pos]

    # 基础类型
    if c in PRIMITIVE_TAGS:
        return Descriptor.primitive(PRIMITIVE_TAGS[c]), pos + 1

    # 数组
    if c == "[":
        elem, p = _parse_one(s, pos + 1)
        return Descriptor.array(elem), p

    # 类
    if c == "L":
        end = s.find(";", pos)
        if end < 0:
            raise ValueError(f"类描述符缺少 ;: {s}")
        name = s[pos + 1:end]
        return Descriptor.class_(name), end + 1

    # 方法
    if c == "(":
        end = s.find(")", pos)
        if end < 0:
            raise ValueError(f"方法描述符缺少 ): {s}")
        params_str = s[pos + 1:end]
        params = []
        p = 0
        while p < len(params_str):
            d, p = _parse_one(params_str, p)
            params.append(d)
        ret, p2 = _parse_one(s, end + 1)
        return Descriptor.method(params, ret), p2

    raise ValueError(f"无法解析的描述符字符 '{c}': {s}")