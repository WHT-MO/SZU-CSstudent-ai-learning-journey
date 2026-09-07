i=3
while i > 0:
    print(i)
    i = i - 1
print("发射！")

for n in range(1,6):
    print(n)

for day in range(1,15):
    if day == 8:
        print("休整一天，跳过")
        continue
    if day == 13:
        print("提前收操")
        break
    print(f"军训第{day}天")

total = 0
for day in range(1,15):
    h =int(input(f"第{day}天的训练几小时？"))
    total = total + h
print(f"14天共{total}小时")

for i in range(1,4):
    for j in range(1,4):
        print(i, j, end="|")
    print()

#九九乘法表
for i in range(1,10):
    for j in range(1,i+1):
        print(f"{j}x{i}={j*i}",end="|")
    print()

#猜数字
answer = 7
while True:
    guess = int(input("猜数字："))
    if guess > answer:
        print("大了")
    elif guess < answer:
        print("小了")
    else:
        print("猜对了")
        break
    


