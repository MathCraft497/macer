from enum import Enum, auto
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
