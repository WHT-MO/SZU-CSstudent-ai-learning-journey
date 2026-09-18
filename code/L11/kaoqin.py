# ============================================================
# 军训打卡小程序 · 面向对象版（学员版，2026-09-15 · L11 class 入门）
# 由 code\L10\kaoqin.py（散装全局变量 + 函数版）改造而来：状态收进 Kaoqin 对象。
#
# 结构：类 Kaoqin 持三个属性 last / d / today
#   方法：daka(打卡) / see(查记录) / delete(清空存档) / exit(退出提示)
#         check(日期复核) / read(读档 + 问今天 + 兜底新用户) / write(写档) / special(初始特例筛查)
#   主循环只负责：读档 → 复核 → 特例 → 菜单 → 写档 → "继续请按0"
#
# 核心决策（学员自产）：
#   ① 状态全部住对象（self.last / self.d / self.today），程序里再无全局状态变量 ——
#      L10 版 check() 读全局 last 的隐患由此消失。
#   ② 方法内访问对象数据一律带 self. —— 记法："住对象的带 self，一趟性的不带"。
#   ③ read() 一个方法仍干三件事（读文件 / 问"今天是第几天" / 文件不存在当新用户）。
#      学员判断：三件属于同一职责"启动时把状态准备好"，永远一起改，故**不拆**。
#      将来的拆分信号（出现才拆）：㈠ 别处需要"只读档、不问用户"；㈡ 需要把状态直接注入
#      而不喂 stdin（自动化验收）。
#   ④ 构造器**不带参数**（形状乙）：__init__ 里直接写死新用户状态，调用写成 Kaoqin()。
#      收益：初值只留一处 —— read() 的 FileNotFoundError 分支只打印提示，不再重复赋值。
#
# 已知有意差异（学员 2026-09-15 决定，非缺陷）：
#   ① 清空存档 / 取消清空后 **留在菜单**（可继续操作）；L10 版是**直接退出菜单**。
#      理由（学员）：清空后可能还要接着用，将来会有其他功能，不必为此退出重进。
#   ② 程序运行中途若存档文件被删：本版**保留内存中的状态**继续用（因 read() 兜底不再重置），
#      L10 版会把它当新用户重置为 0/0/1。
#   除以上两条，其余行为与 L10 版逐字一致（见验收）。
#
# 验收（2026-09-15 教员对照 L10 版实跑）：
#   · 同一串输入喂两版 —— T1 新用户打卡→查记录→退出、T3 清空后重启第 2 天打卡：
#     输出与存档 **逐字/逐值一致**（存档分别为 1 1 / 2 1）。
#   · 本版新流程：清空确认 → "已清空" → 回菜单 → 按 0 退出 → 存档 [0 0]；
#     清空时取消 → 回菜单 → 退出 → 存档不变 [2 1]。
#
# 用法（存档落在 cwd，所以在本文件所在目录运行）：
#   cd D:\code\dsh\python-course\code\L11
#   python kaoqin.py
# ============================================================

class Kaoqin:
    def __init__(self):
        self.last = 0
        self.d = 0
        self.today = 1

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
               with open("打卡状态.txt","w",encoding="utf-8") as f:
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
        with open("打卡状态.txt","w",encoding="utf-8") as f:
            f.write(f"{self.last} {self.d}")

    def read(self):#读档
        try:
            with open("打卡状态.txt","r",encoding="utf-8") as f:
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
