"""
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
    RED    = "\033[1;31m"
    YELLOW = "\033[1;33m"
    BLUE   = "\033[1;34m"
    CYAN   = "\033[1;36m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"

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

        return "\n".join(parts)

    def _render_snippet(self, source_lines, span, color):
        if not span or span.line < 1 or span.line > len(source_lines):
            return []
        out = []
        idx = span.line - 1
        src = source_lines[idx].rstrip("\n")
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
