freq = {}#freq是频率，ch是频道/字符
for _ in range(4):
    line = input()
    for ch in line:
        if "A" <= ch <= "Z":#又忘记过滤A-Z
             freq[ch] = freq.get(ch,0) + 1
hmax = 0
for ch,c in freq.items():
    if hmax <= c:
        hmax = c
h = hmax
while h >= 1:
    line = ""#重名使用，以后要注意
    for x in range(ord("A"),ord("Z") + 1):
        if freq.get(chr(x),0) >= h:
            line += "* "#列宽没对齐
        else:
            line += "  "
    print(line.rstrip())
    h = h - 1#没改判定条件陷入死循环了
y = ""
for x in range(ord("A"),ord("Z") + 1):
    y += chr(x) + " "
print(y.rstrip())    
