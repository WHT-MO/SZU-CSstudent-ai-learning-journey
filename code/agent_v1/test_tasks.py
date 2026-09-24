import asyncio
import gc

def ends(finished_task):
    error = finished_task.exception()
    background_tasks.discard(finished_task)
    print(error)
    print(len(background_tasks))

async def say_hi():
    print("start")
    await asyncio.sleep(1)
    raise ValueError("模拟任务失败")
    print("hello")

async def main():
    task = asyncio.create_task(say_hi())
    print("main")
    await task

async def main2():
    task = asyncio.create_task(say_hi())
    task.add_done_callback(ends)
    background_tasks.add(task)
    print("main2")
    await asyncio.sleep(2)

async def wait(future):
    print("waiting")
    print(await future)

async def wait2():
    print("waiting")
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    await future

async def Future():
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    print(future)
    task = asyncio.create_task(wait(future))
    await asyncio.sleep(0.1)
    future.set_result("ready")
    await task

async def Future2():
    task = asyncio.create_task(wait2())
    await asyncio.sleep(0.1)
    print(task.done())
    background_tasks.add(task)
    del task
    print("before gc")
    gc.collect()
    print("before release")
    background_tasks.clear()
    gc.collect()
    print(background_tasks)
    print("after release")

background_tasks = set()

if __name__ == "__main__":
    asyncio.run(Future2())