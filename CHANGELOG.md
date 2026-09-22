# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 与
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范。

## [Unreleased]

### 计划中

- 模块系统（真实加载 `import`）
- 多错误收集（一次报告多个错误）
- 彩色诊断的精细控制
- LSP 服务器

## [0.1.0] - 2024-XX-XX

### 新增

- 词法分析器：注释、字面量、标识符、运算符
- 语法分析器：类、函数、控制流、表达式优先级
- 静态类型检查器：类型推断、赋值兼容、子类型
- 代码生成器：转译为 Python
- 独立错误系统：错误码、Span 高亮、note 提示
- 运行时支持：内置函数 + 异常包装（无 Python traceback 泄露）
- CLI：`check` / `compile` / `run` 三个子命令

### 语言特性

- 类型：`Int` `Float` `String` `Bool` `Void` `Any` 与用户类
- 声明：`var` `let`（不可变）
- 类与继承：`class` `extends` `self` `new`
- 控制流：`if/else` `while` `return`
- 运算符：算术、比较、逻辑、字段访问、调用
- 内置库：`print` `len` `str` `int` `float` `abs`