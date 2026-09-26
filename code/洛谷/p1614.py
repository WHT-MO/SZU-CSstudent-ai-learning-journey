n,m = map(int,input().split())
line = []
sums = 0
for _ in range(n):
    x = int(input())
    line.append(x)
if n == 0 or m == 0:
    print(0)
else:
    sums = sum(line[:m])
    min_sums = sums

    for i in range(m, n):
        sums = sums - line[i - m] + line[i]

        if sums < min_sums:
            min_sums = sums

    print(min_sums)