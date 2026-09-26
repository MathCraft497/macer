from .tokens import Token, TokenType, KEYWORDS, TYPE_KEYWORDS
from .diagnostics import (
    DiagnosticBag, MacerCompileError, Diagnostic, Span, Severity, ErrCode,
)


class Lexer:
    def __init__(self, source, filename="<source>", bag=None):
        if source and source[0] == "\ufeff":
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
        return "\0"

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def skip_whitespace_and_comments(self):
        while self.pos < len(self.source):
            ch = self.peek()
            if ch in " \t\r\n":
                self.advance()
            elif ch == "/" and self.peek(1) == "/":
                while self.pos < len(self.source) and self.peek() != "\n":
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
            if ch == "\\":
                if self.pos >= len(self.source):
                    break
                nxt = self.advance()
                mapping = {"n": "\n", "t": "\t", "r": "\r",
                           "\\": "\\", "\"": "\"", "'": "'"}
                if nxt not in mapping:
                    self._err(ErrCode.LEX_BAD_ESCAPE,
                              f"非法转义 '\\{nxt}'",
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

            if ch == "\"":
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
                "@": TokenType.AT,
            }
            if ch in single:
                self.advance()
                self._add(single[ch], ch, line, col, start_pos); continue

            self._err(ErrCode.LEX_UNKNOWN_CHAR,
                      f"无法识别的字符 '{ch}'", line, col, width=1)

        return self.tokens
