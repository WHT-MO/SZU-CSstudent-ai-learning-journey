import sys

total = 0
n = 0
for line in sys.stdin:      # ← 有多少行就读多少行；读完了自动停下来（不报错）
    total = total + int(line)
    n = n + 1
print(n, total)