r"""拉取洛谷题面与样例到本地（只留本机，不进 GitHub）。

用法:
    python code\洛谷\拉题.py P1308          # 拉指定题
    python code\洛谷\拉题.py P1308 P13224   # 拉多道

产物（都在 code\洛谷\题目\ 下，该目录已 gitignore）:
    <题号>.md         题面（描述 / 输入输出格式 / 提示）
    <题号>_in1.txt    样例 1 输入       <题号>_out1.txt   样例 1 输出
    <题号>_in2.txt    样例 2 输入       ...（有几组写几组）

题面藏在题目页面的 <script type="application/json"> 块里，
路径: data.problem.content.{description,inputFormat,outputFormat,hint} 与 data.problem.samples
"""
import json
import pathlib
import re
import sys

import requests

UA = {"User-Agent": "Mozilla/5.0"}
OUT_DIR = pathlib.Path(__file__).resolve().parent / "题目"
FIELDS = [("description", "题目描述"), ("inputFormat", "输入格式"),
          ("outputFormat", "输出格式"), ("hint", "提示")]


def fetch(pid):
    url = f"https://www.luogu.com.cn/problem/{pid}"
    html = requests.get(url, headers=UA, timeout=25).text
    for block in re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        problem = (data.get("data") or {}).get("problem")
        if problem:
            return problem
    raise RuntimeError(f"{pid}: 页面里没找到题目 JSON")


def save(problem):
    pid = problem["pid"]
    content = problem.get("content") or {}
    parts = [f"# {problem.get('name', '')}  ({pid})",
             f"> 难度值 {problem.get('difficulty')}｜标签 {problem.get('tags')}"
             f"｜通过 {problem.get('totalAccepted')}/{problem.get('totalSubmit')}"]
    for key, label in FIELDS:
        value = content.get(key)
        if value:
            parts.append(f"## {label}\n{value}")
    lines = ["\n\n".join(parts), ""]
    for i, sample in enumerate(problem.get("samples") or [], 1):
        text_in, text_out = sample[0], sample[1]
        lines.append(f"## 样例 {i} 输入\n```\n{text_in.rstrip()}\n```")
        lines.append(f"## 样例 {i} 输出\n```\n{text_out.rstrip()}\n```")
        (OUT_DIR / f"{pid}_in{i}.txt").write_text(text_in, encoding="utf-8")
        (OUT_DIR / f"{pid}_out{i}.txt").write_text(text_out, encoding="utf-8")
    (OUT_DIR / f"{pid}.md").write_text("\n\n".join(lines), encoding="utf-8")
    return len(problem.get("samples") or [])


def main(pids):
    OUT_DIR.mkdir(exist_ok=True)
    for pid in pids:
        try:
            n = save(fetch(pid))
            print(f"{pid}: 已保存题面 + {n} 组样例 -> {OUT_DIR}")
        except Exception as exc:                      # 抓不到就说清楚，不装成功
            print(f"{pid}: 失败 —— {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["P1308"])
