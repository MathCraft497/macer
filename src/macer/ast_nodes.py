from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class TypeNode:
    name: str
    generics: List["TypeNode"] = field(default_factory=list)
    is_array: bool = False
    array_dims: int = 0

    def __str__(self):
        base = self.name
        if self.generics:
            base += f"<{', '.join(str(g) for g in self.generics)}>"
        if self.is_array:
            base += "[]" * self.array_dims
        return base


class Expr:
    line: int = 0
    col: int = 0


@dataclass
class IntLit(Expr):
    value: int
    line: int = 0
    col: int = 0


@dataclass
class FloatLit(Expr):
    value: float
    line: int = 0
    col: int = 0


@dataclass
class StringLit(Expr):
    value: str
    line: int = 0
    col: int = 0


@dataclass
class BoolLit(Expr):
    value: bool
    line: int = 0
    col: int = 0


@dataclass
class NullLit(Expr):
    line: int = 0
    col: int = 0


@dataclass
class Ident(Expr):
    name: str
    line: int = 0
    col: int = 0


@dataclass
class SelfExpr(Expr):
    line: int = 0
    col: int = 0


@dataclass
class NewExpr(Expr):
    class_name: str
    args: List[Expr]
    line: int = 0
    col: int = 0


@dataclass
class Binary(Expr):
    op: str
    left: Expr
    right: Expr
    line: int = 0
    col: int = 0


@dataclass
class Unary(Expr):
    op: str
    operand: Expr
    line: int = 0
    col: int = 0


@dataclass
class Call(Expr):
    callee: Expr
    args: List[Expr]
    line: int = 0
    col: int = 0
    is_string_method: bool = False


@dataclass
class FieldAccess(Expr):
    obj: Expr
    field: str
    line: int = 0
    col: int = 0


@dataclass
class Assign(Expr):
    target: Expr
    value: Expr
    line: int = 0
    col: int = 0


@dataclass
class SliceStringExpr(Expr):
    raw: str
    line: int = 0
    col: int = 0


@dataclass
class IndexExpr(Expr):
    obj: Expr
    index: Expr
    line: int = 0
    col: int = 0


@dataclass
class IndexAssign(Expr):
    obj: Expr
    index: Expr
    value: Expr
    line: int = 0
    col: int = 0


class Stmt:
    line: int = 0
    col: int = 0


@dataclass
class VarDecl(Stmt):
    name: str
    type_node: TypeNode
    init: Optional[Expr]
    mutable: bool = True
    line: int = 0
    col: int = 0


@dataclass
class ExprStmt(Stmt):
    expr: Expr
    line: int = 0
    col: int = 0


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]
    line: int = 0
    col: int = 0


@dataclass
class IfStmt(Stmt):
    cond: Expr
    then_body: List[Stmt]
    else_body: Optional[List[Stmt]]
    line: int = 0
    col: int = 0


@dataclass
class WhileStmt(Stmt):
    cond: Expr
    body: List[Stmt]
    line: int = 0
    col: int = 0


@dataclass
class Block(Stmt):
    body: List[Stmt]
    line: int = 0
    col: int = 0


@dataclass
class Param:
    name: str
    type_node: TypeNode


@dataclass
class FuncDecl:
    name: str
    params: List[Param]
    return_type: TypeNode
    body: List[Stmt]
    is_method: bool = False
    is_public: bool = True
    line: int = 0
    col: int = 0
    operator: Optional[str] = None


@dataclass
class FieldDecl:
    name: str
    type_node: TypeNode
    init: Optional[Expr]
    is_public: bool = True
    line: int = 0
    col: int = 0


@dataclass
class ClassDecl:
    name: str
    parent: Optional[str]
    fields: List[FieldDecl]
    methods: List[FuncDecl]
    is_public: bool = True
    line: int = 0
    col: int = 0


@dataclass
class ImportDecl:
    module: str
    alias: Optional[str] = None
    names: Optional[List[str]] = None
    is_wildcard: bool = False
    line: int = 0
    col: int = 0


@dataclass
class PackageDecl:
    name: str
    line: int = 0
    col: int = 0


@dataclass
class Program:
    package: Optional[PackageDecl] = None
    imports: List[ImportDecl] = field(default_factory=list)
    declarations: List[Any] = field(default_factory=list)
