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
- [内置库](#内置库)
- [导入](#导入)

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
extends
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

// 不可变变量（重新赋值会报 MCE3008）
let name: String = "Macer";
// name = "X";   // 错误

// 无初始化（仅 Any 类型允许，否则报 MCE3002）
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
| 6 | `+` `-` | 左 | 加减 |
| 7 | `*` `/` `%` | 左 | 乘除模 |
| 8 | `-` `!` | 右（一元） | 取负 / 逻辑非 |
| 9 | `.` `()` | 左 | 字段访问 / 调用 |

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
- 方法内通过 `self` 访问字段和其他方法
- `init` 是特殊方法：构造时调用

### 创建实例

```macer
let p: Point = new Point(3, 4);
print(str(p.norm2()));  // 25
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

- 用 `extends` 指定父类
- 子类方法可覆盖父类方法
- 子类实例可赋给父类类型变量

```macer
let p: Point = new Point3D(1, 2, 3);  // OK
```

---

## 内置库

`../src/macer/runtime/basic.mce` 声明以下内置符号，用户程序无需 import 即可使用。

### 内置函数

| 签名 | 说明 |
|------|------|
| `print(value: Any) -> Void` | 打印 |
| `len(s: Any) -> Int` | 长度 |
| `str(v: Any) -> String` | 转字符串 |
| `int(v: Any) -> Int` | 转整数 |
| `float(v: Any) -> Float` | 转浮点 |
| `abs(v: Any) -> Float` | 绝对值 |

### 内置类

```macer
public class Math {
    public PI: Float = 3.141592653589793;
    public func max(a: Int, b: Int) -> Int { ... }
    public func min(a: Int, b: Int) -> Int { ... }
}

public class StringUtils {
    public func concat(a: String, b: String) -> String { ... }
    public func isEmpty(s: String) -> Bool { ... }
}
```

---

## 导入

语法：

```macer
// 整模块导入
import geometry;
import math.utils;
import math.utils as mu;

// 具名导入
from geometry import Point, Circle;
```

> **注意**：当前编译器对 `import` 仅做语法解析，未实现模块加载。
> 多文件场景建议合并编译或扩展 `Compiler`。