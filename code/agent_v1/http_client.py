import httpx
import json
import asyncio
import re

async def request_agent(
        prompt: str,
        session_id: str = "default",
        read_only: bool = False,
    ) -> dict | None:
    
    request_body = {
        "prompt": prompt,
        "session_id": session_id,
        "read_only": read_only,
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
                    agent_result = event["result"]

                    if agent_result["completed"] == False:
                        print(f"任务结束原因：{agent_result["reason"]}")
                        return agent_result
                    
                    return agent_result
            
                elif event["type"] == "agent_error":
                    print(f"{event["message"]}")
                    return None

                elif event["type"] == "tool_start":
                    print(f"准备调用工具：{event["tool_call_id"]}")

                elif event["type"] == "tool_end":
                    print(f"工具状态：{event["tool_call_id"]} {event["status"]}")

async def run_request(
        prompt,
        session_id,
        read_only=False,
    ):
    try:
        await request_agent(
            prompt,
            session_id,
            read_only=read_only,
        )

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

async def request_steer(text, session_id):
    request_body = {
        "text": text,
        "session_id": session_id,
        }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url="http://127.0.0.1:8000/steer",
            json=request_body,
        )
        response.raise_for_status()
        data = response.json()
        return data
    
async def main():
    request_task = None
    current_session_id = "default"

    read_only = False #只读
    active_session_id = None #进行中会话

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

        elif command == "/mode": #切换权限
            if not argument:
                if read_only:
                    print("当前为只读模式")
                else:
                    print("当前为标准模式")
                
            else:
                argument = argument.strip()

                if argument == "readonly":
                    print("已切换为只读模式")
                    read_only = True

                elif argument == "normal":
                    print("已切换为标准模式")
                    read_only = False

                else:
                    print("仅支持只读/mode readonly和标准/mode normal")

        elif command == "/steer": #插入会话
            if not argument:
                print("请输入补充任务")

            else:
                argument = argument.strip()

                if request_task is None or request_task.done() == True:
                    print("当前没有任务运行")

                else:
                    try:
                        steer_result = await request_steer(argument, active_session_id)
                        if steer_result["accepted"] == True:
                            print("已排队")
                        else:
                            print(f"{steer_result["reason"]}")

                    except httpx.HTTPError as error:
                        print(f"补充请求失败{error}")         

        else:
            if request_task is None or request_task.done() == True:
                active_session_id = current_session_id
                request_task = asyncio.create_task(
                    run_request(prompt, active_session_id, read_only)
                )
            else:
                print("请先/stop停止当前任务")
                continue

if __name__ == "__main__":
    asyncio.run(main())