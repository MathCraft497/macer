# -*- coding: utf-8 -*-
"""Macer 一键重建：写入所有核心文件到可用状态"""
from pathlib import Path
import sys

ROOT = Path(__file__).parent

FILES = {}

# ============================================================
# src/macer/tokens.py
# ============================================================
FILES["src/macer/tokens.py"] = '''from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    CHAR = auto()
    IDENT = auto()

    CLASS = auto()
    FUNC = auto()
    VAR = auto()
    LET = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    RETURN = auto()
    NEW = auto()
    SELF = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    IMPORT = auto()
    FROM = auto()
    AS = auto()
    PUBLIC = auto()
    PRIVATE = auto()
    EXTENDS = auto()
    CALC = auto()
    PACKAGE = auto()

    TYPE_INT = auto()
    TYPE_FLOAT = auto()
    TYPE_STRING = auto()
    TYPE_BOOL = auto()
    TYPE_VOID = auto()
    TYPE_ANY = auto()
    TYPE_CHAR = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    EQEQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    DOT = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    ARROW = auto()

    EOF = auto()


KEYWORDS = {
    "class": TokenType.CLASS,
    "func": TokenType.FUNC,
    "var": TokenType.VAR,
    "let": TokenType.LET,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "return": TokenType.RETURN,
    "new": TokenType.NEW,
    "self": TokenType.SELF,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
    "import": TokenType.IMPORT,
    "from": TokenType.FROM,
    "as": TokenType.AS,
    "public": TokenType.PUBLIC,
    "private": TokenType.PRIVATE,
    "extends": TokenType.EXTENDS,
    "calc": TokenType.CALC,
    "package": TokenType.PACKAGE,
}

TYPE_KEYWORDS = {
    "Int": TokenType.TYPE_INT,
    "Float": TokenType.TYPE_FLOAT,
    "String": TokenType.TYPE_STRING,
    "Bool": TokenType.TYPE_BOOL,
    "Void": TokenType.TYPE_VOID,
    "Any": TokenType.TYPE_ANY,
    "Char": TokenType.TYPE_CHAR,
}


@dataclass
class Token:
    type: TokenType
    value: object
    line: int
    col: int
    start_pos: int = 0
    end_pos: int = 0

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"
'''

