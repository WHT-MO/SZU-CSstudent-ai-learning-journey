n, m = map(int,input().split())
d = []
for _ in range(m + 1):
    d.append([0] * n)
d[0][0] = 1
for step in range(1,m + 1):
    for person in range(n):
        d[step][person] = d[step - 1][(person - 1) % n] + d[step - 1][(person + 1) % n]
print(d[m][0])