# 贡献指南

感谢你愿意为 Macer 做贡献！

## 目录

- [开发环境](#开发环境)
- [项目结构](#项目结构)
- [编码规范](#编码规范)
- [扩展编译器](#扩展编译器)
- [提交 PR](#提交-pr)

---

## 开发环境

- Python 3.8+
- 无需第三方依赖

```bash
git clone <repo> macer
cd macer
python macer.py run examples/hello.mce
```

如果看到 `Hello, Macer!`，说明环境正常。

---

## 项目结构

```
macer/
├── macer.py                    # CLI 入口
├── src/
│   ├── diagnostics.py          # 诊断系统
│   ├── tokens.py               # Token 定义
│   ├── lexer.py                # 词法分析
│   ├── ast_nodes.py            # AST 节点
│   ├── parser.py               # 语法分析
│   ├── type_checker.py         # 类型检查
│   ├── codegen.py              # 代码生成
│   └── compiler.py             # 主入口
├── libs/
│   ├── runtime.py              # 运行时
│   └── basic.mce               # 内置库声明
├── examples/
└── docs/
```

---

## 编码规范

- 使用 **4 空格** 缩进
- 类型注解尽量完整
- 错误信息使用**中文**，但错误码用英文常量
- 每个公开函数写一行 docstring
- 新增错误码时遵守段位规则（见 [错误码表](error-codes.md)）

---

## 扩展编译器

### 增加新语法

1. 在 `tokens.py` 的 `TokenType` 与 `KEYWORDS` 中加 Token
2. 在 `lexer.py` 中识别关键字/符号
3. 在 `ast_nodes.py` 中加 AST 节点
4. 在 `parser.py` 中加语法规则
5. 在 `type_checker.py` 中加类型规则
6. 在 `codegen.py` 中加代码生成

**示例**：增加 `for` 循环

```python
# tokens.py
FOR = auto()
KEYWORDS["for"] = TokenType.FOR

# ast_nodes.py
@dataclass
class ForStmt(Stmt):
    init: Stmt
    cond: Expr
    step: Stmt
    body: List[Stmt]

# parser.py
def parse_for(self):
    self.expect(TokenType.FOR)
    ...

# type_checker.py
elif isinstance(s, ast.ForStmt):
    ...

# codegen.py
elif isinstance(s, ast.ForStmt):
    ...
```

### 增加新内置函数

1. 在 `../src/macer/runtime/runtime.py` 中实现 Python 侧函数
2. 在 `../src/macer/compiler.py` 的 `BUILTIN_FUNCS` 注册签名
3. 在 `../src/macer/runtime/basic.mce` 中写声明（可选）

**示例**：增加 `sqrt`

```python
# libs/runtime.py
import math as _math
def sqrt(v):
    if v < 0:
        raise MacerRuntimeErr("MCE4099", "sqrt 参数不能为负")
    return _math.sqrt(v)

# compiler.py
BUILTIN_FUNCS = {
    ...
    "sqrt": ([ast.Param("v", ast.TypeNode("Float"))], ast.TypeNode("Float")),
}
```

### 增加新错误码

在 `../src/macer/diagnostics.py` 的 `ErrCode` 类中追加常量：

```python
class ErrCode:
    ...
    TYPE_GENERIC_NOT_SUPPORTED = "MCE3013"
```

### 替换后端

`CodeGen` 是唯一输出 Python 的模块。要改为 C / LLVM / WASM：

1. 新建 `codegen_c.py` 等
2. 保证接口是 `CodeGen(program).generate() -> str`（或 bytes）
3. 在 `compiler.py` 中切换

---

## 提交 PR

### 流程

1. Fork 本仓库
2. 新建分支：`git checkout -b feature/your-feature`
3. 提交改动：`git commit -m "feat: 增加 for 循环"`
4. 推送：`git push origin feature/your-feature`
5. 打开 Pull Request

### Commit 规范

采用 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `refactor:` 重构
- `test:` 测试
- `chore:` 杂项

### PR 检查清单

- [ ] 通过 `python macer.py run examples/hello.mce`
- [ ] 新增功能附带示例 `.mce`
- [ ] 错误信息使用中文，附错误码
- [ ] 更新相关文档
- [ ] 更新 `CHANGELOG.md`

---

## 报告问题

提交 Issue 时请附：

1. Macer 版本（`git rev-parse HEAD`）
2. Python 版本（`python --version`）
3. 复现用的 `.mce` 代码
4. 完整错误输出（含错误码）

---

## 许可证

提交代码即表示同意以 [MIT 许可证](../LICENSE) 发布。