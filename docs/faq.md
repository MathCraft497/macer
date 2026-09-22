# 常见问题（FAQ）

## 语言设计

### Q1：为什么 Macer 用 Python 后端而不是 LLVM？

Python 后端让编译器实现更短、更易读，适合学习与快速原型。
前端（词法、语法、类型）完全独立于后端，要替换成 C / LLVM / WASM
只需重写 `codegen.py`。

### Q2：`Any` 会不会破坏类型安全？

`Any` 与任意类型可互相赋值，是**逃生口**。推荐只在必要时
（如与动态数据交互）使用。

### Q3：支持泛型吗？

当前版本**不支持**。词法和语法层预留了泛型括号 `<...>` 的解析，
但类型检查未实现。计划在后续版本加入。

### Q4：支持接口 / trait 吗？

当前版本**不支持**。可通过抽象基类 + 覆盖方法模拟。

### Q5：支持运算符重载吗？

**支持**。用 `calc.` 前缀声明：

```macer
public class Vec {
    public func calc.opr+(other: Vec) -> Vec {
        return new Vec(self.x + other.x);
    }
}
```

详见 [运算符重载](operators.md)。

### Q6：`obj[xxx]` 里的内容会求值吗？

**不会**。方括号里的内容**原样转字符串**。

```macer
let o: Object = new Object();
print(o[lalal:yjfjfj-jf]);   // 输出 "lalal:yjfjfj-jf"
print(o[a + b]);              // 输出 "a + b"（不是加法结果）
```

详见 [运算符重载](operators.md)。

### Q7：`Object` 是什么？

`macer.lang.Object` 是 Macer 的**根基类**，类似 Java 的 `java.lang.Object`。

- 所有类（不写 `extends`）**隐式继承** `Object`
- 提供默认的 `get.opr` / `set.opr` / `toString`
- 详见 [根基类 Object](object-base.md)

---

## 编译与运行

### Q8：为什么错误信息里看不到 Python 异常？

Macer 有**独立的诊断系统**：

- **编译期**：所有错误经 `MacerCompileError` 抛出，被 `Compiler` 捕获
- **运行期**：`libs/runtime.py` 的 `__macer_wrap__` 把 Python 异常转成 `MCE4xxx` 诊断
- **兜底**：任何内部错误都转成 `MCE4099`，不泄露 traceback

### Q9：`import` 能跨文件吗？

**能**。`package_loader.py` 会递归加载所有 `import` 的包。

```macer
package com.example.app;

import com.example.util.StringHelper;   // 加载 com/example/util/StringHelper.mce
import macer.math.Math;                 // 加载 stdlib/macer/math/Math.mce
```

### Q10：`import macer.lang.print` 是什么？

从 `macer.lang` 包里导入 `print` **符号**（函数）。

加载器会：

1. 先试 `macer/lang/print.mce` → 不存在
2. 试 `macer/lang/print/` 目录 → 不存在
3. **回退**：加载 `macer/lang/` 包下所有文件
4. 从已加载的符号里找 `print`

### Q11：`init` 里为什么不用显式调用父类构造？

`CodeGen.gen_ctor` 会在用户 `init` 体之前**自动插入**：

```python
ParentClass.__init__(self, ...)
```

并把父类构造参数按名称转发。

### Q12：运行 `run` 生成的 `.__macer__.py` 是什么？

编译器的**中间产物**（Python 代码），会放在 `.mce` 同目录。

- 可安全删除
- 下次运行会重新生成
- 清理：`Get-ChildItem -Recurse -Filter "*.__macer__.py" | Remove-Item -Force`

---

## 包系统

### Q13：`package` 声明必须和目录匹配吗？

**必须**。Macer 采用 **Java 风格**：

```macer
package com.example.app;
```

文件**必须**位于 `com/example/app/` 目录下。否则报 `MCE5002`。