# ============================================================
# src/macer/diagnostics.py
# ============================================================
FILES["src/macer/diagnostics.py"] = '''"""
Macer 诊断系统
"""
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional


class ErrCode:
    FILE_NOT_FOUND       = "MCE0001"

    LEX_UNKNOWN_CHAR     = "MCE1001"
    LEX_UNTERMINATED_STR = "MCE1002"
    LEX_BAD_ESCAPE       = "MCE1003"
    LEX_BAD_NUMBER       = "MCE1004"

    PARSE_UNEXPECTED     = "MCE2001"
    PARSE_EXPECTED       = "MCE2002"
    PARSE_BAD_ASSIGN     = "MCE2003"
    PARSE_TOO_DEEP       = "MCE2004"

    TYPE_UNDEFINED       = "MCE3001"
    TYPE_MISMATCH        = "MCE3002"
    TYPE_DUPLICATE       = "MCE3003"
    TYPE_NOT_CALLABLE    = "MCE3004"
    TYPE_ARG_COUNT       = "MCE3005"
    TYPE_NOT_CLASS       = "MCE3006"
    TYPE_NO_MEMBER       = "MCE3007"
    TYPE_IMMUTABLE       = "MCE3008"
    TYPE_RETURN_MISMATCH = "MCE3009"
    TYPE_COND_NOT_BOOL   = "MCE3010"
    TYPE_NO_METHOD       = "MCE3011"
    TYPE_BAD_OPERATOR    = "MCE3012"

    RT_DIV_ZERO          = "MCE4001"
    RT_NULL_ACCESS       = "MCE4002"
    RT_INDEX_OOB         = "MCE4003"
    RT_ASSERT            = "MCE4004"
    RT_STACK_OVERFLOW    = "MCE4005"
    RT_GENERIC           = "MCE4099"

    PKG_NOT_FOUND        = "MCE5001"
    PKG_PATH_MISMATCH    = "MCE5002"
    PKG_CYCLIC_IMPORT    = "MCE5003"
    PKG_DUPLICATE_CLASS  = "MCE5004"
    PKG_BAD_IMPORT       = "MCE5005"


class Severity:
    ERROR   = "error"
    WARNING = "warning"
    NOTE    = "note"


class Color:
    ENABLED = True
    RED    = "\\033[1;31m"
    YELLOW = "\\033[1;33m"
    BLUE   = "\\033[1;34m"
    CYAN   = "\\033[1;36m"
    BOLD   = "\\033[1m"
    RESET  = "\\033[0m"

    @classmethod
    def disable(cls):
        cls.ENABLED = False

    @classmethod
    def wrap(cls, text, color):
        if not cls.ENABLED:
            return text
        return f"{color}{text}{cls.RESET}"


@dataclass
class Span:
    line: int
    col: int
    end_line: int = 0
    end_col: int = 0

    def __post_init__(self):
        if self.end_line == 0:
            self.end_line = self.line
        if self.end_col == 0:
            self.end_col = self.col + 1


@dataclass
class Diagnostic:
    code: str
    severity: str
    message: str
    span: Optional[Span] = None
    filename: str = "<source>"
    note: Optional[str] = None
    note_span: Optional[Span] = None

    def render(self, source_lines=None):
        parts = []
        sev_color = {
            Severity.ERROR:   Color.RED,
            Severity.WARNING: Color.YELLOW,
            Severity.NOTE:    Color.BLUE,
        }.get(self.severity, Color.RED)

        head = (f"{Color.wrap(self.severity, sev_color)}"
                f"{Color.wrap('[' + self.code + ']', Color.BOLD)}: {self.message}")
        parts.append(head)

        if self.span:
            loc = f"{self.filename}:{self.span.line}:{self.span.col}"
        else:
            loc = self.filename
        parts.append(f"  {Color.wrap('-->', Color.CYAN)} {loc}")

        if self.span and source_lines:
            parts.extend(self._render_snippet(source_lines, self.span, sev_color))

        if self.note:
            parts.append(f"  {Color.wrap('note', Color.BLUE)}: {self.note}")

        return "\\n".join(parts)

    def _render_snippet(self, source_lines, span, color):
        if not span or span.line < 1 or span.line > len(source_lines):
            return []
        out = []
        idx = span.line - 1
        src = source_lines[idx].rstrip("\\n")
        num_str = str(span.line)
        gutter = " " * len(num_str)
        bar = Color.wrap("|", Color.CYAN)
        out.append(f"{gutter} {bar}")
        out.append(f"{Color.wrap(num_str, Color.CYAN)} {bar} {src}")
        col = max(1, span.col)
        if span.end_line == span.line:
            width = max(1, span.end_col - span.col)
        else:
            width = max(1, len(src) - col + 1)
        carets = Color.wrap("^" * width, color)
        out.append(f"{gutter} {bar} " + " " * (col - 1) + carets)
        return out


@dataclass
class DiagnosticBag:
    diagnostics: List[Diagnostic] = field(default_factory=list)

    def add(self, diag):
        self.diagnostics.append(diag)

    def error(self, code, message, span=None, filename="<source>",
              note=None, note_span=None):
        self.add(Diagnostic(code, Severity.ERROR, message, span, filename,
                            note, note_span))

    def has_errors(self):
        return any(d.severity == Severity.ERROR for d in self.diagnostics)

    def error_count(self):
        return sum(1 for d in self.diagnostics if d.severity == Severity.ERROR)


class MacerError(Exception):
    def __init__(self, diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


class MacerCompileError(MacerError):
    pass


class MacerRuntimeError(MacerError):
    pass


def print_diagnostics(bag, source="", filename="<source>", stream=sys.stderr):
    cache = {}

    def get_lines(fn):
        if fn in cache:
            return cache[fn]
        try:
            if fn and os.path.isfile(fn):
                with open(fn, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()
                cache[fn] = lines
                return lines
        except Exception:
            pass
        lines = (source or "").splitlines()
        cache[fn] = lines
        return lines

    for i, d in enumerate(bag.diagnostics):
        if i > 0:
            print(file=stream)
        lines = get_lines(d.filename)
        print(d.render(lines), file=stream)


def print_banner(stream=sys.stderr):
    print(Color.wrap("Macer 编译器遇到错误：", Color.RED), file=stream)
'''

