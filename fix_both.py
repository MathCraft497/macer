"""修复 _topo_sort_classes 让隐式继承 Object 的类排到 Object 之后"""
from pathlib import Path

p = Path("src/macer/codegen.py")
src = p.read_text(encoding="utf-8")

old = '''    def _topo_sort_classes(self):
        visited = set()
        result = []

        def visit(fqn):
            if fqn in visited:
                return
            visited.add(fqn)
            decl = self.classes[fqn]
            if decl.parent:
                parent_fqn = self._resolve_parent_fqn(
                    decl.parent, self.class_pkg[fqn])
                if parent_fqn and parent_fqn in self.classes:
                    visit(parent_fqn)
            result.append(fqn)

        for fqn in self.classes:
            visit(fqn)
        return result'''

new = '''    def _topo_sort_classes(self):
        """拓扑排序：父类先出。

        注意：类可能显式 `extends X`，也可能隐式继承 `macer.lang.Object`。
        两者都要考虑，否则子类会排在 Object 之前。
        """
        visited = set()
        result = []

        def visit(fqn):
            if fqn in visited:
                return
            visited.add(fqn)
            decl = self.classes[fqn]

            # 解析父类（显式或隐式）
            parent_fqn = None
            if decl.parent:
                parent_fqn = self._resolve_parent_fqn(
                    decl.parent, self.class_pkg[fqn])
            elif fqn != self.OBJECT_FQN and self.OBJECT_FQN in self.classes:
                # 隐式继承 macer.lang.Object
                parent_fqn = self.OBJECT_FQN

            # 递归访问父类
            if parent_fqn and parent_fqn in self.classes:
                visit(parent_fqn)

            result.append(fqn)

        # 先访问 Object（让它一定排在最前）
        if self.OBJECT_FQN in self.classes:
            visit(self.OBJECT_FQN)

        for fqn in self.classes:
            visit(fqn)
        return result'''

if old in src:
    src = src.replace(old, new, 1)
    p.write_text(src, encoding="utf-8")
    print("OK  _topo_sort_classes 已修复")
else:
    print("FAIL  未匹配，尝试手动改（见文档）")
    print()
    print("=== 当前 _topo_sort_classes ===")
    i = src.find("def _topo_sort_classes")
    j = src.find("\n    def ", i + 10)
    print(src[i:j])