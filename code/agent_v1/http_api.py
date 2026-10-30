from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

from agent_runner import run_agent
from agent_events import listeners
from tool_policies import read_only_guard

class ChatRequest(BaseModel):
    prompt: str
    session_id: str = "default"
    read_only: bool = False

class SteerRequest(BaseModel):
    text: str
    session_id: str = "default"

app = FastAPI() #创建Web应用实例
agent_lock = asyncio.Lock() #全局锁
steering_queues = {} #队列登记

@app.post("/chat") #注册API接口
async def chat(data: ChatRequest): #接收API请求
    queue = asyncio.Queue()
    prompt = data.prompt
    session_id = data.session_id
    read_only = data.read_only

    task = asyncio.create_task(
        run_agent_to_queue(
            prompt,
            queue,
            session_id,
            read_only,
        )
    )

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

async def run_agent_to_queue( #事件放入队列
        prompt,
        queue,
        session_id: str = "default",
        read_only: bool = False,
    ): 
    before_tool = None
    if read_only:
        before_tool = read_only_guard

    listener = queue.put
    async with agent_lock:
        listeners.append(listener)
        steering_queue = asyncio.Queue()
        steering_queues[session_id] = steering_queue

        try:
            result = await run_agent(
                prompt,
                session_id=session_id,
                before_tool=before_tool,
                steering_queue=steering_queue,
            )
            await queue.put({
                "type": "agent_done",
                "result": result,
            })

        except Exception as error:
            await queue.put({
                "type": "agent_error",
                "message": str(error)
            })

        finally: #移除队列登记，清理监听器、通知发送端结束
            steering_queues.pop(session_id, None)
            listeners.remove(listener)
            await queue.put(None)

@app.post("/steer") 
async def steer(data: SteerRequest): #补充会话
    steer_result = { #返回响应字段
        "accepted": False,
        "reason": None,
    }

    text = data.text.strip()
    if not text:
        steer_result["reason"] = "补充指令不能为空"
        return steer_result

    steering_queue = steering_queues.get(data.session_id)
    if steering_queue is None:
        steer_result["reason"] = "当前会话没有运行任务"
        return steer_result

    steering_queue.put_nowait(text)
    steer_result["accepted"] = True
    return steer_result