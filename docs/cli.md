# CLI 使用

## 命令格式

```bash
python macer.py <command> <file> [options]
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
| `--no-color` | 关闭彩色输出（非 TTY 时自动关闭） |

## 示例

### 类型检查

```bash
python macer.py check examples/hello.mce
```

成功输出：

```
[macer] examples/hello.mce 类型检查通过
```

失败输出（示例）：

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

```bash
python macer.py compile examples/hello.mce -o hello.py
```

输出：

```
[macer] 生成 hello.py
```

### 编译到 stdout

```bash
python macer.py compile examples/hello.mce
```

输出（截取）：

```python
# 由 Macer 编译器生成 —— 请勿手动修改
from __future__ import annotations
import sys
from src.macer.runtime.runtime import *

...
```

### 编译并运行

```bash
python macer.py run examples/hello.mce
```

输出：

```
Hello, Macer!
HELLO, World!!!
sum = 30
```

### 关闭颜色

```bash
python macer.py --no-color check bad.mce
```

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
  - Windows：`del *.__macer__.py`

## 加入 PATH（可选）

### Linux / macOS

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
alias macer='python ~/projects/macer/macer.py'
```

然后：

```bash
macer run hello.mce
```

### Windows

创建 `macer.bat`，放入 PATH：

```bat
@echo off
python "D:\projects\macer\macer.py" %*
```