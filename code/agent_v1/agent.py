import asyncio

# W1 第 3 格：一次事件先改 state，再按顺序通知监听器。
# 两个监听器内部虽没有等待操作，仍写成 async def，供 emit 统一 await 调用。
async def show_state(current_state):
    # 数消息列表中的元素；len(current_state) 数的是字典的键。
    print(len(current_state["messages"]))
    print(current_state)

async def record_state(current_state):
    # 记录“此刻的消息数”这个整数快照，不保存会继续变化的字典引用。
    event_log.append(len(current_state["messages"]))

async def emit(message):
    state["messages"].append(message)  # 先更新状态
    for listener in listeners:
        await listener(state)  # 再按列表顺序通知；反过来会让记录滞后一轮

async def task():
    # 两次发事件：第一轮日志为 [1]，第二轮为 [1, 2]。
    await emit("hello")
    print(event_log)
    await emit("two")
    print(event_log)

state = {"messages":[]}  # 一个字典键指向消息列表
event_log = []  # 保存每次通知时的消息数
listeners = [show_state,record_state]  # 存函数本身；没有 ()，此处不调用

asyncio.run(task())  # 从同步入口启动事件循环
