# ============================================================
# 洛谷 P1598 垂直柱状图（学员重构版，2026-09-11）
# 存档说明：原 AC 代码（09-08）从未入库；本文件为 09-11 重构后的完整版本
# 重构目标：手打 26 字母表 → ord()/chr() + range() 生成（改码不改输出）
# 校验：样例输入 code/测试/p1598_sample_in.txt，输出与官方样例逐字符比对
#
# 卡点记录（已知边界，非缺陷）：
#   第 2 行 range(4) 写死行数——P1598 输入为一段文本、行数不固定；
#   "读到 EOF 为止"需要 import sys / sys.stdin 循环，属 L12 模块课内容，当前尚未解锁。
#   本版按本题官方样例的 4 行硬写；若输入行数变化会漏读或多读。
# ============================================================

freq = {}
for _ in range(4):
    line = input()
    for ch in line:
        if "A" <= ch <= "Z":
             freq[ch] = freq.get(ch,0) + 1
hmax = 0
for ch,c in freq.items():
    if hmax <= c:
        hmax = c
h = hmax
while h >= 1:
    line = ""
    for x in range(ord("A"),ord("Z") + 1):
        if freq.get(chr(x),0) >= h:
            line += "* "
        else:
            line += "  "
    print(line.rstrip())
    h = h - 1
y = ""
for x in range(ord("A"),ord("Z") + 1):
    y += chr(x) + " "
print(y.rstrip())