# ============================================================
# src/macer/lexer.py
# ============================================================
FILES["src/macer/lexer.py"] = '''from .tokens import Token, TokenType, KEYWORDS, TYPE_KEYWORDS
from .diagnostics import (
    DiagnosticBag, MacerCompileError, Diagnostic, Span, Severity, ErrCode,
)


class Lexer:
    def __init__(self, source, filename="<source>", bag=None):
        if source and source[0] == "\\ufeff":
            source = source[1:]
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self.bag = bag if bag is not None else DiagnosticBag()

    def _err(self, code, msg, line=None, col=None, width=1):
        line = line if line is not None else self.line
        col = col if col is not None else self.col
        diag = Diagnostic(
            code=code, severity=Severity.ERROR, message=msg,
            span=Span(line, col, line, col + max(width, 1)),
            filename=self.filename,
        )
        self.bag.add(diag)
        raise MacerCompileError(diag)

    def peek(self, offset=0):
        p = self.pos + offset
        if p < len(self.source):
            return self.source[p]
        return "\\0"

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def skip_whitespace_and_comments(self):
        while self.pos < len(self.source):
            ch = self.peek()
            if ch in " \\t\\r\\n":
                self.advance()
            elif ch == "/" and self.peek(1) == "/":
                while self.pos < len(self.source) and self.peek() != "\\n":
                    self.advance()
            elif ch == "/" and self.peek(1) == "*":
                self.advance(); self.advance()
                closed = False
                while self.pos < len(self.source):
                    if self.peek() == "*" and self.peek(1) == "/":
                        self.advance(); self.advance()
                        closed = True
                        break
                    self.advance()
                if not closed:
                    self._err(ErrCode.LEX_UNTERMINATED_STR, "块注释未闭合")
            else:
                break

    def read_string(self):
        quote = self.advance()
        start_line = self.line
        start_col = self.col - 1
        buf = []
        while self.pos < len(self.source) and self.peek() != quote:
            ch = self.advance()
            if ch == "\\\\":
                if self.pos >= len(self.source):
                    break
                nxt = self.advance()
                mapping = {"n": "\\n", "t": "\\t", "r": "\\r",
                           "\\\\": "\\\\", "\\"": "\\"", "'": "'"}
                if nxt not in mapping:
                    self._err(ErrCode.LEX_BAD_ESCAPE,
                              f"非法转义 '\\\\{nxt}'",
                              self.line, self.col - 2, width=2)
                buf.append(mapping[nxt])
            else:
                buf.append(ch)
        if self.pos >= len(self.source):
            self._err(ErrCode.LEX_UNTERMINATED_STR, "字符串未闭合",
                      start_line, start_col)
        self.advance()
        return "".join(buf)

    def read_number(self):
        start = self.pos
        is_float = False
        while self.pos < len(self.source) and (self.peek().isdigit() or self.peek() == "."):
            if self.peek() == ".":
                if is_float or not self.peek(1).isdigit():
                    break
                is_float = True
            self.advance()
        text = self.source[start:self.pos]
        try:
            return float(text) if is_float else int(text)
        except ValueError:
            self._err(ErrCode.LEX_BAD_NUMBER, f"非法数字 '{text}'")

    def read_ident(self):
        start = self.pos
        while self.pos < len(self.source) and (self.peek().isalnum() or self.peek() == "_"):
            self.advance()
        return self.source[start:self.pos]

    def _add(self, ttype, value, line, col, start_pos):
        self.tokens.append(Token(ttype, value, line, col,
                                 start_pos=start_pos, end_pos=self.pos))

    def tokenize(self):
        while True:
            self.skip_whitespace_and_comments()
            if self.pos >= len(self.source):
                self.tokens.append(Token(TokenType.EOF, None, self.line, self.col,
                                         start_pos=self.pos, end_pos=self.pos))
                break

            line, col = self.line, self.col
            start_pos = self.pos
            ch = self.peek()

            if ch.isdigit():
                val = self.read_number()
                t = TokenType.FLOAT if isinstance(val, float) else TokenType.INT
                self._add(t, val, line, col, start_pos)
                continue

            if ch.isalpha() or ch == "_":
                name = self.read_ident()
                if name in KEYWORDS:
                    self._add(KEYWORDS[name], name, line, col, start_pos)
                elif name in TYPE_KEYWORDS:
                    self._add(TYPE_KEYWORDS[name], name, line, col, start_pos)
                else:
                    self._add(TokenType.IDENT, name, line, col, start_pos)
                continue

            if ch == "\\"":
                val = self.read_string()
                self._add(TokenType.STRING, val, line, col, start_pos)
                continue

            # 双字符（必须在单字符之前）
            two = self.source[self.pos:self.pos + 2]
            if two == "==":
                self.advance(); self.advance()
                self._add(TokenType.EQEQ, "==", line, col, start_pos); continue
            if two == "!=":
                self.advance(); self.advance()
                self._add(TokenType.NEQ, "!=", line, col, start_pos); continue
            if two == "<=":
                self.advance(); self.advance()
                self._add(TokenType.LE, "<=", line, col, start_pos); continue
            if two == ">=":
                self.advance(); self.advance()
                self._add(TokenType.GE, ">=", line, col, start_pos); continue
            if two == "&&":
                self.advance(); self.advance()
                self._add(TokenType.AND, "&&", line, col, start_pos); continue
            if two == "||":
                self.advance(); self.advance()
                self._add(TokenType.OR, "||", line, col, start_pos); continue
            if two == "->":
                self.advance(); self.advance()
                self._add(TokenType.ARROW, "->", line, col, start_pos); continue

            single = {
                "+": TokenType.PLUS, "-": TokenType.MINUS,
                "*": TokenType.STAR, "/": TokenType.SLASH,
                "%": TokenType.PERCENT, "=": TokenType.EQ,
                "<": TokenType.LT, ">": TokenType.GT,
                "!": TokenType.NOT, ".": TokenType.DOT,
                ",": TokenType.COMMA, ":": TokenType.COLON,
                ";": TokenType.SEMICOLON, "(": TokenType.LPAREN,
                ")": TokenType.RPAREN, "{": TokenType.LBRACE,
                "}": TokenType.RBRACE, "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
            }
            if ch in single:
                self.advance()
                self._add(single[ch], ch, line, col, start_pos); continue

            self._err(ErrCode.LEX_UNKNOWN_CHAR,
                      f"无法识别的字符 '{ch}'", line, col, width=1)

        return self.tokens
'''

# ============================================================
# src/macer/ast_nodes.py
# ============================================================
FILES["src/macer/ast_nodes.py"] = '''from dataclasses import dataclass, field
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
'''

print("=== Macer 一键重建 ===")
print(f"根目录: {ROOT}")
print()

for path, content in FILES.items():
    full = ROOT / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    print(f"OK  {path}  ({len(content.splitlines())} 行)")

print()
print("完成。请运行验证：")
print("  python -c \"import macer.lexer, macer.diagnostics, macer.ast_nodes, macer.tokens; print('OK')\"")