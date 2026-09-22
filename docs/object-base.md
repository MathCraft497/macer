# 根基类 Object

`macer.lang.Object` 是 Macer 的**所有类的隐式基类**（类似 Java 的 `java.lang.Object`）。

## 定义

**`stdlib/macer/lang/Object.mce`**：

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

    // 字符串表示
    public func toString() -> String {
        return "Object";
    }
}
```

## 隐式继承

**所有类**（不写 `extends`）**自动继承** `Object`：

```macer
package com.example.app;

// 不写 extends，隐式继承 Object
public class App {
    public func run() -> Void {
        // ...
    }
}
```

**等价于**：

```macer
public class App extends macer.lang.Object {
    // ...
}
```

## 所有类自动获得的能力

| 能力 | 说明 |
|------|------|
| `obj[xxx]` | 索引读，默认返回原字符串 |
| `obj[xxx] = v` | 索引写，默认不做任何事 |
| `obj.toString()` | 返回 `"Object"`（子类可覆盖） |
| 类型相容 | `let o: Object = anyInstance;` 都合法 |

## 例子

```macer
package com.example.app;

import macer.lang.Object;
import macer.lang.print;

public class App {
    public func run() -> Void {
        let o: Object = new Object();
        print(o[hello]);         // hello
        print(o[a:b]);           // a:b
        print(o.toString());     // Object
    }
}

func main() -> Void {
    let app: App = new App();
    app.run();

    // 任何类都可以赋给 Object
    let obj: Object = app;
    print(obj.toString());       // Object（App 没覆盖）
}
```

## 覆盖 `Object` 的方法

子类可以覆盖 `get.opr` / `set.opr` / `toString`：

```macer
package com.example.app;

public class MyObj {
    public func calc.get.opr(text: String) -> String {
        return "MY:" + text;
    }

    public func toString() -> String {
        return "MyObj";
    }
}

func main() -> Void {
    let m: MyObj = new MyObj();
    print(m[hello]);           // MY:hello
    print(m.toString());       // MyObj

    // 通过 Object 引用访问时，仍调子类实现（动态分派）
    let o: Object = m;
    print(o[hello]);           // MY:hello
}
```

## 拓扑排序

**编译时**，类按以下顺序生成：

1. **`Object` 最前**
2. 然后其他类（按继承链拓扑排序）
3. 子类永远在父类之后

这样保证 Python 执行 `class Sub(Base):` 时 `Base` 已定义。

## 生成的 Python

`Object.mce` 生成：

```python
class macer_lang_Object:
    def __getitem__(self, text):
        return text

    def __setitem__(self, text, value):
        pass

    def toString(self):
        return "Object"
```

其他类继承它：

```python
class com_example_app_App(macer_lang_Object):
    def run(self):
        ...
```

## 未来扩展

计划加入：

- `Object.hashCode() -> Int`
- `Object.equals(other: Object) -> Bool`
- `Object.getClass() -> String`

## 相关

- [语言参考](language-reference.md)
- [运算符重载](operators.md)
- [包系统](packages.md)
- [编译器架构](compiler-architecture.md)