"""
Macer 项目清单（Macer.toml）
类似 Cargo.toml / pom.xml。
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Python 3.11+ 有 tomllib；否则用 tomli
try:
    import tomllib                # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib   # 需要 pip install tomli
    except ImportError:
        tomllib = None


@dataclass
class Dependency:
    name: str
    version: str = "*"
    path: Optional[str] = None
    git: Optional[str] = None
    branch: Optional[str] = None
    tag: Optional[str] = None


@dataclass
class PackageSection:
    name: str = "unnamed"
    version: str = "0.1.0"
    edition: str = "2024"
    authors: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class BuildSection:
    source_roots: List[str] = field(default_factory=lambda: ["src"])
    entry: Optional[str] = None
    out_dir: str = "target"


@dataclass
class Manifest:
    package: PackageSection
    build: BuildSection
    dependencies: Dict[str, Dependency] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str) -> "Manifest":
        if tomllib is None:
            raise RuntimeError(
                "需要 tomllib (Python 3.11+) 或 tomli。"
                "请升级 Python 或 pip install tomli"
            )
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        pkg_data = data.get("package", {})
        pkg = PackageSection(
            name=pkg_data.get("name", "unnamed"),
            version=pkg_data.get("version", "0.1.0"),
            edition=pkg_data.get("edition", "2024"),
            authors=pkg_data.get("authors", []),
            description=pkg_data.get("description", ""),
        )

        bld_data = data.get("build", {})
        bld = BuildSection(
            source_roots=bld_data.get("source_roots", ["src"]),
            entry=bld_data.get("entry"),
            out_dir=bld_data.get("out_dir", "target"),
        )

        deps: Dict[str, Dependency] = {}
        for name, spec in data.get("dependencies", {}).items():
            if isinstance(spec, str):
                deps[name] = Dependency(name=name, version=spec)
            elif isinstance(spec, dict):
                deps[name] = Dependency(
                    name=name,
                    version=spec.get("version", "*"),
                    path=spec.get("path"),
                    git=spec.get("git"),
                    branch=spec.get("branch"),
                    tag=spec.get("tag"),
                )

        return cls(package=pkg, build=bld, dependencies=deps)


def find_manifest(start_dir: str) -> Optional[str]:
    """从 start_dir 向上查找 Macer.toml"""
    cur = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(cur, "Macer.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent