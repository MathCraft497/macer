"""常量池"""
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Any


class ConstTag(IntEnum):
    INT = 0x01
    FLOAT = 0x02
    STRING = 0x03
    CHAR = 0x04
    BOOL = 0x05
    NULL = 0x06
    CLASS_REF = 0x07       # u2 -> string index
    FIELD_REF = 0x08       # u2 class_idx, u2 name_idx, u2 type_idx
    METHOD_REF = 0x09      # u2 class_idx, u2 name_idx, u2 descriptor_idx
    FUNC_REF = 0x0A        # u2 name_idx, u2 descriptor_idx


@dataclass
class Constant:
    tag: ConstTag
    value: Any = None          # int/float/str/bool/None
    parts: tuple = ()          # 复合类型：多个索引


class ConstantPool:
    def __init__(self):
        self.constants: List[Constant] = []
        self._cache: dict = {}     # (tag, value) -> index（去重）

    # ---------- 添加常量 ----------
    def add(self, tag: ConstTag, value=None, parts=()) -> int:
        key = (tag, value, parts)
        if key in self._cache:
            return self._cache[key]
        idx = len(self.constants)
        self.constants.append(Constant(tag, value, parts))
        self._cache[key] = idx
        return idx

    def add_int(self, v: int) -> int:
        return self.add(ConstTag.INT, v)

    def add_float(self, v: float) -> int:
        return self.add(ConstTag.FLOAT, v)

    def add_string(self, s: str) -> int:
        return self.add(ConstTag.STRING, s)

    def add_char(self, c: str) -> int:
        return self.add(ConstTag.CHAR, c)

    def add_bool(self, b: bool) -> int:
        return self.add(ConstTag.BOOL, b)

    def add_null(self) -> int:
        return self.add(ConstTag.NULL)

    def add_class_ref(self, name: str) -> int:
        name_idx = self.add_string(name)
        return self.add(ConstTag.CLASS_REF, parts=(name_idx,))

    def add_field_ref(self, class_name: str, field_name: str,
                      field_type: str) -> int:
        c = self.add_class_ref(class_name)
        n = self.add_string(field_name)
        t = self.add_string(field_type)
        return self.add(ConstTag.FIELD_REF, parts=(c, n, t))

    def add_method_ref(self, class_name: str, method_name: str,
                       descriptor: str) -> int:
        c = self.add_class_ref(class_name)
        n = self.add_string(method_name)
        d = self.add_string(descriptor)
        return self.add(ConstTag.METHOD_REF, parts=(c, n, d))

    def add_func_ref(self, func_name: str, descriptor: str) -> int:
        n = self.add_string(func_name)
        d = self.add_string(descriptor)
        return self.add(ConstTag.FUNC_REF, parts=(n, d))

    # ---------- 查询 ----------
    def get(self, idx: int) -> Constant:
        if idx < 0 or idx >= len(self.constants):
            raise IndexError(f"常量池索引越界: {idx}")
        return self.constants[idx]

    def resolve_string(self, idx: int) -> str:
        c = self.get(idx)
        if c.tag != ConstTag.STRING:
            raise TypeError(f"常量池[{idx}] 不是字符串: {c.tag}")
        return c.value

    def __len__(self):
        return len(self.constants)