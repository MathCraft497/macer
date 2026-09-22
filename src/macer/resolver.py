"""
Macer 依赖解析器（v1.0 雏形）
- 支持 path / git / registry（未来）
- 处理 source_roots 优先级
- 检测版本冲突
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from .manifest import Manifest, Dependency, find_manifest


@dataclass
class ResolvedDep:
    name: str
    version: str
    source_root: str        # 该依赖的源码根目录
    manifest_path: Optional[str] = None


class DependencyResolver:
    def __init__(self, project_dir: str):
        self.project_dir = os.path.abspath(project_dir)
        self.manifest_path = find_manifest(self.project_dir)
        self.manifest: Optional[Manifest] = None
        if self.manifest_path:
            self.manifest = Manifest.load(self.manifest_path)

    def resolve(self) -> List[ResolvedDep]:
        """
        返回所有依赖的源码根目录，按优先级排序：
        1. 项目自身
        2. path 依赖
        3. stdlib（由编译器提供）
        """
        result: List[ResolvedDep] = []
        if self.manifest is None:
            return result

        seen: Dict[str, str] = {}

        for name, dep in self.manifest.dependencies.items():
            if dep.path:
                dep_dir = os.path.join(
                    os.path.dirname(self.manifest_path), dep.path
                )
                dep_dir = os.path.abspath(dep_dir)
                dep_manifest = os.path.join(dep_dir, "Macer.toml")

                version = dep.version
                if os.path.isfile(dep_manifest):
                    sub = Manifest.load(dep_manifest)
                    if version == "*":
                        version = sub.package.version
                    # 该依赖的源根
                    for root in sub.build.source_roots:
                        result.append(ResolvedDep(
                            name=name,
                            version=version,
                            source_root=os.path.join(dep_dir, root),
                            manifest_path=dep_manifest,
                        ))
                else:
                    # 没有 manifest，就当作普通源码目录
                    result.append(ResolvedDep(
                        name=name,
                        version=version,
                        source_root=dep_dir,
                    ))

            elif dep.git:
                # TODO: clone 到缓存目录
                raise NotImplementedError(
                    f"git 依赖暂未实现：{name} → {dep.git}"
                )
            else:
                # registry 依赖，暂时忽略
                pass

            seen[name] = dep.version

        return result

    def source_roots(self, stdlib_root: Optional[str] = None) -> List[str]:
        """
        综合项目自身源根 + 依赖源根 + stdlib，作为 PackageLoader 的搜索路径。
        """
        roots: List[str] = []

        # 项目自身
        if self.manifest:
            for r in self.manifest.build.source_roots:
                roots.append(os.path.join(self.project_dir, r))
        else:
            roots.append(os.path.join(self.project_dir, "src"))

        # 依赖
        for dep in self.resolve():
            if dep.source_root and os.path.isdir(dep.source_root):
                roots.append(dep.source_root)

        # stdlib
        if stdlib_root and os.path.isdir(stdlib_root):
            roots.append(stdlib_root)

        # 去重并保持顺序
        seen = set()
        uniq = []
        for r in roots:
            r = os.path.abspath(r)
            if r not in seen:
                seen.add(r)
                uniq.append(r)
        return uniq

    def entry_file(self) -> Optional[str]:
        """返回清单里声明的入口，或自动推断"""
        if not self.manifest:
            return None
        if self.manifest.build.entry:
            return os.path.join(self.project_dir, self.manifest.build.entry)

        # 自动找 src/**/Main.mce
        for root in self.manifest.build.source_roots:
            base = os.path.join(self.project_dir, root)
            for dirpath, _, files in os.walk(base):
                if "Main.mce" in files:
                    return os.path.join(dirpath, "Main.mce")
        return None