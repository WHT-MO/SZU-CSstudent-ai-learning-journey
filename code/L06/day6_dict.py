# ============================================================
# L06 示例代码 —— 字典 dict（作业请新建 my_day6.py）
# 运行：python day6_dict.py
# ============================================================

# ---- ① 建字典 + 取/改/增 ----
scores = {"张三": 92, "李四": 88}
print(scores["张三"])        # 92 按键取值
scores["王五"] = 95          # 新增
scores["张三"] = 90          # 覆盖
print(scores)                # {'张三': 90, '李四': 88, '王五': 95}

# 安全查询：.get / in
print(scores.get("赵六"))    # None（不报错）
print(scores.get("赵六", "查无此人"))  # 给默认值
print("张三" in scores)      # True

# ---- ② 遍历 ----
for name in scores:
    print("键：", name)
for name, score in scores.items():
    print(f"{name}: {score}")

# ---- ③ 嵌套：dict 套 dict ----
roster = {
    "张3": {"gender": "男", "hours": 2},
    "李4": {"gender": "女", "hours": 1},
}
print(roster["张3"]["hours"])   # 2

# ---- ④ 经典计数套路（P1598 的核心） ----
line = "HELLO"
freq = {}
for ch in line:
    freq[ch] = freq.get(ch, 0) + 1
print(freq)                     # {'H':1,'E':1,'L':2,'O':1}


# ============================================================
# 📋 作业：新建 my_day6.py
#
# 1. 洛谷 P1598 垂直柱状图 → AC
#    （读 4 行大写字母 → dict 计数 → 按 A-Z 输出竖条；
#      每行末尾不许有空格，拼完用 .rstrip()）
#
# 2. 通讯录：循环 3 次输入"姓名 电话"（空格分隔）存入 dict，
#    再输入一个姓名 → 打印电话；查不到打印"查无此人"
#    （name, phone = input().split()；.get(name, "查无此人")）
#
# 3. 睡前 3 行笔记（含卡点记录：卡在哪/试了多久）。
# ============================================================
