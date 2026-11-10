import asyncio
from contextvars import ContextVar

#监听器
event_source = ContextVar("event_source", default="main") #标记并发任务
task_listener = ContextVar("task_listener", default=None) #单独会话监听
listeners = []

async def emit(event):
    sub_event = event.copy()
    sub_event["source"] = event_source.get()

    active_listeners = listeners.copy()
    current_listener = task_listener.get()
    if current_listener is not None:
        active_listeners.append(current_listener)

    for listener in active_listeners:
        try:
            await listener(sub_event)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"监听器处理失败：{type(error).__name__}: {error}")