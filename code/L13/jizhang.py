from datetime import date
import json
import os

class Jizhang:
    def __init__(self):
        self.today = str(date.today())
        self.name = 0
        self.comein = 0
        self.comeback = 0
        self.path = os.path.join(os.path.dirname(__file__),"记账日志.txt")
        self.back = []

    def write(self):#存档
        self.name = input("你用的模型是：")
        self.comein = int(input("输入Tokens：")) + self.comein
        self.comeback = int(input("输出Tokens：")) + self.comeback
        self.back = [self.name,self.today,self.comein,self.comeback]
        with open(self.path,"w",encoding="utf-8") as f:
            json.dump(self.back,f,ensure_ascii=False)

    def read(self):#读档
        try:
            with open(self.path,"r",encoding="utf-8") as f:
                self.back = json.load(f)
                self.comein = self.back[2]
                self.comeback = self.back[3]
        except FileNotFoundError:
            print("还没有存档，这是第一次运行")

    def check(self):#看全部
        print(f"模型：{self.back[0]} 日期：{self.back[1]}\n输入：{self.back[2]} 输出：{self.back[3]}")

    def exit(self):#退出菜单
        print("感谢使用。")

data = Jizhang()
t = 0
while t == 0:
    data.read()
    while True:
        x = int(input("1 = 录入，2 = 查阅，0 = 退出"))
        if x == 1:
            data.write()
        elif x == 2:
            data.check()
        elif x == 0:
            data.exit()
            break
    t = int(input("继续请按0："))