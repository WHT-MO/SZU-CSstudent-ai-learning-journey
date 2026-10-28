import httpx
import json
import asyncio
import re

async def request_agent(prompt: str, session_id: str = "default") -> dict | None:
    request_body = {
        "prompt": prompt,
        "session_id": session_id,
        }
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            method="POST",
            url="http://127.0.0.1:8000/chat",
            headers=headers,
            json=request_body,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue

                event = json.loads(line[5:].strip())

                if event["type"] == "text_delta":
                    print(f"{event["text"]}", end="", flush=True)

                elif event["type"] == "agent_done":
                    print()
                    if event["result"] is None:
                        print("任务结束，未取得完整回答")
                        return 
                    
                    return event["result"]
            
                elif event["type"] == "agent_error":
                    print(f"{event["message"]}")
                    return None

                elif event["type"] == "tool_start":
                    print(f"准备调用工具：{event["tool_call_id"]}")

                elif event["type"] == "tool_end":
                    print(f"工具状态：{event["tool_call_id"]} {event["status"]}")

async def run_request(prompt, session_id):
    try:
        await request_agent(prompt, session_id)

    except httpx.HTTPError as error:
        print(f"请求服务失败：{error}")

    except Exception as error:
        print(f"请求错误{error}")

    except asyncio.CancelledError:
        raise

async def cancel_request(task) -> bool:
    try:
        if task is None or task.done() == True:
            return False
    
        else:
            task.cancel()
            await task

    except asyncio.CancelledError:
        pass

    return True

async def main():
    request_task = None
    current_session_id = "default"

    while True:
        prompt = (await asyncio.to_thread( #让输入不阻塞请求
            input, f"[{current_session_id}]请输入任务："
            )).strip() 
        command, separator, argument = prompt.partition(" ")

        if prompt == "/exit":
            break

        elif not prompt:
            continue

        elif command == "/session":
            if not argument:
                print(f"当前会话为{current_session_id}")
            else:
                argument = argument.strip()
                match = re.fullmatch(r"[A-Za-z0-9_-]+", argument)

                if match is None:
                    print("会话名不符合规则")
                else:
                    current_session_id = argument

        elif prompt == "/stop":
            stopped = await cancel_request(request_task)
            if stopped is True:
                print("已停止")
            elif stopped is False:
                print("当前没有运行请求")
            request_task = None

        else:
            if request_task is None or request_task.done() == True:
                request_task = asyncio.create_task(
                    run_request(prompt, current_session_id)
                )
            else:
                print("请先/stop停止当前任务")
                continue

if __name__ == "__main__":
    asyncio.run(main())