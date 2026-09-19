nums = int(input())
x = {}
t = 0
for i in range(nums):
    x[i] = list(map(int,input().split()))
for ch,c in x.items():
    s = ch + 1
    for _ in range(len(x) - 1 - ch):
        if abs(c[0] - x[s][0]) <= 5 and abs(c[1] - x[s][1]) <= 5 and abs(c[2] - x[s][2]) <= 5 and abs((c[0] + c[1] + c[2]) - (x[s][0] + x[s][1] + x[s][2])) <= 10:
            t = t + 1
            s = s + 1
        else:
            s = s + 1
print(t)