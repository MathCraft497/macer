"""编译入口：Macer 源码 → BytecodeWriter"""
from pathlib import Path
from ..package_loader import PackageLoader
from ..type_checker import TypeChecker
from ..compiler import BUILTIN_FUNCS
from ..diagnostics import DiagnosticBag
from ..codegen_bytecode import BytecodeCodeGen
from .writer import BytecodeWriter


def compile_file_to_bytecode(path: str, source_roots=None) -> tuple:
    """编译 .mce 文件到字节码

    返回 (writer, bag)。成功时 writer 非空，bag 无错。
    """
    if source_roots is None:
        source_roots = ["src", "stdlib"]

    bag = DiagnosticBag()
    loader = PackageLoader(source_roots, bag)
    units = loader.load_project(path)

    if bag.has_errors():
        return None, bag

    TypeChecker(units, BUILTIN_FUNCS, path, bag).check()
    if bag.has_errors():
        return None, bag

    codegen = BytecodeCodeGen(units)
    writer = codegen.generate()
    return writer, bag


def compile_source_to_bytecode(source: str,
                               filename="<source>") -> tuple:
    """编译源码字符串到字节码（无 import）"""
    from ..lexer import Lexer
    from ..parser import Parser
    from ..package_loader import LoadedUnit

    bag = DiagnosticBag()
    try:
        tokens = Lexer(source, filename, bag).tokenize()
        program = Parser(tokens, filename, bag, source=source).parse()
    except Exception:
        return None, bag

    unit = LoadedUnit(
        package=program.package.name if program.package else None,
        filename=filename, source=source, program=program,
    )
    TypeChecker([unit], BUILTIN_FUNCS, filename, bag).check()
    if bag.has_errors():
        return None, bag

    codegen = BytecodeCodeGen([unit])
    writer = codegen.generate()
    return writer, bag