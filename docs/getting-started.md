# 快速开始

## 环境要求

- **Python 3.8+**
- 无需第三方依赖

## 安装

```bash
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

## 运行

在项目根目录执行：

```bash
python macer.py run hello.mce
```

输出：

```
Hello, Macer!
```

## 三种运行模式

### 1. 类型检查（不生成代码）

```bash
python macer.py check hello.mce
```

成功输出：

```
[macer] hello.mce 类型检查通过
```

### 2. 编译为 Python

```bash
python macer.py compile hello.mce -o hello.py
```

不指定 `-o` 则输出到 stdout：

```bash
python macer.py compile hello.mce
```

### 3. 编译并运行

```bash
python macer.py run hello.mce
```

## 下一步

- 学习[语言参考](language-reference.md)
- 查看[错误码表](error-codes.md)
- 了解[编译器架构](compiler-architecture.md)

## 一个稍大的例子

```macer
public class Point {
    public x: Int;
    public y: Int;

    public func init(x: Int, y: Int) {
        self.x = x;
        self.y = y;
    }

    public func norm2() -> Int {
        return self.x * self.x + self.y * self.y;
    }
}

func main() -> Void {
    let p: Point = new Point(3, 4);
    print("norm^2 = " + str(p.norm2()));
}
```

输出：

```
norm^2 = 25
```