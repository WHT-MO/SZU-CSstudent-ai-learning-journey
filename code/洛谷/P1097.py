n = int(input())
line = []
freq = {}
for _ in range(n):
    i = int(input())
    line.append(i)
for ch in line:
    freq[ch] = freq.get(ch, 0) + 1
freq_d = dict(sorted(freq.items()))
for i,j in freq_d.items():
    print(i,j)
