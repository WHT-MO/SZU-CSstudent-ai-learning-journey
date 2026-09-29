M,N = map(int,input().split())
freq = {}
group = {}
for _ in range(M):
    ch,c = map(int,input().split())
    freq[ch] = freq.get(ch, c)
freq_d = dict(sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])))
nums = int (N * 1.5)
scores = list(freq_d.values())[nums - 1]
for i,j in freq_d.items():
    if j < scores:
        break
    group[i] = group.get(i, j)

print(scores,len(group))
for d,s in group.items():
    print(d,s)