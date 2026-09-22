# Macer

> 一门面向对象、静态类型的编程语言

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)

Macer 是一门语法简洁、类型安全、错误信息友好的静态类型编程语言。
编译器采用 Python 编写，可转译为 Python 直接运行。

## 特性

- **面向对象**：类、字段、方法、继承（`extends`）、`self`
- **静态类型**：编译期类型检查，支持子类型与数值提升
- **独立诊断**：类似 Rust/Elm 的错误提示，带错误码与源码高亮
- **零依赖**：仅需 Python 3.8+，无需任何第三方包

## 快速开始

```bash
git clone <repo> macer
cd macer
python macer.py run examples/hello.mce
```

输出：

```
Hello, Macer!
HELLO, World!!!
sum = 30
```

## 示例代码

```macer
public class Greeter {
    public name: String;

    public func init(name: String) {
        self.name = name;
    }

    public func greet() -> Void {
        print("Hello, " + self.name + "!");
    }
}

func main() -> Void {
    let g: Greeter = new Greeter("Macer");
    g.greet();
}
```

## 文档

- [文档首页](docs/index.md)
- [快速开始](docs/getting-started.md)
- [语言参考](docs/language-reference.md)
- [编译器架构](docs/compiler-architecture.md)
- [错误码表](docs/error-codes.md)
- [CLI 使用](docs/cli.md)
- [常见问题](docs/faq.md)
- [贡献指南](docs/contributing.md)

## 项目结构

```
macer/
├── macer.py          # CLI 入口
├── src/              # 编译器源码
├── libs/             # 运行时 + 内置库
├── examples/         # 示例程序
└── docs/             # 文档
```

## 环境要求

- Python 3.8+

## 许可证

本项目采用 [MIT 许可证](LICENSE)。