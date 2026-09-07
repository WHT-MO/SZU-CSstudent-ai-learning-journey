# ============================================================
# L02 作业（学员原稿，首 AC：洛谷 P5711 闰年判断 100 分）
# ============================================================

# ---------- ① 成绩等级判断器 ----------
score=int(input("输入成绩(0-100)"))
if score>=90:
    print("A")
elif score>=80:
    print("B")
elif score>=70:
    print("C")
elif score>=60:
    print("D")
else:
    print("不及格")

# ---------- ② 军训状态助手（逻辑组合 and） ----------
hours=int(input("今天训练几小时？"))
napped=input("中午午睡了吗？(y/n)")

if hours>=8 and napped=="y":
    print("满血复活，晚上照常上课")
elif hours>=8 and napped=="n":
    print("危险！晚上学完立刻睡")
else:
    print("轻松日，加练一道题")

# ---------- ③ 闰年判断（P5711：输出 1/0） ----------
year=int(input())
if (year%4==0 and year%100!=0) or (year%400==0):
    print(1)  #闰年
else:
    print(0)  #平年
