# L06 · 字典 dict（键值对：给数据起"名字"）

> 本课目标：学会 dict——用"钥匙(键)"直接取"东西(值)"；这是 agent 项目（JSON、配置、工具参数、频次统计）的地基。
> 验收：洛谷 **P1598 垂直柱状图** AC + 通讯录小作业。
> 机制4：本课起每课开头 🔴🟡🟢 前置清单；作业带卡点记录。

## 🔴🟡🟢 前置清单（开课前口头确认）
- 🔴 list 的下标与遍历（`[0]`、`for x in list`）｜🔴 tuple 打包/解包（`a, b = ...`）
- 🔴 `input().split()` + `map(int, ...)`｜🟡 set 的 `in` 成员判断｜🟢 JSON 长什么样（不懂正常，只用直觉）
> 哪项含糊先说，先补再往下。

## 1. 为什么要字典

list 擅长"一串按顺序"，不擅长"按名字找"。成绩场景：
- list：你得记"第几个是张三"（下标不人话）
- **dict：用"名字"（键）直接取"成绩"（值），像查字典**

```python
scores = {"张三": 92, "李四": 88, "王五": 95}
print(scores["张三"])      # 92
```

## 2. 基本操作

```python
scores = {"张三": 92, "李四": 88}
scores["王五"] = 95        # 键不存在 = 新增
scores["张三"] = 90        # 键已存在 = 覆盖
print(scores.get("赵六"))  # None：.get 查询，键不存在不报错
# scores["赵六"]           # ❌ KeyError：直接 [] 取不存在的键会炸
print("张三" in scores)    # True：键在不在
del scores["李四"]         # 删除
len(scores)                # 键值对个数
```

遍历：
```python
for name in scores:                 # 遍历键
    print(name)
for name, score in scores.items():  # 键值一起
    print(name, score)
```

## 3. 嵌套：dict 套 dict/list（真实数据常态）

```python
roster = {
    "张3": {"gender": "男", "hours": 2},
    "李4": {"gender": "女", "hours": 1},
}
print(roster["张3"]["hours"])       # 2
```

> agent 参数、工具返回、配置文件——全是"字典套字典/列表"。**dict 结构 = Python 眼中的 JSON**。

## 4. 经典计数套路（P1598 就靠它）

```python
freq = {}
for ch in line:                # 逐字符
    freq[ch] = freq.get(ch, 0) + 1   # 出现过就 +1，没见过按 0 起
```

一行读四个：四行都用 `for _ in range(4): line = input()`。

## ⚠️ 最易错 4 条

1. `{}` 是空 **dict**，不是空 set（空 set 写 `set()`）
2. `dict[不存在的键]` → **KeyError**；安全查询用 `.get(键)` 或先 `in`
3. 键必须"可哈希"：str/int/tuple 可以；**list/set/dict 不能当键**
4. 遍历 dict 默认拿到**键**，不是值（要值用 `.values()` 或 `.items()`）

## 📋 今日验收

1. **洛谷 P1598 垂直柱状图**（已实测题面）：输入 4 行大写字母 → 统计 A–Z 频次 → 画竖条图。
   提示：① dict 计数套路；② 只需要出现过的 A–Z 且按字母序输出；③ **每行末尾不许有空格**——拼好每行后 `.rstrip()` 再去尾。
2. **通讯录**（新建 `my_day6.py`）：循环录入 3 次"姓名 电话"（空格分隔）存 dict → 输入一个姓名打印电话；查不到打印"查无此人"。提示：`name, phone = input().split()`；`.get(name, "查无此人")`。
3. 睡前 3 行笔记（含卡点记录）

## 🎤 费曼检验 #6（作业后回答，禁术语）

**12 岁版**：list 是"排队名单"（第几个是谁），dict 是"点名册"（每页贴名字、下面记信息）——点名册不用从头翻到尾，**按名字直接翻**。

三问：① dict 和 list 的最大区别（生活比喻）？② 为什么 `dict[不存在的键]` 会报错、`.get()` 不会？③ 什么东西能当"键"（名字/编号这类 vs 会变的清单）？
