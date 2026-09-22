# 快速开始

## 环境要求

- **Python 3.8+**
- 无需第三方依赖

## 安装

```
git clone <repo> macer
cd macer
```

## 第一个程序

创建文件 `hello.mce`：

```macer
func main() -> Void {
    print("Hello, Macer!");
}
```

运行：

```
python -m macer run hello.mce
```

输出：

```
Hello, Macer!
```

## 三种运行模式

### 1. 类型检查（不生成代码）

```
python -m macer check hello.mce
```

成功输出：

```
[macer] hello.mce 类型检查通过
```

### 2. 编译为 Python

```
python -m macer compile hello.mce -o hello.py
```

不指定 `-o` 则输出到 stdout。

### 3. 编译并运行

```
python -m macer run hello.mce
```

## 类与继承

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

public class LoudGreeter extends Greeter {
    public func greet() -> Void {
        print("HELLO, " + self.name + "!!!");
    }
}

func main() -> Void {
    let g: Greeter = new Greeter("Macer");
    g.greet();

    let lg: Greeter = new LoudGreeter("World");
    lg.greet();
}
```

运行（先建好目录结构，见下节）：

```
python -m macer run \
  --source-root src \
  --source-root stdlib \
  src/com/example/app/Main.mce
```

输出：

```
Hello, Macer!
HELLO, World!!!
```

## 使用包系统

Macer 采用 **Java 风格包系统**：`package` 声明与目录结构必须一一对应。

### 目录结构

```
project/
├── src/
│   └── com/
│       └── example/
│           ├── app/
│           │   └── Main.mce        ← package com.example.app;
│           └── util/
│               └── StringHelper.mce ← package com.example.util;
└── stdlib/                          ← 编译器提供的标准库
```

### Main.mce

```macer
package com.example.app;

import com.example.util.StringHelper;
import macer.lang.print;
import macer.math.Math;

public class App {
    public func run() -> Void {
        let sh: StringHelper = new StringHelper();
        let math: Math = new Math();

        print(sh.shout("hello"));
        print("PI = " + str(math.PI));
    }
}

func main() -> Void {
    let app: App = new App();
    app.run();
}
```

### StringHelper.mce

```macer
package com.example.util;

public class StringHelper {
    public func upper(s: String) -> String {
        return s;
    }

    public func shout(s: String) -> String {
        return self.upper(s) + "!!!";
    }
}
```

### 运行

```
python -m macer run \
  --source-root src \
  --source-root stdlib \
  src/com/example/app/Main.mce
```

### 输出

```
hello!!!
PI = 3.141592653589793
```

### 常见错误

**MCE5002**：包名与目录不匹配

```
error[MCE5002]: 包名 'com.example.app' 与目录结构不匹配；
文件应位于 .../com/example/app/ 下
```

**解决**：确认 `package com.example.app;` 的文件确实位于 `com/example/app/` 目录下。

## 索引切片与运算符重载

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
    print(o[hello]);         // MY:hello
    print(o[a:b]);           // MY:a:b
}
```

**注意**：方括号里的内容**原样转字符串**，**不做求值**。

`o[a:b]` 会传给 `get.opr` 的 `text` 参数是 `"a:b"`，而不是一个 `a:b` 表达式。

### 二元运算符

```macer
public class Vec {
    public x: Int;

    public func init(x: Int) {
        self.x = x;
    }

    public func calc.opr+(other: Vec) -> Vec {
        return new Vec(self.x + other.x);
    }

    public func calc.opr==(other: Vec) -> Bool {
        return self.x == other.x;
    }
}

func main() -> Void {
    let a: Vec = new Vec(1);
    let b: Vec = new Vec(2);
    let c: Vec = a + b;         // 调 a.opr+(b)
    print(str(c.x));            // 3
    print(str(a == b));         // False
}
```

## 下一步

- 学习[语言参考](language-reference.md)
- 学习[包系统](packages.md)
- 学习[运算符重载](operators.md)
- 查看[错误码表](error-codes.md)
- 了解[编译器架构](compiler-architecture.md)