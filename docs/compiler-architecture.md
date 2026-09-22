# 编译器架构

Macer 编译器用 Python 实现，分为**包加载 / 词法 / 语法 / 类型 / 代码生成**五个阶段。

## 编译流水线

```
源代码 (.mce)
    │
    ▼
┌──────────────────┐
│ PackageLoader    │  包加载 + 依赖解析
│                  │  import 处理 / 循环检测 / 目录校验
└──────────────────┘
    │  多个 LoadedUnit
    ▼
┌──────────┐
│  Lexer   │  Token 流
└──────────┘
    │
    ▼
┌──────────┐
│  Parser  │  AST
└──────────┘
    │
    ▼
┌──────────────┐
│ TypeChecker  │  类型标注 + 静态检查
│              │  FQN 归一化 / 隐式 Object 继承
└──────────────┘
    │
    ▼
┌──────────┐
│ CodeGen  │  Python 代码（合并所有单元）
└──────────┘
    │
    ▼
执行 / 输出
```

## 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 诊断 | `diagnostics.py` | 错误码、`Span`、`Diagnostic`、渲染 |
| 词法 | `tokens.py` / `lexer.py` | 源码 → Token |
| 语法 | `ast_nodes.py` / `parser.py` | Token → AST |
| 包加载 | `package_loader.py` | 扫描目录、递归加载 import |
| 类型 | `type_checker.py` | 类型推断、FQN 归一化、隐式继承 |
| 生成 | `codegen.py` | AST → Python（合并多单元、拓扑排序） |
| 主控 | `compiler.py` | 串联各阶段、捕获异常 |
| 运行时 | `runtime/runtime.py` | 内置函数、`__macer_wrap__` |
| 清单 | `manifest.py` | 解析 `Macer.toml` |
| 依赖 | `resolver.py` | 依赖解析 |
| CLI | `cli.py` | 命令行入口 |

## 目录结构

```
macer/
├── src/macer/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── compiler.py
│   ├── diagnostics.py
│   ├── tokens.py
│   ├── lexer.py
│   ├── ast_nodes.py
│   ├── parser.py
│   ├── package_loader.py
│   ├── type_checker.py
│   ├── codegen.py
│   ├── manifest.py
│   ├── resolver.py
│   └── runtime/
│       ├── __init__.py
│       ├── runtime.py
│       └── basic.mce
├── stdlib/
│   └── macer/
│       ├── lang/
│       │   ├── Object.mce
│       │   └── basic.mce
│       ├── math/
│       │   └── Math.mce
│       └── io/
│           └── Console.mce
├── examples/
├── docs/
└── pyproject.toml
```

## 关键数据结构

### Token

```python
@dataclass
class Token:
    type: TokenType
    value: object
    line: int
    col: int
    start_pos: int = 0      # 原始源码位置（用于切片字符串）
    end_pos: int = 0
```

### AST 节点

- **表达式**：`IntLit` `FloatLit` `StringLit` `BoolLit` `NullLit`
  `Ident` `SelfExpr` `NewExpr` `Binary` `Unary` `Call` `FieldAccess`
  `Assign` `SliceStringExpr` `IndexExpr` `IndexAssign`
- **语句**：`VarDecl` `ExprStmt` `ReturnStmt` `IfStmt` `WhileStmt` `Block`
- **声明**：`FuncDecl` `ClassDecl` `FieldDecl` `ImportDecl` `PackageDecl` `Program`
- **类型**：`TypeNode(name, generics, is_array, array_dims)`

### 诊断

```python
@dataclass
class Diagnostic:
    code: str
    severity: str          # error / warning / note
    message: str
    span: Optional[Span]
    filename: str
    note: Optional[str]
    note_span: Optional[Span]
```

### ClassInfo

```python
class ClassInfo:
    decl: ClassDecl
    name: str
    package: Optional[str]
    fqn: str                    # 全限定名（如 "macer.lang.Object"）
    parent_simple: Optional[str]
    parent_fqn: Optional[str]   # 解析后的父类 FQN
    fields: dict                # name -> FieldDecl
    methods: dict               # name -> FuncDecl
    operators: dict             # "get.opr" / "opr+" -> FuncDecl

    def find_field(self, name, classes): ...
    def find_method(self, name, classes): ...
    def find_operator(self, key, classes): ...
    def is_subclass_of(self, fqn, classes): ...
```

### LoadedUnit

```python
@dataclass
class LoadedUnit:
    package: Optional[str]
    filename: str
    source: str
    program: ast.Program
    symbol_table: dict          # 简单名 → ClassInfo / FuncDecl
```

## 编译主流程

```python
class Compiler:
    def compile_file(self, path, out_path=None):
        bag = DiagnosticBag()
        loader = PackageLoader(self.source_roots, bag)

        # 1. 包加载
        units = loader.load_project(path)

        if bag.has_errors():
            return CompileResult(bag=bag, success=False, source=...)

        # 2. 类型检查
        TypeChecker(units, self.basic_lib, path, bag).check()

        if bag.has_errors():
            return CompileResult(bag=bag, success=False, source=...)

        # 3. 代码生成
        code = CodeGen(units).generate()

        return CompileResult(code=code, bag=bag, success=True, source=...)
```

## PackageLoader 详解

### 加载流程

```
load_project(entry)
    │
    ▼
load_file(entry)
    ├─ 读取源码
    ├─ Lexer → tokens
    ├─ Parser → program
    ├─ 校验 package 与目录匹配
    ├─ 缓存 unit
    └─ 遍历 program.imports
        ├─ import a.b.C    → 加载 a/b/C.mce
        ├─ import a.b.*    → 加载 a/b/ 下所有 .mce
        ├─ from a.b import X → 加载 a/b/X.mce
        └─ 若失败，回退父包
```

