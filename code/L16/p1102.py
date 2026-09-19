N,C = map(int,input().split())
nums = list(map(int,input().split()))
t = 0
treq = {}
for ch in nums:
    treq[ch] = treq.get(ch,0) + 1
for i in treq:
    x = treq.get(i + C, 0)
    if x != 0:
        t = t + treq[i]*treq[i + C]
print(t)