import asyncio
#监听器

async def show_tool_event(event):
    if event["type"] == "tool_start":
        print(f"准备执行工具:{event["tool_call_id"]}")

    if event["type"] == "tool_end":
        if event["status"] == "success":
            print(f"工具执行成功{event["tool_call_id"]}")

        if event["status"] == "timeout":
            print(f"工具等待超时{event["tool_call_id"]}")

        if event["status"] == "error":
            print(f"工具执行失败{event["tool_call_id"]}")

        if event["status"] == "cancelled":
            print(f"工具等待取消{event["tool_call_id"]}")

listeners = [show_tool_event]

async def emit(event):
    for listener in listeners:
        try:
            await listener(event)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"监听器处理失败：{type(error).__name__}: {error}")