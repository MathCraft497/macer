# 语言参考

本文档描述 Macer 语言的完整语法与语义。

## 目录

- [词法元素](#词法元素)
- [类型系统](#类型系统)
- [变量与常量](#变量与常量)
- [运算符](#运算符)
- [控制流](#控制流)
- [函数](#函数)
- [类与继承](#类与继承)
- [根基类 Object](#根基类-object)
- [包与导入](#包与导入)
- [运算符重载](#运算符重载)
- [内置库](#内置库)

---

## 词法元素

### 注释

```macer
// 单行注释

/*
   多行注释
*/
```

### 标识符

- 以字母或下划线开头
- 后可跟字母、数字、下划线
- 区分大小写

### 字面量

| 种类 | 示例 |
|------|------|
| 整数 | `42`、`-7`、`0` |
| 浮点数 | `3.14`、`0.5` |
| 字符串 | `"hello"`、`'world'` |
| 布尔 | `true`、`false` |
| 空值 | `null` |

字符串转义：`\n` `\t` `\r` `\\` `\"` `\'`

### 关键字

```
class    func    var      let      if       else
while    return  new      self     true     false
null     import  from     as       public   private
extends  calc    package
```

### 类型关键字

```
Int  Float  String  Bool  Void  Any
```

---

## 类型系统

Macer 是**静态类型**语言，所有可存储位置都必须显式标注类型。

### 基础类型

| 类型 | 含义 | 字面量示例 | 默认值 |
|------|------|-----------|--------|
| `Int` | 整数 | `42` | `0` |
| `Float` | 浮点数 | `3.14` | `0.0` |
| `String` | 字符串 | `"hi"` | `""` |
| `Bool` | 布尔 | `true` | `False` |
| `Void` | 无返回值 | — | — |
| `Any` | 任意类型 | — | `None` |

### 用户类类型

任何 `class` 定义的类名都是一个类型：

```macer
class Point {
    public x: Int;
    public y: Int;
}

func f(p: Point) -> Void { ... }
```

### 类型相容规则

赋值 `target := source` 合法，当：

1. `target` 与 `source` 是同一类型
2. `target` 是 `Any`，或 `source` 是 `Any`
3. `target = Float` 且 `source = Int`（数值提升）
4. `source` 是 `target` 的子类

示例：

```macer
let a: Float = 3;                      // OK：Int → Float
let b: Any = 42;                       // OK：Int → Any
let c: Greeter = new LoudGreeter("x"); // OK：子类 → 父类
```

---

## 变量与常量

```macer
// 可变变量
var count: Int = 0;
count = count + 1;

// 不可变变量（重新赋值报 MCE3008）
let name: String = "Macer";

// 无初始化（仅 Any 类型允许）
let thing: Any;
```

**规则**：`var` / `let` 声明必须带类型标注（`name: Type`）。

---

## 运算符

按优先级从低到高：

| 优先级 | 运算符 | 结合性 | 说明 |
|--------|--------|--------|------|
| 1 | `=` | 右 | 赋值 |
| 2 | `\|\|` | 左 | 逻辑或 |
| 3 | `&&` | 左 | 逻辑与 |
| 4 | `==` `!=` | 左 | 相等/不等 |
| 5 | `<` `>` `<=` `>=` | 左 | 比较 |
| 6 | `+` `-` | 左 | 加减（`+` 支持字符串拼接） |
| 7 | `*` `/` `%` | 左 | 乘除模 |
| 8 | `-` `!` | 右（一元） | 取负 / 逻辑非 |
| 9 | `.` `()` `[]` | 左 | 字段访问 / 调用 / 索引 |

### 类型规则

| 运算 | 要求 | 结果 |
|------|------|------|
| `+` | 两侧 `String` | `String` |
| `+ - * / %` | 两侧数值 | `Int` 或 `Float` |
| `< > <= >=` | 两侧数值 | `Bool` |
| `== !=` | 两侧类型兼容 | `Bool` |
| `&& \|\|` | 两侧 `Bool` | `Bool` |
| `!` | `Bool` | `Bool` |
| 一元 `-` | 数值 | 同侧 |

### 运算符重载

运算符可被类重载，见[运算符重载](#运算符重载)。

---

## 控制流

### if / else

```macer
if x > 0 {
    print("positive");
} else if x < 0 {
    print("negative");
} else {
    print("zero");
}
```

条件必须是 `Bool`（否则报 `MCE3010`）。

### while

```macer
var i: Int = 0;
while i < 10 {
    print(str(i));
    i = i + 1;
}
```

### return

```macer
func add(a: Int, b: Int) -> Int {
    return a + b;
}

func noop() -> Void {
    return;
}
```

### 语句块

```macer
{
    let temp: Int = 42;
    // temp 作用域仅限此块
}
```

---

## 函数

```macer
// 无返回值
func greet(name: String) -> Void {
    print("Hello, " + name + "!");
}

// 有返回值
func add(a: Int, b: Int) -> Int {
    return a + b;
}

// 省略返回类型 = Void
func ping() {
    print("pong");
}

// 声明式函数（无 body，用于内置库）
public func print(value: Any) -> Void;
```

- 顶层函数默认 `public`
- 参数必须标注类型
- 函数名在同一作用域不可重复
- `main()` 是程序入口（可选）

---

## 类与继承

### 定义类

```macer
public class Point {
    public x: Int;
    public y: Int;
    private secret: String;

    public func init(x: Int, y: Int) {
        self.x = x;
        self.y = y;
        self.secret = "hidden";
    }

    public func norm2() -> Int {
        return self.x * self.x + self.y * self.y;
    }

    private func helper() -> Void {
        print("internal");
    }
}
```

### 字段

- 语法：`[public|private] name: Type [= init];`
- 无初始值时默认值：
  - `Int → 0`
  - `Float → 0.0`
  - `String → ""`
  - `Bool → false`
  - 其他 → `None`

### 方法

- 语法：`[public|private] func name(params) -> Ret { ... }`
- 方法内通过 `self` 访问字段和方法
- `init` 是构造方法

### 创建实例

```macer
let p: Point = new Point(3, 4);
print(str(p.norm2()));
```

### 继承

```macer
public class Point3D extends Point {
    public z: Int;

    public func init(x: Int, y: Int, z: Int) {
        self.z = z;
        // 父类构造参数由编译器自动转发
    }

    public func norm2() -> Int {
        return self.x * self.x + self.y * self.y + self.z * self.z;
    }
}
```

- 子类方法可覆盖父类方法
- 子类实例可赋给父类类型变量

```macer
let p: Point = new Point3D(1, 2, 3);  // OK
```

---

## 根基类 Object

**`macer.lang.Object`** 是所有类的**隐式基类**（类似 Java 的 `java.lang.Object`）。

### 定义

`stdlib/macer/lang/Object.mce`：

```macer
package macer.lang;

public class Object {
    // 索引读：obj[xxx] -> get.opr("xxx")
    public func calc.get.opr(text: String) -> String {
        return text;
    }

    // 索引写：obj[xxx] = v -> set.opr("xxx", v)
    public func calc.set.opr(text: String, value: Any) -> Void {
    }

    public func toString() -> String {
        return "Object";
    }
}
```

### 隐式继承

所有类（不写 `extends`）**自动继承** `Object`：

```macer
public class App {          // 等价于 public class App extends Object
    // ...
}
```

### 所有类自动获得

- `obj[xxx]` — 索引读，默认返回原字符串
- `obj[xxx] = v` — 索引写
- `obj.toString()` — 返回 `"Object"`（子类可覆盖）

---

## 包与导入

### 包声明

```macer
package com.example.app;
```

**要求**：文件必须位于 `com/example/app/` 目录下。

### 导入

```macer
// 单类导入
import com.example.util.StringHelper;

// 包通配
import com.example.io.*;

// 别名
import com.example.util.StringHelper as Helper;

// 具名导入
from com.example.util import StringHelper, MathHelper;

// 内置函数也能导入
import macer.lang.print;
import macer.lang.str;
```

### 目录结构

```
project/
├── src/
│   └── com/example/app/
│       └── Main.mce          ← package com.example.app;
└── stdlib/                    ← 编译器提供的标准库
```

### 运行

```
python -m macer run --source-root src --source-root stdlib src/com/example/app/Main.mce
```

### 错误码

| 码 | 含义 |
|----|------|
| `MCE5001` | 找不到包或符号 |
| `MCE5002` | 包名与目录不匹配 |
| `MCE5003` | 循环依赖 |
| `MCE5004` | 重复定义的类 |
| `MCE5005` | 导入的符号不存在 |

---

## 运算符重载

通过 `calc.` 前缀声明运算符。

### 支持的运算符

| 声明 | 用户书写 | 说明 |
|------|----------|------|
| `calc.get.opr(text: String)` | `obj[xxx]` | 索引读，**文本不求值** |
| `calc.set.opr(text, v)` | `obj[xxx] = v` | 索引写 |
| `calc.opr+(other)` | `a + b` | 加法 |
| `calc.opr-(other)` | `a - b` | 减法 |
| `calc.opr*(other)` | `a * b` | 乘法 |
| `calc.opr/(other)` | `a / b` | 除法 |
| `calc.opr==(other)` | `a == b` | 相等 |
| `calc.opr!=(other)` | `a != b` | 不等 |
| `calc.opr<(other)` | `a < b` | 小于 |
| `calc.opr>(other)` | `a > b` | 大于 |

### 索引切片（`get.opr` / `set.opr`）

**关键**：方括号里的内容**原样转字符串**，**不求值**。

```macer
public class Object {
    public func calc.get.opr(text: String) -> String {
        return text;
    }
}

let o: Object = new Object();
print(o[hello]);              // "hello"
print(o[a:b]);                // "a:b"
print(o[lalal:yjfjfj-jf]);    // "lalal:yjfjfj-jf"
print(o[a[b[c]]]);            // "a[b[c]]"（支持嵌套）
```

**等价于**：

```macer
o.get.opr("hello")
o.get.opr("a:b")
o.get.opr("lalal:yjfjfj-jf")
```

### 索引写

```macer
o[key] = "value";      // 等价于 o.set.opr("key", "value")
```

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

let a: Vec = new Vec(1);
let b: Vec = new Vec(2);
let c: Vec = a + b;         // 调 a.opr+(b)
print(str(c.x));            // 3
print(str(a == b));         // False
```

### 实现映射（Python 后端）

| Macer | Python |
|-------|--------|
| `calc.get.opr` | `__getitem__` |
| `calc.set.opr` | `__setitem__` |
| `calc.opr+` | `__add__` |
| `calc.opr-` | `__sub__` |
| `calc.opr==` | `__eq__` |
| `calc.opr!=` | `__ne__` |

---

## 内置库

`stdlib/` 下声明。

### `macer.lang`（语言核心）

- `Object` — 根基类
- `print(value: Any) -> Void`
- `len(s: Any) -> Int`
- `str(v: Any) -> String`
- `int(v: Any) -> Int`
- `float(v: Any) -> Float`
- `abs(v: Any) -> Float`

### `macer.math`

- `Math` — 数学工具类（`PI`、`max`、`min`）

### `macer.io`

- `Console` — 控制台