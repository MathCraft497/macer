# Macer

> 一门面向对象、静态类型的编程语言

Macer 支持类、继承、包系统、运算符重载、静态类型检查，
并带独立诊断系统（错误信息全部是 Macer 风格，绝不泄露 Python traceback）。

## 特性

- **面向对象**：类、字段、方法、继承（`extends`）、`self`
- **静态类型**：编译期类型检查，FQN 归一化
- **根基类**：`macer.lang.Object`，所有类隐式继承
- **包系统**：`package` / `import`，Java 风格目录匹配
- **运算符重载**：`calc.opr+` / `calc.opr==` / `calc.get.opr` / `calc.set.opr`
- **索引切片**：`obj[原始文本]`，方括号内容不求值，原样转字符串
- **独立诊断**：`MCE` 错误码 + 源码高亮
- **运行时隔离**：无 Python traceback 泄露
- **零依赖**：只用 Python 标准库

## 快速开始

```
git clone <repo> macer
cd macer
python -m macer run --source-root examples/multi-package/src --source-root stdlib examples/multi-package/src/com/example/app/Main.mce
```

输出：

```
hello!!!
square(5) = 25
cube(3) = 27
max(10, 7) = 10
Math.PI = 3.141592653589793
```

## 语言示例

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
}
```

## 项目结构

```
macer/
├── src/macer/        编译器源码
├── stdlib/           标准库（.mce）
├── examples/         示例
├── docs/             文档
└── pyproject.toml    打包配置
```

## 文档

- [语言参考](docs/language-reference.md)
- [错误码表](docs/error-codes.md)
- [CLI 使用](docs/cli.md)

## 许可证

MIT