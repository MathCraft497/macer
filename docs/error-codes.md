# 错误码表

Macer 拥有**独立于宿主语言的错误模型**，用户永远看不到 Python traceback。

## 错误码格式

```
MCE<段位><序号>
```

| 段位 | 分类 | 说明 |
|------|------|------|
| `0xxx` | 通用 | 文件、IO |
| `1xxx` | 词法 | 字符、字符串、数字 |
| `2xxx` | 语法 | 期望符号、赋值目标 |
| `3xxx` | 类型 | 未定义、不匹配、重复 |
| `4xxx` | 运行时 | 除零、空引用、越界 |
| `5xxx` | 包系统 | 包加载、导入、目录 |

---

## 通用（0xxx）

| 码 | 含义 |
|----|------|
| `MCE0001` | 文件未找到 |

---

## 词法（1xxx）

| 码 | 含义 |
|----|------|
| `MCE1001` | 无法识别的字符 |
| `MCE1002` | 字符串未闭合 |
| `MCE1003` | 非法转义字符 |
| `MCE1004` | 非法数字字面量 |

---

## 语法（2xxx）

| 码 | 含义 |
|----|------|
| `MCE2001` | 意外的 Token |
| `MCE2002` | 期望特定 Token |
| `MCE2003` | 非法赋值目标 |
| `MCE2004` | 语法嵌套过深 |

---

## 类型（3xxx）

| 码 | 含义 |
|----|------|
| `MCE3001` | 未定义的标识符 |
| `MCE3002` | 类型不匹配 |
| `MCE3003` | 重复定义 |
| `MCE3004` | 不可调用 |
| `MCE3005` | 参数个数不符 |
| `MCE3006` | 非类类型当作类使用 |
| `MCE3007` | 成员不存在 |
| `MCE3008` | 不可变变量赋值 |
| `MCE3009` | 返回类型不匹配 |
| `MCE3010` | 条件非 Bool |
| `MCE3011` | 方法不存在 |
| `MCE3012` | 运算符使用错误 |

---

## 运行时（4xxx）

| 码 | 含义 |
|----|------|
| `MCE4001` | 除以零 |
| `MCE4002` | 空引用访问 |
| `MCE4003` | 下标越界 / 键不存在 |
| `MCE4004` | 断言失败 |
| `MCE4005` | 栈溢出 |
| `MCE4099` | 未分类运行时错误 |

---

## 包系统（5xxx）

| 码 | 含义 | 触发场景 |
|----|------|----------|
| `MCE5001` | 找不到包或符号 | `import a.b.C` 但找不到 C |
| `MCE5002` | 包名与目录不匹配 | `package a.b;` 但文件不在 `a/b/` 下 |
| `MCE5003` | 循环依赖 | A import B，B import A |
| `MCE5004` | 重复定义的类 | 两个包下同名类冲突 |
| `MCE5005` | 导入的符号不存在 | `from a.b import X` 但 X 不存在 |

---

## 诊断格式

标准格式：

```
<severity>[<code>]: <message>
  --> <filename>:<line>:<col>
  |
N | <source line>
  | <caret underline>
  note: <additional info>       ← 可选
  |
M | <related source line>      ← 可选
  | <caret>
```

- `severity`：`error` / `warning` / `note`
- `caret underline`：`^` 重复出现，长度 = span 宽度
- `note`：补充上下文（如"上次声明在此"）

---

## 错误示例

### 词法错误（MCE1001）

输入：

```macer
func main() -> Void {
    let x: Int = 10 @ 20;
}
```

输出：

```
Macer 编译器遇到错误：
error[MCE1001]: 无法识别的字符 '@'
  --> demo.mce:2:19
  |
2 |     let x: Int = 10 @ 20;
  |                    ^

错误：1 个。编译终止。
```

### 类型不匹配（MCE3002）

输入：

```macer
func main() -> Void {
    let x: Int = "hello";
}
```

输出：

```
Macer 编译器遇到错误：
error[MCE3002]: 变量 'x' 初始化类型不匹配：String 无法赋给 Int
  --> demo.mce:2:17
  |
2 |     let x: Int = "hello";
  |                 ^

错误：1 个。编译终止。
```

### 重复定义（MCE3003，带 note）

输入：

```macer
func main() -> Void {
    let x: Int = 1;
    let x: Int = 2;
}
```

输出：

```
Macer 编译器遇到错误：
error[MCE3003]: 重复定义 'x'
  --> demo.mce:3:5
  |
3 |     let x: Int = 2;
  |     ^
  note: 'x' 上一次声明在第 2 行
  |
2 |     let x: Int = 1;
  |     ^

错误：1 个。编译终止。
```

### 包名目录不匹配（MCE5002）

输入（文件位于 `examples/objtest/Main.mce`）：

```macer
package com.example.objtest;
```

输出：

```
Macer 编译器遇到错误：
error[MCE5002]: 包名 'com.example.objtest' 与目录结构不匹配；
文件应位于 .../com/example/objtest/ 下
  --> examples/objtest/Main.mce

错误：1 个。编译终止。
```

### 找不到包（MCE5001）

输入：

```macer
import com.example.nothing.Foo;
```

输出：

```
Macer 编译器遇到错误：
error[MCE5001]: 找不到导入的符号 'com.example.nothing.Foo'
  --> main.mce

错误：1 个。编译终止。
```

### 运行时错误（MCE4001）

输入：

```macer
func main() -> Void {
    let a: Int = 10;
    let b: Int = 0;
    print(str(a / b));
}
```

输出：

```
error[MCE4001]: 除以零
```

**无 Python traceback**。