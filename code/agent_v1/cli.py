import asyncio
from agent_runner import run_agent
from session_store import clear_session
from agent_events import listeners
from session_store import get_session_path
from tool_policies import read_only_guard

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

async def show_model_event(event):
    if event["type"] == "text_delta":
        print(event["text"], end="", flush=True)

    if event["type"] == "model_response_end":
        print()   
        if event["usage"]:
            print("输入：",event["usage"]["prompt_tokens"])
            print("输出：",event["usage"]["completion_tokens"])
            print("合计：",event["usage"]["total_tokens"])

async def run_cli_task(prompt, session_id, read_only, steering_queue): #启动助手
    before_tool = None
    if read_only:
        before_tool = read_only_guard

    try:
        agent_result = await run_agent(
            prompt,
            session_id=session_id,
            before_tool=before_tool,
            steering_queue=steering_queue,
        )

        if agent_result["completed"] == False:
            print(agent_result["reason"])
 
    except Exception as error:
        print(f"请求错误{error}")

    except asyncio.CancelledError:
        raise

async def cancel_request(task) -> bool: #取消助手
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
    listeners.extend([show_tool_event, show_model_event])
    agent_task = None
    current_session_id = "default" #默认会话

    read_only = False #只读开关
    steering_queue = None

    while True:
        user_prompt = (await asyncio.to_thread( #让输入不阻塞请求
            input, f"[{current_session_id}]请输入任务："
            )).strip() 
        
        command, separator, argument = user_prompt.partition(" ") #按空格拆分

        if user_prompt == "/reset": #清除对话
            if agent_task is None or agent_task.done() == True:
                clear_session(session_id=current_session_id)
            else:
                print("请先/stop停止当前任务")
                continue

        elif user_prompt == "/exit": #退出
            break

        elif not user_prompt:
            continue

        elif command == "/session": #切换会话
            if not argument:
                print(f"当前会话为{current_session_id}")
            else:
                argument = argument.strip()

                try:
                    get_session_path(argument)
                    current_session_id = argument
                except ValueError:
                    print("会话名不符合规则")
                    continue

        elif user_prompt == "/stop":
            stopped = await cancel_request(agent_task)
            if stopped is True:
                print("已停止")
            elif stopped is False:
                print("当前没有运行请求")
            agent_task = None

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

                if agent_task is None or agent_task.done() == True:
                    print("当前没有任务运行")

                else:
                    steering_queue.put_nowait(argument)
                    print("补充指令已排队")

        else:
            if agent_task is None or agent_task.done() == True:
                steering_queue = asyncio.Queue()
                agent_task = asyncio.create_task(
                    run_cli_task(user_prompt, current_session_id, read_only, steering_queue)
                )
            else:
                print("请先/stop停止当前任务")
                continue


if __name__ == "__main__":
    asyncio.run(main())