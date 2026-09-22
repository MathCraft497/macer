"""Macer 编译器 CLI"""
import sys
import os
import subprocess
import argparse

from .compiler import Compiler
from .diagnostics import (
    print_diagnostics, print_banner, Color, ErrCode, Severity,
    Diagnostic, DiagnosticBag,
)


def _fail(result):
    print_banner()
    print_diagnostics(result.bag, result.source, "<source>")
    print(file=sys.stderr)
    n = result.bag.error_count()
    print(Color.wrap(f"错误：{n} 个。编译终止。", Color.RED), file=sys.stderr)
    sys.exit(1)


def _add_common_args(parser):
    """所有子命令共享的选项"""
    parser.add_argument(
        "--source-root", action="append", default=None,
        help="源码根目录（可多次指定），默认 src 和 stdlib",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="关闭彩色输出",
    )


def main():
    ap = argparse.ArgumentParser(prog="macer", description="Macer 语言编译器")
    _add_common_args(ap)

    sub = ap.add_subparsers(dest="cmd", required=True)

    # 共享 parent，让子命令也能识别这些选项
    common = argparse.ArgumentParser(add_help=False)
    _add_common_args(common)

    c = sub.add_parser("compile", parents=[common], help="编译 .mce 文件")
    c.add_argument("file")
    c.add_argument("-o", "--out", default=None)

    r = sub.add_parser("run", parents=[common], help="编译并直接运行")
    r.add_argument("file")

    t = sub.add_parser("check", parents=[common], help="仅做类型检查")
    t.add_argument("file")

    args = ap.parse_args()

    # 合并顶层与子命令的 source_root / no_color
    source_roots = args.source_root or ["src", "stdlib"]
    no_color = args.no_color or not sys.stderr.isatty()

    if no_color:
        Color.disable()

    compiler = Compiler(source_roots=source_roots)

    if args.cmd == "compile":
        result = compiler.compile_file(args.file, args.out)
        if not result.success:
            _fail(result)
        if not args.out:
            sys.stdout.write(result.code)
            if not result.code.endswith("\n"):
                sys.stdout.write("\n")
        else:
            print(f"[macer] 生成 {args.out}")

    elif args.cmd == "check":
        result = compiler.compile_file(args.file)
        if not result.success:
            _fail(result)
        print(f"[macer] {args.file} 类型检查通过")

    elif args.cmd == "run":
        out_py = args.file.replace(".mce", ".__macer__.py")
        result = compiler.compile_file(args.file, out_py)
        if not result.success:
            _fail(result)

        env = dict(os.environ)
        pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env["PYTHONPATH"] = pkg_root + os.pathsep + env.get("PYTHONPATH", "")

        proc = subprocess.run([sys.executable, out_py], env=env)
        sys.exit(proc.returncode)


if __name__ == "__main__":
    main()