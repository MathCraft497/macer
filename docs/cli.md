# CLI 使用

## 命令格式

```
python -m macer <命令> [选项] <文件>
```

或安装后（`pip install -e .`）：

```
macer <命令> [选项] <文件>
```

## 子命令

| 命令 | 说明 |
|------|------|
| `check <file>` | 仅做词法/语法/类型检查，不生成代码 |
| `compile <file> [-o out]` | 编译为 Python；不带 `-o` 输出到 stdout |
| `run <file>` | 编译并立即运行 |

## 全局选项

| 选项 | 说明 |
|------|------|
| `--source-root <dir>` | 源码根目录（**可多次指定**），默认 `src` 和 `stdlib` |
| `--no-color` | 关闭彩色输出（非 TTY 时自动关闭） |

## 示例

### 类型检查

```
python -m macer check examples/hello.mce
```

成功输出：

```
[macer] examples/hello.mce 类型检查通过
```

失败输出：

```
Macer 编译器遇到错误：
error[MCE3002]: 变量 'x' 初始化类型不匹配：String 无法赋给 Int
  --> examples/hello.mce:2:17
  |
2 |     let x: Int = "hello";
  |                 ^

错误：1 个。编译终止。
```

### 编译为 Python 文件

```
python -m macer compile examples/hello.mce -o hello.py
```

输出：

```
[macer] 生成 hello.py
```

### 编译到 stdout

```
python -m macer compile examples/hello.mce
```

输出（截取）：

```python
# 由 Macer 编译器生成 —— 请勿手动修改
from __future__ import annotations
import sys
from macer.runtime import *
from macer.runtime import __macer_wrap__
...
```

### 编译并运行

```
python -m macer run examples/hello.mce
```

输出：

```
Hello, Macer!
```

### 使用多个 source-root

```
python -m macer run \
  --source-root examples/multi-package/src \
  --source-root stdlib \
  examples/multi-package/src/com/example/app/Main.mce
```

输出：

```
hello!!!
square(5) = 25
cube(3) = 27
max(10, 7) = 10
Math.PI = 3.141592653589793
```

### 关闭颜色

```
python -m macer --no-color check bad.mce
```

## `--source-root` 说明

`--source-root` 指定 **.mce 文件的搜索路径**。

**示例**：

假设目录结构：

```
project/
├── src/
│   └── com/example/app/Main.mce
└── stdlib/
    └── macer/lang/Object.mce
```

命令：

```
python -m macer run --source-root src --source-root stdlib src/com/example/app/Main.mce
```

**含义**：

- 入口文件：`src/com/example/app/Main.mce`
- 搜索根 1：`src/`（项目源码）
- 搜索根 2：`stdlib/`（标准库）

遇到 `import macer.lang.Object` 时：

1. 在 `src/macer/lang/Object.mce` 找 → 不存在
2. 在 `stdlib/macer/lang/Object.mce` 找 → 存在 ✅

**默认值**：如果不指定 `--source-root`，默认用 `["src", "stdlib"]`。

## 退出码

| 码 | 含义 |
|----|------|
| `0` | 成功 |
| `1` | 编译错误、运行时错误、文件未找到 |

## 中间产物

`run` 命令会在 `.mce` 同目录生成 `xxx.__macer__.py`。

- 这是**中间产物**，可安全删除
- 下次运行会重新生成
- 清理命令：
  - Linux/macOS：`rm *.__macer__.py`
  - Windows PowerShell：`Get-ChildItem -Recurse -Filter "*.__macer__.py" | Remove-Item -Force`

## 加入 PATH（可选）

### 安装到系统

```
pip install -e .
```

安装后可以直接：

```
macer run hello.mce
macer check hello.mce
macer compile hello.mce -o hello.py
```

### Linux / macOS 别名

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```
alias macer='python -m macer'
```

### Windows 批处理

创建 `macer.bat`，放入 PATH：

```bat
@echo off
python -m macer %*
```

## 常见问题

### Q：`python -m macer` 提示找不到模块

**原因**：没有安装到 Python 环境。

**解决**：

```
pip install -e .
```

或在项目根目录运行（`sys.path` 会包含当前目录）。

### Q：`--source-root` 报 `invalid choice`

**原因**：`cli.py` 是旧版，不支持该选项。

**解决**：更新 `cli.py`（见[编译器架构](compiler-architecture.md)）。

### Q：提示 `MCE5002 包名与目录不匹配`

**原因**：`package com.example.app;` 的文件不在 `com/example/app/` 目录下。

**解决**：调整目录结构，或改 `package` 声明。

### Q：`run` 后生成的 `.py` 能直接跑吗？

**可以**，但要设置 `PYTHONPATH`：

```
PYTHONPATH=src python xxx.__macer__.py
```

或安装 Macer（`pip install -e .`）后直接：

```
python xxx.__macer__.py
```

因为生成的代码里有 `from macer.runtime import *`。