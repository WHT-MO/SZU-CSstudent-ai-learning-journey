import asyncio
import time

# W1 第 1 格：用“等待 1 秒”模拟 I/O，比较串行与并发的耗时。
async def say_hi():
    print("start")
    await asyncio.sleep(1)  # 当前协程暂停；事件循环可以运行别的任务
    print("hello")

async def main():
    # 同时安排两个协程；两段等待可以重叠。
    await asyncio.gather(say_hi(),say_hi())

async def main2():
    # 第一个完成后才开始等第二个，所以两段等待相加。
    await say_hi()
    await say_hi()

if __name__ == "__main__":
    # 两组都只启动一次事件循环，避免“启动次数不同”干扰对照。
    start = time.perf_counter()
    asyncio.run(main())
    end = time.perf_counter()
    print(f"并发耗时{end - start}秒")

    start = time.perf_counter()
    asyncio.run(main2())
    end = time.perf_counter()
    print(f"串行耗时{end - start}秒")
