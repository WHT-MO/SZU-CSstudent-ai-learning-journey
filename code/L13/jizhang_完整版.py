from datetime import date
import json
import os


class Jizhang:
    def __init__(self):
        # 存档跟脚本走，不跟 cwd 走（L12 的教训）
        self.path = os.path.join(os.path.dirname(__file__), "记账日志.json")
        self.records = []      # 明细：一条记录 = 一个字典
        self.load()            # 开程序先把旧记录读回来

    # ---------- 存档：先读后写 ----------
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.records = json.load(f)
        except FileNotFoundError:
            self.records = []
            print("还没有存档，这是第一次运行")

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)

    # ---------- 小工具：只要数字 ----------
    def ask_int(self, tip):
        while True:
            try:
                return int(input(tip))
            except ValueError:
                print("这里要填数字，再试一次")

    # ---------- 功能 1：记一笔 ----------
    def add(self):
        name = input("你用的模型是：")
        comein = self.ask_int("输入 Tokens：")
        comeback = self.ask_int("输出 Tokens：")
        self.records.append({
            "日期": str(date.today()),
            "模型": name,
            "输入": comein,
            "输出": comeback,
        })
        self.save()            # 一记完就落盘
        print(f"已记一笔，当前共 {len(self.records)} 笔")

    # ---------- 功能 2：看全部 ----------
    def show_all(self):
        if not self.records:
            print("还没有记录")
            return
        for i, r in enumerate(self.records, 1):
            print(f'{i}. {r["日期"]}  {r["模型"]}  输入 {r["输入"]}  输出 {r["输出"]}')

    # ---------- 功能 3：按日期汇总 ----------
    def summary(self):
        if not self.records:
            print("还没有记录")
            return
        total = {}             # {日期: {"输入": 合计, "输出": 合计}}
        for r in self.records:
            d = r["日期"]
            if d not in total:
                total[d] = {"输入": 0, "输出": 0}
            total[d]["输入"] += r["输入"]
            total[d]["输出"] += r["输出"]

        print("按日期汇总：")
        for d, s in total.items():     # items() 一次拿键和值
            print(f'{d}  输入 {s["输入"]}  输出 {s["输出"]}  合计 {s["输入"] + s["输出"]}')


def main():
    zhang = Jizhang()
    while True:
        print("\n1 = 记一笔  2 = 看全部  3 = 按日期汇总  0 = 退出")
        x = input("请选择：").strip()
        if x == "1":
            zhang.add()
        elif x == "2":
            zhang.show_all()
        elif x == "3":
            zhang.summary()
        elif x == "0":
            print("已存档，再见。")
            break
        else:
            print("没有这个选项")


if __name__ == "__main__":
    main()
