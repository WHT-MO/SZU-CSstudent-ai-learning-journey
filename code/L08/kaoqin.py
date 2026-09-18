#学习打卡
def daka(last,d):
    while True:
        x = int(input("1 = 打卡，2 = 查记录，0 = 退出："))
        if x == 1 and last == today - 1:
            last = today
            d = d + 1
            print(f"今天打卡成功，已连续打卡{d}天")
        elif x == 1 and last < today - 1:
            d = 1
            last = today
            print(f"今天打卡成功，已连续打卡{d}天")
        elif x == 1 and last == today:
            print("今天已经打卡过了")
        elif x == 2:
            print(f"上次打卡是第{last}天，连续打卡{d}天")
        elif x == 0:
            print("感谢使用。")
            break
    return last,d
def check(today):
    while last > today or today == 0:
        print("你确定没记错？")
        today = int(input("今天是第几天："))
    return today
d = 0
t = 0
last = int(input("上次打卡第几天："))
while t == 0:
    today = int(input("今天是第几天："))
    today = check(today)
    if last == today - 1 and d == 0 and last != 0:
        d = 1
    elif last == today and d == 0:
        d = 1
    elif last < today - 1 and d != 0:
        d = 0
    last,d = daka(last,d)
    t = int(input("继续请按0："))
    if t == 0:
        print(f"上次打卡第{last}天，欢迎继续使用。")
    else:
        break