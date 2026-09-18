import os

class Kaoqin:
    def __init__(self):
        self.last = 0
        self.d = 0
        self.today = 1
        self.path = os.path.join(os.path.dirname(__file__), "打卡状态.txt")

    def daka(self):#打卡
        if self.last == self.today - 1:
            self.last = self.today
            self.d = self.d + 1
            print(f"今天打卡成功，已连续打卡{self.d}天")
        elif self.last < self.today - 1:
            self.d = 1
            self.last = self.today
            print(f"今天打卡成功，已连续打卡{self.d}天")
        elif self.last == self.today:
            print("今天已经打卡过了")

    def see(self):#查记录
        print(f"上次打卡是第{self.last}天，连续打卡{self.d}天")

    def delete(self):#清空存档
         daka_choose = 1
         while daka_choose != 0:
            daka_choose = int(input("你确定吗？(1 = 确定，0 = 取消)："))
            if daka_choose == 0:
               break
            elif daka_choose == 1:
               with open(self.path,"w",encoding="utf-8") as f:
                   self.last = 0
                   self.d = 0
                   f.write("0 0")
               print("已清空")
               break

    def exit(self):#退出菜单
        print("感谢使用。")

    def check(self):#检查日期
        while self.last > self.today or self.today == 0:
            print("你确定没记错？")
            self.today = int(input("今天是第几天："))

    def write(self):#写档
        with open(self.path,"w",encoding="utf-8") as f:
            f.write(f"{self.last} {self.d}")

    def read(self):#读档
        try:
            with open(self.path,"r",encoding="utf-8") as f:
                self.last,self.d = map(int,(f.read().split()))
                print(f"上次打卡第{self.last}天，已连续打卡{self.d}天")
                self.today = int(input("今天是第几天："))
        except FileNotFoundError:
            print("还没有存档，这是第一次运行")

    def special(self):#初始特例筛查
        if self.last == self.today - 1 and self.d == 0 and self.last != 0:
            self.d = 1
        elif self.last == self.today and self.d == 0:
            self.d = 1
        elif self.last < self.today - 1 and self.d != 0:
            self.d = 0

t = 0
data = Kaoqin()
while t == 0:
    data.read()
    data.check()
    data.special()
    while True:
        x = int(input("1 = 打卡，2 = 查记录，3 = 清空存档，0 = 退出："))
        if x == 1:
            data.daka()
        elif x == 2:
            data.see()
        elif x == 3:
            data.delete()
        elif x == 0:
            data.exit()
            break
    data.write()
    t = int(input("继续请按0："))
    if t == 0:
        print(f"上次打卡第{data.last}天，欢迎继续使用。")
    else:
        break
