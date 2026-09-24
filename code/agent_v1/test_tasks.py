import asyncio
import gc

# W1 第 2 格：对比任务异常的处理，再观察 Future 与任务引用。
def ends(finished_task):
    # 完成回调会收到那个 Task；读取 exception() 才拿到失败原因。
    error = finished_task.exception()
    background_tasks.discard(finished_task)  # 任务已结束，从强引用集合移走
    print(error)
    print(len(background_tasks))

async def say_hi():
    print("start")
    await asyncio.sleep(1)
    raise ValueError("模拟任务失败")  # 故意失败，用来观察异常走向
    print("hello")  # 上一行已抛异常，这行不会执行

async def main():
    task = asyncio.create_task(say_hi())  # 创建并安排任务，此时不等它完成
    print("main")
    await task  # 任务失败会把 ValueError 传到这里

async def main2():
    task = asyncio.create_task(say_hi())
    task.add_done_callback(ends)  # 完成时调用 ends(task)
    background_tasks.add(task)  # 集合保留强引用，直到回调清理
    print("main2")
    await asyncio.sleep(2)  # 让事件循环继续运行，给后台任务完成的机会

async def wait(future):
    print("waiting")
    print(await future)  # Future 未完成就暂停；完成后打印它的结果

async def wait2():
    print("waiting")
    loop = asyncio.get_running_loop()
    future = loop.create_future()  # 在任务内部创建一个尚无结果的 Future
    await future  # 没有代码给它 set_result，任务会一直等待

async def Future():
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    print(future)
    task = asyncio.create_task(wait(future))
    await asyncio.sleep(0.1)  # 给 wait 一次开始运行的机会；0.1 秒不是必须值
    future.set_result("ready")  # 填入结果，唤醒等待 future 的任务
    await task  # 等待被唤醒的任务结束

async def Future2():
    task = asyncio.create_task(wait2())
    await asyncio.sleep(0.1)  # 先让 wait2 跑到 await future
    print(task.done())  # False：任务仍在等待，并未完成
    background_tasks.add(task)  # 集合留下强引用
    del task  # 删除局部变量；集合仍持有原 Task
    print("before gc")
    gc.collect()  # 此时任务仍在集合里，不因失去所有强引用而销毁
    print("before release")
    background_tasks.clear()  # 释放集合持有的引用
    gc.collect()  # 本机实验曾出现 pending Task 被销毁的警告；并非每次必然
    print(background_tasks)
    print("after release")

background_tasks = set()  # 后台任务注册表：保存尚需关注的 Task

if __name__ == "__main__":
    asyncio.run(Future2())  # 当前入口运行 GC 对照；其他函数保留作独立实验