**为什么这么设计**：让代码组织清晰、避免命名冲突。

### Q14：怎么修复 `MCE5002`（包名与目录不匹配）？

**两种方式**：

1. **移动文件**：把 `.mce` 移到与 `package` 声明匹配的目录下
2. **改 `package`**：把声明的包名改成与目录匹配

**推荐第 1 种**（保持目录结构规范）。

### Q15：找不到 `macer.lang.Object` 怎么办？

**检查**：

1. 有 `stdlib/macer/lang/Object.mce` 吗？
2. 运行时指定了 `--source-root stdlib` 吗？

```bash
python -m macer run --source-root src --source-root stdlib src/Main.mce
```

### Q16：`MCE5001 找不到包` 怎么办？

**检查**：

1. 拼写对不对？
2. 目录结构对不对？
3. `--source-root` 是否包含了文件所在根？

### Q17：能循环 import 吗？

**不能**。加载器检测循环依赖，报 `MCE5003`。

**解决**：拆分共同依赖到第三个包，或用接口解耦。

---

## 打包与发布

### Q18：需要虚拟环境吗？

**不需要**。Macer 只用 Python 标准库，不安装任何 pip 包。

### Q19：会不会污染 Python 环境？

**不会**。删掉整个 `macer/` 目录就等于卸载完毕。

### Q20：`pip install -e .` 报错怎么办？

**常见错误**：

- **`does not appear to be a Python project`** → 缺 `pyproject.toml`
- **`Invalid statement (at line 1, column 1)`** → `pyproject.toml` 有 BOM
- **`Multiple top-level packages discovered`** → `pyproject.toml` 缺 `[tool.setuptools.packages.find]`

**修复**：确认 `pyproject.toml` 存在且无 BOM。

### Q21：`macer` 命令和 `python -m macer` 区别？

- `macer`：安装后（`pip install -e .`）可用
- `python -m macer`：任何情况都可用（需在项目根或已安装）

### Q22：怎么发布到 PyPI？

```bash
pip install build twine
python -m build
python -m twine upload dist/*
```

详见 [贡献指南](contributing.md)。

---

## 开发

### Q23：编译器自身报错怎么办？

理论上不会。`Compiler.compile_source` 有 `except Exception` 兜底，
会把任何内部错误也转成 `MCE4099`，不泄露 Python traceback。

**如果真遇到**：把完整报错贴到 GitHub Issues。

### Q24：怎么扩展语言？

见 [编译器架构](compiler-architecture.md) 的"扩展指南"章节。

### Q25：怎么写测试？

`tests/smoke_test.py` 提供回归测试框架。跑：

```bash
python tests/smoke_test.py
```

### Q26：怎么回退到某个版本？

```bash
git log --oneline
git reset --soft <commit>
# 或
git reset --hard <commit>
```

### Q27：`main` 函数是必须的吗？

**不是**。如果没有 `main`，编译器不生成入口，可把 `.mce` 当库用。

---

## 未来计划

### Q28：会支持哪些新特性？

按优先级：

1. `String` 类（用 `Char[]` 实现）
2. `Char` 类型
3. 数组类型 `T[]`
4. `Object.toString()` 自动调用（`"a" + obj`）
5. 接口 `interface`
6. 泛型 `List<T>`
7. 多错误收集（一次报多个）
8. LSP 服务器

### Q29：会支持自举吗？

长期目标：**用 Macer 自己重写 Macer 编译器**。

### Q30：会支持原生编译吗？

长期目标：**LLVM / C 后端**。前端已经和 Python 后端解耦。

---

## 其他

### Q31：为什么叫 "Macer"？

Macer 是 "**M**odern **A**nd **C**lean **E**xperimental **R**untime" 的缩写。
或者就是随口起的名字。

### Q32：许可证是什么？

**MIT**。可自由使用、修改、商用。

### Q33：怎么贡献？

见 [贡献指南](contributing.md)。