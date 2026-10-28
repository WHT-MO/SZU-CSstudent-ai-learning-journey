from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

from agent_runner import run_agent
from agent_events import listeners

class ChatRequest(BaseModel):
    prompt: str
    session_id: str = "default"

app = FastAPI() #创建Web应用实例
agent_lock = asyncio.Lock() #全局锁

@app.post("/chat") #注册API接口
async def chat(data: ChatRequest): #接收API请求
    queue = asyncio.Queue()
    prompt = data.prompt
    session_id = data.session_id

    task = asyncio.create_task(run_agent_to_queue(prompt, queue, session_id))

    return StreamingResponse(
        stream_events(queue, task),
        media_type="text/event-stream",
    )

async def stream_events(queue, task): #返回SSE事件流
    try:
        while True:
            event = await queue.get()
            if event is None:
                return
            data = json.dumps(event, ensure_ascii=False)
            yield f"data: {data}\n\n"

    finally:
        if not task.done(): #请求停止未结束函数
            task.cancel()

        try: #等待退出，释放锁
            await task 
        except asyncio.CancelledError: #因取消退出
            pass


async def run_agent_to_queue(prompt, queue, session_id: str = "default"): #事件放入队列
    listener = queue.put
    async with agent_lock:
        listeners.append(listener)

        try:
            result = await run_agent(prompt, session_id=session_id)
            await queue.put({
                "type": "agent_done",
                "result": result,
            })

        except Exception as error:
            await queue.put({
                "type": "agent_error",
                "message": str(error)
            })

        finally: #清理监听器、通知发送端结束
            listeners.remove(listener)
            await queue.put(None)