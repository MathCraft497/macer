# Macer 文档

欢迎使用 **Macer** —— 一门面向对象、静态类型的编程语言。

## 特性速览

- **面向对象**：类、字段、方法、继承、`self`
- **静态类型**：编译期类型检查，FQN 归一化
- **根基类**：`macer.lang.Object`，所有类隐式继承
- **包系统**：`package` / `import`，Java 风格目录匹配
- **运算符重载**：`calc.opr+` / `calc.get.opr` / `calc.set.opr`
- **索引切片**：`obj[原始文本]`，不求值
- **独立诊断**：`MCE` 错误码 + 源码高亮
- **零依赖**：只用 Python 标准库

## 目录

### 入门

- [快速开始](getting-started.md) — 5 分钟上手
- [CLI 使用](cli.md) — 命令行工具

### 语言

- [语言参考](language-reference.md) — 完整的语法与语义
- [包系统](packages.md) — `package` / `import` / 目录匹配
- [运算符重载](operators.md) — `calc.opr+` / `calc.get.opr` / `calc.set.opr`
- [根基类 Object](object-base.md) — 所有类隐式继承

### 编译器

- [编译器架构](compiler-architecture.md) — 编译流水线与内部设计
- [贡献指南](contributing.md) — 如何扩展编译器
- [错误码表](error-codes.md) — 所有诊断码速查

### 其他

- [常见问题](faq.md) — FAQ

## 快速开始

```
git clone <repo> macer
cd macer

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

## 示例代码

### Hello World

```macer
func main() -> Void {
    print("Hello, Macer!");
}
```

### 类与继承

```macer
package com.example.app;

import macer.lang.print;

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

### 索引切片

```macer
package com.example.objtest;

import macer.lang.Object;
import macer.lang.print;

public class MyObj {
    public func calc.get.opr(text: String) -> String {
        return "MY:" + text;
    }
}

func main() -> Void {
    let o: MyObj = new MyObj();
    print(o[hello]);          // MY:hello
    print(o[a:b]);            // MY:a:b
}
```

### 运算符重载

```macer
public class Vec {
    public x: Int;

    public func init(x: Int) {
        self.x = x;
    }

    public func calc.opr+(other: Vec) -> Vec {
        return new Vec(self.x + other.x);
    }
}

func main() -> Void {
    let a: Vec = new Vec(1);
    let b: Vec = new Vec(2);
    let c: Vec = a + b;      // 调 a.opr+(b)
    print(str(c.x));         // 3
}
```

## 项目结构

```
macer/
├── src/macer/        编译器源码
├── stdlib/           标准库（.mce）
├── examples/         示例程序
├── docs/             文档
├── tests/            测试
└── pyproject.toml    打包配置
```

## 环境要求

- Python 3.8+
- 无需第三方依赖

## 版本

当前版本：**v0.1.0**

## 许可证

MIT