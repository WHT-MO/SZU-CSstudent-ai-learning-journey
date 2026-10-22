import asyncio
#监听器

listeners = []

async def emit(event):
    for listener in listeners:
        try:
            await listener(event)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"监听器处理失败：{type(error).__name__}: {error}")