# 包系统

Macer 采用 **Java 风格包系统**：包名与目录结构**必须一一对应**。

## 基本规则

```macer
// 文件：src/com/example/util/StringHelper.mce
package com.example.util;

public class StringHelper {
    public func upper(s: String) -> String {
        return s;
    }
}
```

**规则**：

- `package com.example.util;` → 文件**必须**在 `com/example/util/` 下
- 类名 `StringHelper` → 文件名**必须**是 `StringHelper.mce`
- 一个文件可有**一个 public 类**（和文件名同名）+ 任意 private 类

## 目录结构

```
project/
├── src/
│   └── com/
│       └── example/
│           ├── app/
│           │   └── Main.mce           ← package com.example.app;
│           └── util/
│               ├── StringHelper.mce   ← package com.example.util;
│               └── MathHelper.mce
└── stdlib/                            ← 编译器提供的标准库
    └── macer/
        ├── lang/
        │   ├── Object.mce
        │   └── basic.mce
        └── math/
            └── Math.mce
```

## 包声明

```macer
package com.example.app;
```

- 必须是文件**第一个非注释内容**
- 一个文件**只能有一个**
- 以 `;` 结尾（可省略）
- **必须与目录匹配**（否则报 `MCE5002`）

## import 语法

### 1. 单类导入

```macer
import com.example.util.StringHelper;
```

**含义**：加载 `com/example/util/StringHelper.mce`，把 `StringHelper` 引入当前文件的符号表。

### 2. 包通配

```macer
import com.example.io.*;
```

**含义**：加载 `com/example/io/` 下所有 `.mce`，把其中所有符号引入符号表。

### 3. 别名

```macer
import com.example.util.StringHelper as Helper;
```

**含义**：加载 `StringHelper`，在当前文件里用 `Helper` 引用它。

### 4. 具名导入

```macer
from com.example.util import StringHelper, MathHelper;
```

**含义**：分别加载两个类。

### 5. 内置函数

```macer
import macer.lang.print;
import macer.lang.str;
```

**含义**：从 `macer.lang` 包导入 `print` / `str` **符号**（函数）。

**加载器逻辑**：

1. 先试 `macer/lang/print.mce` → 不存在
2. 试 `macer/lang/print/` 目录 → 不存在
3. **回退**：加载 `macer/lang/` 包下所有文件
4. 从已加载符号里找 `print`

## 跨包访问

```macer
// 文件 A：com/example/util/StringHelper.mce
package com.example.util;

public class StringHelper {
    public func shout(s: String) -> String {
        return s + "!!!";
    }
}
```

```macer
// 文件 B：com/example/app/Main.mce
package com.example.app;

import com.example.util.StringHelper;
import macer.lang.print;

func main() -> Void {
    let sh: StringHelper = new StringHelper();
    print(sh.shout("hello"));     // hello!!!
}
```

## 运行时

编译时**自动加载**所有依赖的包：

```
python -m macer run \
  --source-root src \
  --source-root stdlib \
  src/com/example/app/Main.mce
```

`--source-root` 可**多次指定**，作为**搜索路径**。

**搜索顺序**：按 `--source-root` 给的顺序。

## 与 Object 的关系

所有类（不写 `extends`）**隐式继承** `macer.lang.Object`：

```macer
package com.example.app;

public class App {          // 隐式 extends Object
    // ...
}
```

详见 [根基类 Object](object-base.md)。

## 完整示例

### 目录

```
demo/
├── src/
│   └── com/
│       └── example/
│           ├── app/
│           │   └── Main.mce
│           └── util/
│               ├── StringHelper.mce
│               └── MathHelper.mce
└── stdlib/
    └── macer/
        ├── lang/
        └── math/
```

### `StringHelper.mce`

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

### `MathHelper.mce`

```macer
package com.example.util;

public class MathHelper {
    public func square(x: Int) -> Int {
        return x * x;
    }
}
```

### `Main.mce`

```macer
package com.example.app;

import com.example.util.StringHelper;
import com.example.util.MathHelper;
import macer.lang.print;
import macer.lang.str;

public class App {
    public func run() -> Void {
        let sh: StringHelper = new StringHelper();
        let mh: MathHelper = new MathHelper();

        print(sh.shout("hello"));
        print("square(5) = " + str(mh.square(5)));
    }
}

func main() -> Void {
    let app: App = new App();
    app.run();
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
square(5) = 25
```

## 错误码

| 码 | 含义 |
|----|------|
| `MCE5001` | 找不到包或符号 |
| `MCE5002` | 包名与目录不匹配 |
| `MCE5003` | 循环依赖 |
| `MCE5004` | 重复定义的类 |
| `MCE5005` | 导入的符号不存在 |

详见 [错误码表](error-codes.md)。

## 相关

- [语言参考](language-reference.md)
- [根基类 Object](object-base.md)
- [编译器架构](compiler-architecture.md)