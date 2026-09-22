import os
from typing import List

from .package_loader import PackageLoader, PackageLoadError
from .type_checker import TypeChecker
from .codegen import CodeGen
from . import ast_nodes as ast
from .diagnostics import (
    DiagnosticBag, MacerCompileError, Diagnostic, Span, Severity, ErrCode,
)


BUILTIN_FUNCS = {
    "print": ([ast.Param("value", ast.TypeNode("Any"))], ast.TypeNode("Void")),
    "len":   ([ast.Param("s", ast.TypeNode("Any"))], ast.TypeNode("Int")),
    "str":   ([ast.Param("v", ast.TypeNode("Any"))], ast.TypeNode("String")),
    "int":   ([ast.Param("v", ast.TypeNode("Any"))], ast.TypeNode("Int")),
    "float": ([ast.Param("v", ast.TypeNode("Any"))], ast.TypeNode("Float")),
    "abs":   ([ast.Param("v", ast.TypeNode("Any"))], ast.TypeNode("Float")),
}


class CompileResult:
    def __init__(self, code=None, bag=None, success=True, source=""):
        self.code = code
        self.bag = bag
        self.success = success
        self.source = source


class Compiler:
    def __init__(self, source_roots: List[str] = None):
        self.source_roots = source_roots or ["src", "stdlib"]
        self.basic_lib = BUILTIN_FUNCS

    def compile_source(self, source: str, filename="<source>") -> CompileResult:
        """编译单段源码（无包加载）。主要用于 API 调用和快速测试。"""
        bag = DiagnosticBag()
        from .lexer import Lexer
        from .parser import Parser
        try:
            tokens = Lexer(source, filename, bag).tokenize()
            program = Parser(tokens, filename, bag).parse()
        except MacerCompileError:
            return CompileResult(bag=bag, success=False, source=source)

        # 包装成单单元
        from .package_loader import LoadedUnit
        unit = LoadedUnit(
            package=program.package.name if program.package else None,
            filename=filename, source=source, program=program,
        )

        try:
            TypeChecker([unit], self.basic_lib, filename, bag).check()
            if bag.has_errors():
                return CompileResult(bag=bag, success=False, source=source)
            code = CodeGen([unit]).generate()
        except MacerCompileError:
            return CompileResult(bag=bag, success=False, source=source)
        except RecursionError:
            bag.add(Diagnostic(
                ErrCode.PARSE_TOO_DEEP, Severity.ERROR,
                "语法嵌套过深", span=Span(1, 1, 1, 2), filename=filename,
            ))
            return CompileResult(bag=bag, success=False, source=source)
        except Exception as e:
            bag.add(Diagnostic(
                ErrCode.RT_GENERIC, Severity.ERROR,
                f"编译器内部错误：{type(e).__name__}: {e}",
                span=Span(1, 1, 1, 2), filename=filename,
            ))
            return CompileResult(bag=bag, success=False, source=source)

        return CompileResult(code=code, bag=bag, success=True, source=source)

    def compile_file(self, path: str, out_path: str = None) -> CompileResult:
        """编译一个 .mce 文件，自动加载其 import 的包。"""
        bag = DiagnosticBag()

        # 确保路径存在
        if not os.path.isfile(path):
            bag.add(Diagnostic(
                ErrCode.FILE_NOT_FOUND, Severity.ERROR,
                f"找不到文件 '{path}'", span=None, filename=path,
            ))
            return CompileResult(bag=bag, success=False, source="")

        # 读取入口源码（用于错误高亮）
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
        except UnicodeDecodeError as e:
            bag.add(Diagnostic(
                ErrCode.FILE_NOT_FOUND, Severity.ERROR,
                f"文件不是有效的 UTF-8 编码：{e}",
                span=None, filename=path,
            ))
            return CompileResult(bag=bag, success=False, source="")

        loader = PackageLoader(self.source_roots, bag)
        try:
            units = loader.load_project(path)
        except PackageLoadError:
            return CompileResult(bag=bag, success=False, source=source)

        if bag.has_errors():
            return CompileResult(bag=bag, success=False, source=source)

        try:
            TypeChecker(units, self.basic_lib, path, bag).check()
        except MacerCompileError:
            return CompileResult(bag=bag, success=False, source=source)
        except RecursionError:
            bag.add(Diagnostic(
                ErrCode.PARSE_TOO_DEEP, Severity.ERROR,
                "语法嵌套过深", span=Span(1, 1, 1, 2), filename=path,
            ))
            return CompileResult(bag=bag, success=False, source=source)
        except Exception as e:
            bag.add(Diagnostic(
                ErrCode.RT_GENERIC, Severity.ERROR,
                f"编译器内部错误：{type(e).__name__}: {e}",
                span=Span(1, 1, 1, 2), filename=path,
            ))
            return CompileResult(bag=bag, success=False, source=source)

        if bag.has_errors():
            return CompileResult(bag=bag, success=False, source=source)

        code = CodeGen(units).generate()

        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(code)

        return CompileResult(code=code, bag=bag, success=True, source=source)