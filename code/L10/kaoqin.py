# ============================================================
# 军训打卡小程序 · 文件存档版（学员版，2026-09-14 完成 · L10 异常处理 + 文件读写）
# 由 code\L08\kaoqin.py 升级而来：L08 版关掉程序数据就没了，本版把状态落盘。
#
# 交互：启动读存档 → 输入"今天是第几天" → 菜单（1 打卡 / 2 查记录 / 3 清空存档 / 0 退出）
#       → 每轮结束写存档 → "继续请按0"（0 = 继续换天，其他键退出）
# 存档：同目录下 打卡状态.txt，内容一行两个整数 "last d"
#       last = 上次打卡第几天（哨兵 0 = 从未打卡）；d = 连续打卡天数
#
# 核心决策（学员自产）：
#   ① 读档 = 把 f.read() 的整串文本 split → map(int) → 解包成 last, d
#      （和 L04 的输入模板同一套动作，只是数据来源从键盘换成文件）。
#   ② 写档用 "w"（清空重写）：存档存的是【当前状态快照】，不是流水账；要记历史才用 "a"。
#   ③ 文件不存在 = 新用户：try/except 只抓 FileNotFoundError，不写裸 except。
#   ④ 清空存档 = 状态归零：内存 last/d 置 0 并写入 "0 0"；不是删文件、更不是写空文件
#      （空文件下次读会崩）。破坏性操作带二次确认（1 确定 / 0 取消）。
#
# 卡点记录（L10 当天真撞过的）：
#   ① open(路径, "w") 会【先把文件清零】：两次 "w" 各写一行，只剩后写的；追加要用 "a"。
#   ② 相对路径跟的是 cwd（敲命令时所在目录），不是脚本所在目录 —— 换个目录跑，
#      存档就落在那个目录里。
#   ③ 编码：gbk 字节按 utf-8 读就是乱码；读写两端都要显式 encoding="utf-8"。
#   ④ 清空写成 f.write("") → 下次启动 ValueError: not enough values to unpack；
#      只清文件不改内存时，退出前外层写档会把旧值写回去 → 清空等于没做
#      （L08"读操作顺手改状态"的反面：状态在内存/文件两处，必须一起改）。
#
# 已知取舍（学员 2026-09-14 决定，非缺陷）：
#   ① 新用户不询问"今天是第几天"，默认 today = 1。代价：不在第 1 天开始用时，
#      启动当天被记成第 1 天，连续天数从 1 重算。
#   ② 清空后直接退出菜单（回到"继续请按0"），不再回菜单 —— 学员 2026-09-14 确认是有意设计。
#   ③ 清空后启动显示"上次打卡第0天，已连续打卡0天"（哨兵 0 直接显示出来）。
#
# 验收（2026-09-14 教员实跑）：新用户打卡→查记录→退出 = 存档 [1 1]；
#   重启按 3 清空 = [0 0]；清空后重启第 2 天打卡 = [2 1]；清空按 0 取消 = 存档不变。
# 用法（存档落在 cwd，所以在本文件所在目录运行）：
#   cd D:\code\dsh\python-course\code\L10
#   python kaoqin.py
# ============================================================

#学习打卡
def daka(last,d):#菜单
    while True:
        x = int(input("1 = 打卡，2 = 查记录，3 = 清空存档，0 = 退出："))
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
        elif x == 3:
            daka_choose = 1
            while daka_choose != 0:
                daka_choose = int(input("你确定吗？(1 = 确定，0 = 取消)："))
                if daka_choose == 0:
                    break
                elif daka_choose == 1:
                    with open("打卡状态.txt","w",encoding="utf-8") as f:
                        last = 0
                        d = 0
                        f.write("0 0")
                    print("已清空")
                    break
            break
        elif x == 0:
            print("感谢使用。")
            break
    return last,d
def check(today):#检查日期
    while last > today or today == 0:
        print("你确定没记错？")
        today = int(input("今天是第几天："))
    return today

t = 0
while t == 0:
    try:#读取本地存档
        with open("打卡状态.txt","r",encoding="utf-8") as f:
            last,d = map(int,(f.read().split()))
            print(f"上次打卡第{last}天，已连续打卡{d}天")
            today = int(input("今天是第几天："))
    except FileNotFoundError:
        print("还没有存档，这是第一次运行")
        d = 0
        last = 0
        today = 1
    today = check(today)
    #特例筛查
    if last == today - 1 and d == 0 and last != 0:
        d = 1
    elif last == today and d == 0:
        d = 1
    elif last < today - 1 and d != 0:
        d = 0
    last,d = daka(last,d)
    with open("打卡状态.txt","w",encoding="utf-8") as f:
        f.write(f"{last} {d}")
    t = int(input("继续请按0："))
    if t == 0:
        print(f"上次打卡第{last}天，欢迎继续使用。")
    else:
        break
