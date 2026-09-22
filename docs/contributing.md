# 贡献指南

感谢你愿意为 Macer 做贡献！

## 目录

- [开发环境](#开发环境)
- [项目结构](#项目结构)
- [编码规范](#编码规范)
- [扩展编译器](#扩展编译器)
- [测试](#测试)
- [提交 PR](#提交-pr)

---

## 开发环境

- Python 3.8+
- 无需第三方依赖

```bash
git clone <repo> macer
cd macer

# 可编辑安装（可选）
pip install -e .

# 验证
python -m macer run examples/multi-package/src/com/example/app/Main.mce
```

如果看到 5 行输出，说明环境正常。

---

## 项目结构

```
macer/
├── src/macer/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                     CLI 入口
│   ├── compiler.py                编译器主控
│   ├── diagnostics.py             诊断系统
│   ├── tokens.py                  Token 定义
│   ├── lexer.py                   词法分析
│   ├── ast_nodes.py               AST 节点
│   ├── parser.py                  语法分析
│   ├── package_loader.py          包加载
│   ├── type_checker.py            类型检查
│   ├── codegen.py                 代码生成
│   ├── manifest.py                Macer.toml 解析
│   ├── resolver.py                依赖解析
│   └── runtime/
│       ├── __init__.py
│       ├── runtime.py             内置函数 + 运行时包装
│       └── basic.mce              内置声明
├── stdlib/                        标准库（.mce）
│   └── macer/
│       ├── lang/
│       │   ├── Object.mce         根基类
│       │   └── basic.mce          内置函数声明
│       ├── math/
│       │   └── Math.mce
│       └── io/
│           └── Console.mce
├── examples/                      示例程序
├── docs/                          文档
├── tests/                         测试
└── pyproject.toml                 打包配置
```

---

## 编码规范

### 通用

- 使用 **4 空格** 缩进
- 类型注解尽量完整
- 每个公开函数写一行 docstring
- 错误信息使用**中文**，错误码用英文常量
- 文件名使用 `snake_case`

### 错误码

新增错误码时遵守段位规则：

| 段位 | 分类 |
|------|------|
| `0xxx` | 通用 |
| `1xxx` | 词法 |
| `2xxx` | 语法 |
| `3xxx` | 类型 |
| `4xxx` | 运行时 |
| `5xxx` | 包系统 |

在 `src/macer/diagnostics.py` 的 `ErrCode` 类中追加。

### 提交信息

采用 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `refactor:` 重构
- `test:` 测试
- `chore:` 杂项

**示例**：

```
feat: 增加 calc.opr- 减法运算符重载
fix: 修复 Object 基类隐式继承的拓扑排序
docs: 更新语言参考到 v0.1.0
```

---

## 扩展编译器

### 增加新语法

以增加 `for` 循环为例，需要改 6 处：

**1. `tokens.py`**：

```python
class TokenType(Enum):
    ...
    FOR = auto()

KEYWORDS = {
    ...
    "for": TokenType.FOR,
}
```

**2. `lexer.py`**：无需改（关键字自动识别）。

**3. `ast_nodes.py`**：

```python
@dataclass
class ForStmt(Stmt):
    init: Optional[Stmt]
    cond: Optional[Expr]
    step: Optional[Stmt]
    body: List[Stmt]
    line: int = 0
    col: int = 0
```

**4. `parser.py`**：

```python
def parse_statement(self):
    ...
    if tok.type == TokenType.FOR:
        return self.parse_for()

def parse_for(self):
    tok = self.expect(TokenType.FOR)
    ...
    return ast.ForStmt(...)
```

**5. `type_checker.py`**：

```python
def _check_stmt(self, s, scope):
    ...
    elif isinstance(s, ast.ForStmt):
        # 检查 init / cond / step / body
        ...
```

**6. `codegen.py`**：

```python
def gen_stmt(self, s):
    ...
    elif isinstance(s, ast.ForStmt):
        # 生成 Python for 循环
        ...
```

### 增加新内置函数

以增加 `sqrt` 为例，需要改 3 处：

**1. `runtime/runtime.py`**：

```python
import math as _math

def sqrt(v):
    if v < 0:
        raise MacerRuntimeErr("MCE4099", "sqrt 参数不能为负")
    return _math.sqrt(v)
```

**2. `runtime/__init__.py`**：

```python
from .runtime import (..., sqrt, ...)
__all__ = [..., "sqrt", ...]
```

**3. `compiler.py` 的 `BUILTIN_FUNCS`**：

```python
BUILTIN_FUNCS = {
    ...
    "sqrt": ([ast.Param("v", ast.TypeNode("Float"))], ast.TypeNode("Float")),
}
```

**4. `stdlib/macer/lang/basic.mce`**（可选，写声明）：

```macer
public func sqrt(v: Float) -> Float;
```

### 增加新错误码

在 `src/macer/diagnostics.py` 的 `ErrCode` 类中追加常量：

```python
class ErrCode:
    ...
    TYPE_GENERIC_NOT_SUPPORTED = "MCE3013"
```

在对应检查点调用：

```python
self._err(ErrCode.TYPE_GENERIC_NOT_SUPPORTED,
          "当前版本不支持泛型",
          node)
```

### 增加运算符重载

在 `parser.py` 的 `_try_parse_calc_func_name` 中扩展，同时更新：

- `type_checker.py` 的 `OP_KEYS`
- `codegen.py` 的 `OPERATOR_DUNDER`

### 替换后端

`CodeGen` 是唯一输出 Python 的模块。要改为 C / LLVM / WASM：

1. 新建 `codegen_c.py`
2. 保证接口是 `CodeGen(units).generate() -> str`
3. 在 `compiler.py` 中切换

前端（词法、语法、类型）完全复用。

---

## 测试

### 冒烟测试

`tests/smoke_test.py` 提供回归测试：

```bash
python tests/smoke_test.py
```

**期望**：

```
OK  test_hello
OK  test_multi_package
OK  test_type_error
OK  test_lex_error
OK  test_package_mismatch

✅ 5 / 5 通过
```

### 写新测试

```python
def test_your_feature():
    # 写临时 .mce
    tmp = ROOT / "tests" / "_tmp_your.mce"
    tmp.write_text("...", encoding="utf-8")
    try:
        rc, out, err = run_macer("run", str(tmp))
        assert rc == 0, f"失败: {err}"
        assert "期望输出" in out
    finally:
        tmp.unlink()
```

### 手动测试清单

改完代码后，**至少**手动验证：

1. `python -m macer run examples/multi-package/src/com/example/app/Main.mce --source-root examples/multi-package/src --source-root stdlib` 输出 5 行
2. `python tests/smoke_test.py` 全通过
3. 故意造错（如 `let x: Int = "hi";`）报 `MCE3002`
4. 包名目录不匹配报 `MCE5002`

---

## 提交 PR

### 流程

1. Fork 本仓库
2. 新建分支：`git checkout -b feature/your-feature`
3. 提交改动：`git commit -m "feat: 增加 for 循环"`
4. 推送：`git push origin feature/your-feature`
5. 打开 Pull Request

### PR 检查清单

- [ ] `python tests/smoke_test.py` 全通过
- [ ] 新增功能附带示例 `.mce`
- [ ] 错误信息使用中文，附错误码
- [ ] 更新相关文档（`docs/`）
- [ ] 更新 `CHANGELOG.md`

### Commit 规范

```
<type>: <subject>

[optional body]

[optional footer]
```

**示例**：

```
feat: 增加 calc.opr% 取模运算符

- parser.py: 支持 calc.opr% 语法
- type_checker.py: 类型检查
- codegen.py: 映射到 __mod__

Closes #12
```

---

## 报告问题

提交 Issue 时请附：

1. Macer 版本（`git rev-parse HEAD`）
2. Python 版本（`python --version`）
3. 复现用的 `.mce` 代码
4. 完整错误输出（含 `MCE` 错误码）
5. 运行命令

**模板**：

```
## 描述
（简要描述问题）

## 复现
1. 创建 xxx.mce
2. 运行 `python -m macer run xxx.mce`
3. 看到错误

## 期望
（期望行为）

## 实际
（实际输出，含完整报错）

## 环境
- Macer: abc1234
- Python: 3.11.0
- OS: Windows 11
```

---

## 目录结构约定

- **`src/macer/`**：编译器源码，**不改文件名**（避免 `import` 出错）
- **`stdlib/macer/`**：标准库，**包名必须和目录匹配**
- **`examples/`**：示例程序，**每个示例独立目录**
- **`tests/`**：测试文件，**以 `test_` 开头**
- **`docs/`**：文档，**Markdown 格式**

---

## 许可证

提交代码即表示同意以 [MIT 许可证](../LICENSE) 发布。