# ============================================================
# L05 示例代码 —— 字符串方法 / tuple / set（作业请新建 my_day5.py）
# 运行：python day5_strings.py
# ============================================================

# ---- ① 字符串方法 ----
s = "  Hello, ShenZhen 2026  "
print(s.lower())        # 全小写（返回新串）
print(s.strip())        # 去首尾空白
print(s.split())        # 切成单词列表
print(s.count("e"))     # e 出现次数
print(s.replace("ShenZhen", "SZ"))  # 替换

# 不可变陷阱：不接住就白干
t = "abc"
t.upper()               # 没接住 → t 还是 abc
print(t)                # abc
t = t.upper()           # 接住才生效
print(t)                # ABC

# split 与 join 是一对相反操作
words = ["深大", "计软", "大一"]
print("-".join(words))  # 深大-计软-大一
print("".join(words))   # 深大计软大一


# ---- ② tuple：贴封条的列表 ----
point = (3, 5)          # 打包
x, y = point            # 解包
print(x, y)             # 3 5
print(point[0])         # 3（能读）
# point[0] = 9          # ❌ 取消注释会 TypeError
single = (1,)           # 单元素元组必须加逗号


# ---- ③ set：自动去重 ----
nums = [3, 1, 2, 3, 1]
s = set(nums)           # {1, 2, 3}
print(s)
print(len(s))           # 3 个不同数字
print(sorted(s))        # 排序后的列表 [1, 2, 3]

total = {"小明", "小红", "小刚", "小丽", "小强"}
arrived = {"小明", "小刚"}
missing = total - arrived
print("没到的：", "、".join(sorted(missing)))


# ============================================================
# 📋 作业：新建 my_day5.py
#
# 1. 洛谷 P5015 标题统计 → AC
#
# 2. 小作业：
#    a) 输入一行数字（空格分隔）→ 输出：不同数字有几个 + 排序去重列表
#       （len(set(nums)) / sorted(set(nums))）
#    b) 输入一句英文 → 输出：单词数 + 去首尾空白并全小写后的句子
#       （split() 数单词；strip() + lower()）
#
# 3. 睡前 3 行笔记。
# ============================================================
