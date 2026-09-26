"""类表 / 方法表 / 字段表"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FieldDef:
    name_idx: int
    type_idx: int
    access: int = 1        # 0=private, 1=public


@dataclass
class MethodDef:
    name_idx: int
    descriptor_idx: int
    access: int = 1
    code_offset: int = 0
    code_length: int = 0
    local_count: int = 0


@dataclass
class ClassDef:
    name_idx: int
    parent_idx: int = 0xFFFF     # 无父类
    fields: List[FieldDef] = field(default_factory=list)
    methods: List[MethodDef] = field(default_factory=list)


@dataclass
class FunctionDef:
    name_idx: int
    descriptor_idx: int
    code_offset: int = 0
    code_length: int = 0
    local_count: int = 0


class ClassTable:
    def __init__(self):
        self.classes: List[ClassDef] = []
        self.functions: List[FunctionDef] = []

    def add_class(self, name_idx: int, parent_idx: int = 0xFFFF) -> int:
        idx = len(self.classes)
        self.classes.append(ClassDef(name_idx, parent_idx))
        return idx

    def add_field(self, class_idx: int, name_idx: int, type_idx: int,
                  access: int = 1) -> int:
        c = self.classes[class_idx]
        idx = len(c.fields)
        c.fields.append(FieldDef(name_idx, type_idx, access))
        return idx

    def add_method(self, class_idx: int, name_idx: int, descriptor_idx: int,
                   access: int = 1, code_offset: int = 0,
                   code_length: int = 0, local_count: int = 0) -> int:
        c = self.classes[class_idx]
        idx = len(c.methods)
        c.methods.append(MethodDef(name_idx, descriptor_idx, access,
                                   code_offset, code_length, local_count))
        return idx

    def add_function(self, name_idx: int, descriptor_idx: int,
                     code_offset: int = 0, code_length: int = 0,
                     local_count: int = 0) -> int:
        idx = len(self.functions)
        self.functions.append(FunctionDef(name_idx, descriptor_idx,
                                          code_offset, code_length,
                                          local_count))
        return idx

    # ---------- 查找（用于重载） ----------
    def find_method(self, class_idx: int, name: str, descriptor: str,
                    cp) -> Optional[MethodDef]:
        """按方法名 + 描述符精确查找（重载核心）"""
        c = self.classes[class_idx]
        for m in c.methods:
            if (cp.resolve_string(m.name_idx) == name and
                    cp.resolve_string(m.descriptor_idx) == descriptor):
                return m
        return None