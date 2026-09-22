# 多包示例

演示 Macer 包系统：
- `package` 声明
- `import` 单类 / 通配
- 目录结构与包名一致
- 跨包访问类

## 编译运行

```bash
macer run \
  --source-root examples/multi-package/src \
  --source-root stdlib \
  examples/multi-package/src/com/example/app/Main.mce
```

或者项目根已安装 Macer 时：

```bash
cd examples/multi-package
macer run src/com/example/app/Main.mce
```