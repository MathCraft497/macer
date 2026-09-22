# 编译器架构

本文档描述 Macer 编译器的内部设计与模块职责。

## 目录

- [整体流水线](#整体流水线)
- [模块职责](#模块职责)
- [关键数据结构](#关键数据结构)
- [编译主流程](#编译主流程)
- [后端替换](#后端替换)

---

## 整体流水线

```
源代码 (.mce)
    │
    ▼
┌─────────┐    Token 流
│  Lexer  │ ─────────────►
└─────────┘
    │
    ▼
┌─────────┐    AST
│ Parser  │ ─────────────►
└─────────┘
    │
    ▼
┌──────────────┐   类型标注后的 AST
│ TypeChecker  │ ─────────────────►
└──────────────┘
    │
    ▼
┌─────────┐    Python 代码 (.py)
│ CodeGen │ ─────────────────►
└─────────┘
    │
    ▼
执行 / 输出
```

---

## 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 诊断 | `../src/macer/diagnostics.py` | 错误码、`Span`、`Diagnostic`、`DiagnosticBag`、渲染 |
| 词法 | `../src/macer/tokens.py` `../src/macer/lexer.py` | 源码 → Token 流 |
| 语法 | `../src/macer/ast_nodes.py` `../src/macer/parser.py` | Token 流 → AST |
| 类型 | `../src/macer/type_checker.py` | AST → 类型标注 + 静态检查 |
| 生成 | `../src/macer/codegen.py` | AST → Python 源码 |
| 主控 | `../src/macer/compiler.py` | 串联各阶段，捕获异常 |
| 运行时 | `../src/macer/runtime/runtime.py` | 内置函数实现 + 异常包装 |
| CLI | `macer.py` | 命令行入口 |

### 目录结构

```
macer/
├── macer.py
├── src/
│   ├── __init__.py
│   ├── diagnostics.py
│   ├── tokens.py
│   ├── lexer.py
│   ├── ast_nodes.py
│   ├── parser.py
│   ├── type_checker.py
│   ├── codegen.py
│   └── compiler.py
├── libs/
│   ├── __init__.py
│   ├── runtime.py
│   └── basic.mce
├── examples/
│   └── hello.mce
└── docs/
```

---

## 关键数据结构

### Token

```python
@dataclass
class Token:
    type: TokenType
    value: object
    line: int
    col: int
```

### AST 节点

- **表达式**：`IntLit` `FloatLit` `StringLit` `BoolLit` `NullLit`
  `Ident` `SelfExpr` `NewExpr` `Binary` `Unary` `Call` `FieldAccess` `Assign`
- **语句**：`VarDecl` `ExprStmt` `ReturnStmt` `IfStmt` `WhileStmt` `Block`
- **声明**：`FuncDecl` `ClassDecl` `FieldDecl` `ImportDecl` `Program`
- **类型**：`TypeNode(name, generics)`

### 诊断

```python
@dataclass
class Diagnostic:
    code: str
    severity: str
    message: str
    span: Optional[Span]
    filename: str
    note: Optional[str]
    note_span: Optional[Span]
```

### 符号与作用域

```python
class Symbol:
    name: str
    type: TypeNode
    mutable: bool
    kind: str          # var | field | param | func | self
    line: int
    func_sig: tuple    # 用于内置函数

class Scope:
    parent: Optional[Scope]
    symbols: dict      # name -> Symbol
```

### 类信息

```python
class ClassInfo:
    decl: ClassDecl
    name: str
    parent: Optional[str]
    fields: dict       # name -> FieldDecl
    methods: dict      # name -> FuncDecl

    def find_field(name, classes): ...
    def find_method(name, classes): ...
    def is_subclass_of(other, classes): ...
```

---

## 编译主流程

```python
def compile_source(self, source, filename):
    bag = DiagnosticBag()
    try:
        tokens = Lexer(source, filename, bag).tokenize()
        program = Parser(tokens, filename, bag).parse()
        TypeChecker(program, BUILTIN_FUNCS, filename, bag).check()
        code = CodeGen(program).generate()
        return CompileResult(code, bag, success=True, source=source)
    except MacerCompileError:
        return CompileResult(bag=bag, success=False, source=source)
    except RecursionError:
        # 转成 MCE2004
        ...
    except Exception as e:
        # 转成 MCE4099
        ...
```

### 异常隔离策略

- **编译期**：所有错误经 `MacerCompileError` 抛出，被 `Compiler` 捕获
- **运行期**：生成的 Python 代码由 `../src/macer/runtime/runtime.py` 的 `__macer_wrap__` 包裹
- **兜底**：`Compiler.compile_source` 的 `except Exception` 捕获任何内部错误，转成 `MCE4099`

---

## 后端替换

`CodeGen` 是唯一输出 Python 的模块。要改为 C / LLVM / WASM：

1. 新建 `codegen_c.py` 等
2. 保证接口是 `CodeGen(program).generate() -> str`（或 bytes）
3. 在 `compiler.py` 中切换

前端（词法、语法、类型）完全复用。

---

## 增加新语法

1. 在 `tokens.py` 的 `TokenType` 与 `KEYWORDS` 中加 Token
2. 在 `lexer.py` 中识别关键字/符号
3. 在 `ast_nodes.py` 中加 AST 节点
4. 在 `parser.py` 中加语法规则
5. 在 `type_checker.py` 中加类型规则
6. 在 `codegen.py` 中加代码生成

---

## 增加新内置函数

1. 在 `../src/macer/runtime/runtime.py` 中实现 Python 侧函数
2. 在 `../src/macer/compiler.py` 的 `BUILTIN_FUNCS` 注册签名
3. （可选）在 `../src/macer/runtime/basic.mce` 中写声明

---

## 支持多错误收集

当前 `_err` 直接 `raise` 中止。要做到"一次报告多个错误"：

1. 移除 `_err` 中的 `raise`
2. 在调用点判断错误状态并**跳过**当前子树
3. 在合适边界（`;` 或 `}`）恢复