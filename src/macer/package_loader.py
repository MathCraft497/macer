"""
Macer 包加载器
- 根据源码根目录 + 包名定位 .mce 文件
- 递归加载依赖（import 的其他包）
- 检测循环依赖
- 校验包名与目录结构一致
- 缓存已加载单元
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .lexer import Lexer
from .parser import Parser
from .diagnostics import (
    DiagnosticBag, Diagnostic, Severity, ErrCode, MacerCompileError,
)
from . import ast_nodes as ast


class PackageLoadError(Exception):
    pass


@dataclass
class LoadedUnit:
    """一个已加载的编译单元"""
    package: Optional[str]
    filename: str
    source: str
    program: ast.Program
    symbol_table: dict = field(default_factory=dict)   # 简单名 → ClassInfo，稍后由 TypeChecker 填


class PackageLoader:
    """
    从 source_roots 查找 .mce 文件。
    source_roots 例如 ["src", "stdlib"]。
    """

    def __init__(self, source_roots: List[str], bag: DiagnosticBag):
        self.source_roots = [os.path.abspath(r) for r in source_roots]
        self.bag = bag
        self.cache: Dict[str, LoadedUnit] = {}
        self.loading: Set[str] = set()

    # ============ 单文件加载 ============
    def load_file(self, path: str) -> LoadedUnit:
        path = os.path.abspath(path)
        if path in self.cache:
            return self.cache[path]

        if path in self.loading:
            self.bag.add(Diagnostic(
                ErrCode.PKG_CYCLIC_IMPORT, Severity.ERROR,
                f"检测到循环依赖：{path}",
                span=None, filename=path,
            ))
            raise PackageLoadError(path)

        self.loading.add(path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
        except FileNotFoundError:
            self.bag.add(Diagnostic(
                ErrCode.FILE_NOT_FOUND, Severity.ERROR,
                f"找不到文件 '{path}'", span=None, filename=path,
            ))
            raise PackageLoadError(path)
        except UnicodeDecodeError as e:
            self.bag.add(Diagnostic(
                ErrCode.FILE_NOT_FOUND, Severity.ERROR,
                f"文件不是有效的 UTF-8 编码：{e}",
                span=None, filename=path,
            ))
            raise PackageLoadError(path)

        try:
            tokens = Lexer(source, path, self.bag).tokenize()
            program = Parser(tokens, path, self.bag, source=source).parse()
        except MacerCompileError:
            self.loading.discard(path)
            raise PackageLoadError(path)

        unit = LoadedUnit(
            package=program.package.name if program.package else None,
            filename=path,
            source=source,
            program=program,
        )

        # 校验包名与目录结构
        self._verify_package_path(unit)

        self.cache[path] = unit

        # 递归加载 import
        for imp in program.imports:
            try:
                self._load_import(imp, unit.package, path)
            except PackageLoadError:
                pass   # 已有诊断，继续处理其他 import

        self.loading.discard(path)
        return unit

    # ============ 目录结构校验 ============
    def _verify_package_path(self, unit: LoadedUnit):
        """Java 规则：包名必须与目录结构匹配"""
        if not unit.package:
            return

        pkg_path = unit.package.replace(".", os.sep)
        dir_path = os.path.dirname(unit.filename).replace(os.sep, "/")

        # 允许包名对应路径以 / 结尾或包含在路径中
        if not dir_path.endswith(pkg_path.replace(os.sep, "/")):
            self.bag.add(Diagnostic(
                ErrCode.PKG_PATH_MISMATCH, Severity.ERROR,
                f"包名 '{unit.package}' 与目录结构不匹配；"
                f"文件应位于 .../{pkg_path}/ 下",
                span=None, filename=unit.filename,
            ))
            raise PackageLoadError(unit.filename)

    # ============ import 解析 ============
    def _load_import(self, imp: ast.ImportDecl, current_package: Optional[str],
                     current_file: str):
        """
        解析 import 语句：
          import a.b.C      → 加载 a/b/C.mce（类文件）
          import a.b        → 加载 a/b/ 目录下所有 .mce（包）
          import a.b.*      → 同上，显式通配
          from a.b import C → 加载 a/b/C.mce 或回退到 a/b/ 目录
        """
        if imp.is_wildcard:
            self._load_package_dir(imp.module, current_file)
            return

        if imp.names:
            for name in imp.names:
                fq = f"{imp.module}.{name}"
                if not self._try_load_symbol_or_package(fq, current_file):
                    self.bag.add(Diagnostic(
                        ErrCode.PKG_NOT_FOUND, Severity.ERROR,
                        f"找不到导入的符号 '{fq}'",
                        span=None, filename=current_file,
                    ))
                    raise PackageLoadError(fq)
            return

        # import a.b.C  /  import a.b
        if not self._try_load_symbol_or_package(imp.module, current_file):
            self.bag.add(Diagnostic(
                ErrCode.PKG_NOT_FOUND, Severity.ERROR,
                f"找不到导入的 '{imp.module}'",
                span=None, filename=current_file,
            ))
            raise PackageLoadError(imp.module)

    def _try_load_symbol_or_package(self, fq_name: str, current_file: str) -> bool:
        """
        尝试把 fq_name 解析为一个可加载的东西：
          1. a/b/C.mce   —— 单文件（类）
          2. a/b/C/      —— 子包目录
          3. 截去最后一段，试 a/b/ 目录（父包），只要存在就认为成功
             （至于 fq_name 的最后一段是否是包里的符号，交给 TypeChecker 检查）
        """
        # 1. 单文件
        rel = fq_name.replace(".", os.sep) + ".mce"
        for root in self.source_roots:
            path = os.path.join(root, rel)
            if os.path.isfile(path):
                self.load_file(path)
                return True

        # 2. 子包目录
        rel_dir = fq_name.replace(".", os.sep)
        for root in self.source_roots:
            dir_path = os.path.join(root, rel_dir)
            if os.path.isdir(dir_path):
                self._load_package_dir(fq_name, current_file)
                return True

        # 3. 回退：截去最后一段，加载父包
        #    这样 `import macer.lang.print` 会去加载 `macer/lang/` 下的所有文件
        parts = fq_name.split(".")
        if len(parts) >= 2:
            parent = ".".join(parts[:-1])
            rel_parent = parent.replace(".", os.sep)
            for root in self.source_roots:
                dir_path = os.path.join(root, rel_parent)
                if os.path.isdir(dir_path):
                    self._load_package_dir(parent, current_file)
                    return True

        return False

    def _try_load_fq(self, fq_name: str) -> bool:
        rel = fq_name.replace(".", os.sep) + ".mce"
        for root in self.source_roots:
            path = os.path.join(root, rel)
            if os.path.isfile(path):
                self.load_file(path)
                return True
        return False

    def _load_fq_file(self, fq_name: str, current_file: str):
        if not self._try_load_fq(fq_name):
            self.bag.add(Diagnostic(
                ErrCode.PKG_NOT_FOUND, Severity.ERROR,
                f"找不到导入的类 '{fq_name}'",
                span=None, filename=current_file,
            ))
            raise PackageLoadError(fq_name)

    def _load_package_dir(self, pkg_name: str, current_file: str):
        rel = pkg_name.replace(".", os.sep)
        found = False
        for root in self.source_roots:
            dir_path = os.path.join(root, rel)
            if os.path.isdir(dir_path):
                found = True
                for entry in sorted(os.listdir(dir_path)):
                    if entry.endswith(".mce"):
                        try:
                            self.load_file(os.path.join(dir_path, entry))
                        except PackageLoadError:
                            pass
        if not found:
            self.bag.add(Diagnostic(
                ErrCode.PKG_NOT_FOUND, Severity.ERROR,
                f"找不到包 '{pkg_name}'",
                span=None, filename=current_file,
            ))
            raise PackageLoadError(pkg_name)

    # ============ 批量加载 ============
    def load_project(self, entry_file: str) -> List[LoadedUnit]:
        self.load_file(entry_file)
        return list(self.cache.values())