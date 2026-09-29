n = input()
line = []
t = 0
for i in n[:-1]:
    if i != "-":
        line.append(int(i))
for j in range(1,10):
    t += j * line[j - 1]
last = n[-1]
if t % 11 == 10:
    check = "X"
else:
    check = str(t % 11)

if check == last:
    print("Right")
else:
    print(n[:-1] + check)