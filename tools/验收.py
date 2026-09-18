#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收跑测器：一次跑完一道题的全部用例，默认只回一行结果。

用法：
    python tools\\验收.py <解答.py> <用例文件> [-v] [--timeout 10]

用例文件格式（一道题一个文件，人可读可改）：

    ### 01 官方样例
    3
    1 2 3
    ===
    2.00

    ### 02 重复最值只去一个
    4
    5 5 9 9
    ===
    7.00

    （`###` 起一个用例，`===` 之前是标准输入、之后是期望输出；`###` 之前可写自由注释）

判定口径（按洛谷）：
    * 忽略每行行末空格、忽略文末多余空行，其余逐字比较
    * 单例超时（默认 10 秒）即判失败 —— 防死循环把整轮跑测挂住

退出码：0 = 全过；1 = 有失败（只看 exit code 也够用）
"""
from __future__ import annotations

import os
import subprocess
import sys
import time


def parse_cases(path: str) -> list[tuple[str, str, str]]:
    """把用例文件解析成 [(用例名, 标准输入, 期望输出), ...]"""
    cases: list[tuple[str, str, str]] = []
    name: str | None = None
    buf: list[str] = []
    expect: list[str] = []
    in_expect = False

    def flush() -> None:
        if name is not None:
            cases.append((name, "\n".join(buf).strip("\n"), "\n".join(expect).strip("\n")))

    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.startswith("###"):
                flush()
                name = line[3:].strip() or f"用例{len(cases) + 1}"
                buf, expect, in_expect = [], [], False
                continue
            if name is None:
                continue                      # 文件头的自由注释
            if line.strip() == "===":
                in_expect = True
                continue
            (expect if in_expect else buf).append(line)
    flush()
    return cases


def norm(text: str) -> list[str]:
    """行末空格 + 文末空行不参与比较（OJ 口径）。"""
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def main(argv: list[str]) -> int:
    # Windows 控制台默认 GBK：直接打印中文/✓✗ 会 UnicodeEncodeError 或乱码 → 统一按 UTF-8 写。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    positional = [a for a in argv[1:] if not a.startswith("-")]
    verbose = "-v" in argv
    timeout = 10.0
    for i, a in enumerate(argv):
        if a == "--timeout" and i + 1 < len(argv):
            timeout = float(argv[i + 1])

    if len(positional) < 2:
        print(__doc__)
        return 2

    script, case_file = positional[0], positional[1]
    cases = parse_cases(case_file)
    if not cases:
        print(f"用例文件里没解析出用例：{case_file}")
        return 2

    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    fails: list[tuple[str, str, str, list[str]]] = []
    slowest = 0.0

    for name, stdin, want in cases:
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, script],
                input=stdin + "\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            fails.append((name, want, f"超时（>{timeout:g}s）—— 检查死循环", []))
            continue

        spent = time.perf_counter() - start
        slowest = max(slowest, spent)

        if proc.returncode != 0:
            tail = [ln for ln in proc.stderr.strip().splitlines() if ln.strip()][-3:]
            fails.append((name, want, f"运行出错（退出码 {proc.returncode}）", tail))
        elif norm(proc.stdout) != norm(want):
            fails.append((name, want, proc.stdout.rstrip("\n"), []))
        elif verbose:
            print(f"  ✓ {name}  {spent:.2f}s")

    total = len(cases)
    if not fails:
        print(f"PASS {total}/{total} · 最慢 {slowest:.2f}s")
        return 0

    shown = fails if verbose else fails[:3]
    print(f"FAIL {total - len(fails)}/{total} → " + ", ".join(n.split()[0] for n, *_ in fails))
    for name, want, got, err in shown:
        print(f"  ✗ {name}\n      期望 {want!r}\n      实际 {got!r}")
        for line in err:
            print(f"      {line}")
    if not verbose and len(fails) > len(shown):
        print(f"  … 另有 {len(fails) - len(shown)} 例失败（加 -v 看全部）")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
