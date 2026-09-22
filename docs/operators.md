# 运算符重载

Macer 支持**自定义运算符重载**，通过 `calc.` 前缀声明。

## 支持的运算符

| 声明 | 用户书写 | 说明 |
|------|----------|------|
| `calc.get.opr(text: String)` | `obj[xxx]` | 索引读（**文本不求值**） |
| `calc.set.opr(text: String, v: T)` | `obj[xxx] = v` | 索引写 |
| `calc.opr+(other: T)` | `a + b` | 加法 |
| `calc.opr-(other: T)` | `a - b` | 减法 |
| `calc.opr*(other: T)` | `a * b` | 乘法 |
| `calc.opr/(other: T)` | `a / b` | 除法 |
| `calc.opr==(other: T)` | `a == b` | 相等 |
| `calc.opr!=(other: T)` | `a != b` | 不等 |
| `calc.opr<(other: T)` | `a < b` | 小于 |
| `calc.opr>(other: T)` | `a > b` | 大于 |

## 索引切片（`get.opr` / `set.opr`）

**关键特性**：`obj[...]` 里的内容**原样转字符串**，**不求值**。

### 声明

```macer
public class Object {
    // 索引读
    public func calc.get.opr(text: String) -> String {
        return text;
    }

    // 索引写
    public func calc.set.opr(text: String, value: Any) -> Void {
    }
}
```

### 使用

```macer
let o: Object = new Object();

print(o[hello]);              // "hello"
print(o[a:b]);                // "a:b"
print(o[lalal:yjfjfj-jf]);    // "lalal:yjfjfj-jf"
print(o[a[b[c]]]);            // "a[b[c]]"（嵌套也 OK）

o[key] = "value";             // 调 set.opr("key", "value")
```

**注意**：`o[x + 1]` **不会**做加法，而是把 `"x + 1"` 作为字符串传入。

### 子类覆盖

```macer
public class MyObj {
    public func calc.get.opr(text: String) -> String {
        return "MY:" + text;
    }
}

let m: MyObj = new MyObj();
print(m[hello]);      // "MY:hello"
```

## 二元运算符（`opr+` / `opr==`）

**注意**：`opr+` 等二元运算符的参数**是值**（不是字符串）。

### 加法

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

let a: Vec = new Vec(1);
let b: Vec = new Vec(2);
let c: Vec = a + b;         // 调 a.opr+(b)
print(str(c.x));            // 3
```

### 相等

```macer
public class Vec {
    public x: Int;

    public func calc.opr==(other: Vec) -> Bool {
        return self.x == other.x;
    }
}

let a: Vec = new Vec(1);
let b: Vec = new Vec(1);
print(str(a == b));         // True
```

### 减法

```macer
public class Vec {
    public x: Int;

    public func calc.opr-(other: Vec) -> Vec {
        return new Vec(self.x - other.x);
    }
}

let a: Vec = new Vec(5);
let b: Vec = new Vec(3);
let c: Vec = a - b;
print(str(c.x));            // 2
```

## `Object` 的默认实现

`macer.lang.Object` 提供了默认的 `get.opr` / `set.opr`：

```macer
package macer.lang;

public class Object {
    // 默认：返回原字符串
    public func calc.get.opr(text: String) -> String {
        return text;
    }

    // 默认：什么都不做
    public func calc.set.opr(text: String, value: Any) -> Void {
    }
}
```

**所有类**隐式继承 `Object`，所以 `obj[xxx]` 对任何类都可用。

## 实现映射（Python 后端）

| Macer | Python |
|-------|--------|
| `calc.get.opr` | `__getitem__` |
| `calc.set.opr` | `__setitem__` |
| `calc.opr+` | `__add__` |
| `calc.opr-` | `__sub__` |
| `calc.opr*` | `__mul__` |
| `calc.opr/` | `__truediv__` |
| `calc.opr==` | `__eq__` |
| `calc.opr!=` | `__ne__` |
| `calc.opr<` | `__lt__` |
| `calc.opr>` | `__gt__` |
| `obj[原始文本]` | `obj["原始文本"]` |

## 完整的字符串键映射示例

```macer
package com.example.operators;

import macer.lang.print;

public class Dict {
    public data: String;

    public func init() {
        self.data = "";
    }

    public func calc.get.opr(key: String) -> String {
        return "lookup(" + key + ")";
    }

    public func calc.set.opr(key: String, value: String) -> Void {
        self.data = key + " = " + value;
    }
}

func main() -> Void {
    let d: Dict = new Dict();

    print(d[user:name]);        // lookup(user:name)
    print(d[1 + 2]);            // lookup(1 + 2)  ← 不求值
    print(d[a[b[c]]]);          // lookup(a[b[c]])  ← 嵌套 OK

    d[user] = "alice";
    print(d.data);              // user = alice
}
```

## 错误码

| 码 | 含义 |
|----|------|
| `MCE3005` | 运算符参数个数不对 |
| `MCE3002` | 参数类型不匹配 |
| `MCE3007` | 类没定义该运算符 |

## 相关

- [语言参考](language-reference.md)
- [根基类 Object](object-base.md)
- [包系统](packages.md)