### 目录校验

```python
def _verify_package_path(self, unit):
    if not unit.package:
        return
    pkg_path = unit.package.replace(".", os.sep)
    dir_path = os.path.dirname(unit.filename).replace(os.sep, "/")
    if not dir_path.endswith(pkg_path.replace(os.sep, "/")):
        # MCE5002
```

## TypeChecker 详解

### 关键流程

1. **收集所有类与函数** → 按 FQN 存到 `self.classes` / `self.functions`
2. **解析父类** → 无父类的类隐式继承 `macer.lang.Object`
3. **建立每单元的符号表** → 处理该单元的所有 import
4. **逐单元检查** → 类型推断 + 检查

### FQN 归一化

因为 `StringHelper` 和 `com.example.util.StringHelper` 都可能是同一个类，所以：

```python
def _normalize_type(self, t):
    if t.name in PSEUDO_TYPES:
        return t
    if t.name in self.classes:
        return t
    ci = self._resolve_class(t.name, self.current_unit)
    if ci is not None:
        return ast.TypeNode(ci.fqn, t.generics)
    return t
```

`is_assignable` 内部先归一化两侧再比较。

### 隐式 Object 继承

```python
OBJECT_FQN = "macer.lang.Object"

for ci in self.classes.values():
    if ci.fqn == OBJECT_FQN:
        ci.parent_fqn = None
    elif ci.parent_simple:
        # 显式继承
        parent = self._resolve_parent(ci.parent_simple, ci)
        ci.parent_fqn = parent.fqn
    elif OBJECT_FQN in self.classes:
        # 隐式继承
        ci.parent_fqn = OBJECT_FQN
```

## CodeGen 详解

### 拓扑排序

**所有类**（包括显式/隐式继承）先按继承关系排序，保证父类在子类之前：

```python
def visit(fqn):
    if fqn in visited:
        return
    visited.add(fqn)
    decl = self.classes[fqn]

    parent_fqn = None
    if decl.parent:
        parent_fqn = self._resolve_parent_fqn(decl.parent, ...)
    elif fqn != OBJECT_FQN and OBJECT_FQN in self.classes:
        parent_fqn = OBJECT_FQN  # 隐式继承

    if parent_fqn and parent_fqn in self.classes:
        visit(parent_fqn)

    result.append(fqn)

# 先访问 Object
if OBJECT_FQN in self.classes:
    visit(OBJECT_FQN)

for fqn in self.classes:
    visit(fqn)
```

### 命名规则

| 种类 | Macer 名 | Python 名 |
|------|----------|-----------|
| 类 | `macer.lang.Object` | `macer_lang_Object` |
| 顶层函数 `main` | `com.example.app.main` | `main`（固定名） |
| 顶层函数其他 | `macer.math.max` | `macer_math_max` |
| 类方法 | `run` | `run` |

### 运算符映射

| Macer | Python |
|-------|--------|
| `calc.get.opr` | `__getitem__` |
| `calc.set.opr` | `__setitem__` |
| `calc.opr+` | `__add__` |
| `calc.opr-` | `__sub__` |
| `calc.opr==` | `__eq__` |
| `calc.opr!=` | `__ne__` |

### 索引切片

```python
if isinstance(e, ast.IndexExpr):
    if isinstance(e.index, ast.SliceStringExpr):
        key = repr(e.index.raw)      # 原始文本 → 字符串字面量
    else:
        key = self.expr(e.index)
    return f"{self.expr(e.obj)}[{key}]"
```

## 运行时

`runtime/runtime.py` 提供：

- 内置函数：`print` / `len` / `str` / `int` / `float` / `abs`
- `MacerRuntimeErr` 异常类
- `__macer_wrap__(entry)` 包装入口，把 Python 异常转成 Macer 风格

```python
def __macer_wrap__(entry):
    try:
        entry()
    except MacerRuntimeErr as e:
        _emit(e.code, e.message)
        sys.exit(1)
    except ZeroDivisionError:
        _emit("MCE4001", "除以零")
        sys.exit(1)
    # ...
```

`runtime/__init__.py` 显式导出 `__macer_wrap__`（因为 `import *` 不带 `__` 开头的名字）。

## 异常隔离策略

- **编译期**：所有错误经 `MacerCompileError` 抛出，被 `Compiler` 捕获
- **运行期**：`__macer_wrap__` 包裹用户 `main`，把 Python 异常转成 `MCE4xxx`
- **兜底**：`Compiler.compile_source` 的 `except Exception` 捕获任何内部错误，转成 `MCE4099`

## 扩展指南

### 增加新语法

1. `tokens.py`：加 Token 类型
2. `lexer.py`：识别关键字/符号
3. `ast_nodes.py`：加 AST 节点
4. `parser.py`：加语法规则
5. `type_checker.py`：加类型规则
6. `codegen.py`：加代码生成

### 增加新内置函数

1. `runtime/runtime.py`：实现 Python 侧函数
2. `compiler.py` 的 `BUILTIN_FUNCS`：注册签名
3. `stdlib/macer/lang/basic.mce`：写声明

### 增加新错误码

在 `diagnostics.py` 的 `ErrCode` 类中追加常量，遵守段位规则。

### 替换后端

`CodeGen` 是唯一输出 Python 的模块。要改为 C / LLVM / WASM：

1. 新建 `codegen_c.py` 等
2. 保证接口是 `CodeGen(units).generate() -> str`
3. 在 `compiler.py` 中切换