#可视化字母统计柱状图
freq = {} #创造空dict
for _ in range(4): #储存四行输入的字母并计数
    line = input()
    for ch in line:
        if "A" <= ch and "Z" >= ch:
             freq[ch] = freq.get(ch,0) + 1
hmax = 0 #最高一层
for ch,c in freq.items(): #找哪个字母层最高
    if c > hmax: 
        hmax = c
h = hmax 
while h >= 1: #依次往下层输出
    line = ""
    for x in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if freq.get(x,0) >= h:
                line += "* "
        else:
                line += "  "
    print(line.rstrip())
    h = h - 1 
y = "" #最底层字母
for x in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":  #按顺序输出底层字母
    y += x + " "
print(y.rstrip)  #题目要求，去尾空格            