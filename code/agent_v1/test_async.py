import asyncio
import time

async def say_hi():
    print("start")
    await asyncio.sleep(1)
    print("hello")

async def main():
    await asyncio.gather(say_hi(),say_hi())

async def main2():
    await say_hi()
    await say_hi()

if __name__ == "__main__":
    start = time.perf_counter()
    asyncio.run(main())
    end = time.perf_counter()
    print(f"并发耗时{end - start}秒")
    start = time.perf_counter()
    asyncio.run(main2())
    end = time.perf_counter()
    print(f"串行耗时{end - start}秒")
