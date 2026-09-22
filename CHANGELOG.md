# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 与
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范。

## [Unreleased]

### 计划中

- `String` 类（用 `Char[]` 实现）
- `Char` 类型
- 数组类型 `T[]`
- `Object.toString()` 自动调用
- 接口 `interface`
- 泛型 `List<T>`
- 多错误收集
- LSP 服务器

## [0.1.0] - 2026-09-22

### 新增

- 词法分析器：注释、字面量、标识符、运算符
- 语法分析器：类、函数、控制流、表达式优先级
- 静态类型检查器：类型推断、赋值兼容、子类型、FQN 归一化
- 包系统：`package` / `import`，Java 风格目录匹配
- 根基类 `macer.lang.Object`：所有类隐式继承
- 运算符重载：`calc.opr+` / `calc.opr==` / `calc.get.opr` / `calc.set.opr`
- 索引切片：`obj[原始文本]`，不求值
- 代码生成器：多单元合并 + 拓扑排序
- 独立错误系统：`MCE` 错误码、Span 高亮、note 提示
- 运行时支持：内置函数 + 异常包装（无 Python traceback 泄露）
- CLI：`check` / `compile` / `run` 三个子命令
- `--source-root` 支持多次指定

### 语言特性

- 类型：`Int` `Float` `String` `Bool` `Void` `Any` 与用户类
- 声明：`var` `let`（不可变）
- 类与继承：`class` `extends` `self` `new`
- 控制流：`if/else` `while` `return`
- 运算符：算术、比较、逻辑、字段访问、调用、索引
- 包系统：`package` / `import`
- 运算符重载：`calc.*`
- 内置库：`print` `len` `str` `int` `float` `abs`

### 错误码

- `MCE0xxx`：通用
- `MCE1xxx`：词法
- `MCE2xxx`：语法
- `MCE3xxx`：类型
- `MCE4xxx`：运行时
- `MCE5xxx`：包系统