import asyncio
from contextvars import ContextVar

#监听器
event_source = ContextVar("event_source", default="main") #标记并发任务
listeners = []

async def emit(event):
    sub_event = event.copy()
    sub_event["source"] = event_source.get()
    for listener in listeners:
        try:
            await listener(sub_event)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"监听器处理失败：{type(error).__name__}: {error}")