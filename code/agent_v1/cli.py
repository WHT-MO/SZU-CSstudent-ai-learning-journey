import asyncio
import time
from contextlib import redirect_stdout
from collections import deque

from terminal_ui import build_terminal_ui, TerminalWriter
from agent_runner import run_agent
from session_store import clear_session
from agent_events import listeners
from session_store import get_session_path
from tool_policies import read_only_guard, READ_ONLY_TOOL_NAMES
from run_records import append_run_record

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
    if event["type"] == "text_delta" and event.get("source", "main") == "main":
        print(event["text"], end="", flush=True)

    if event["type"] == "model_response_end":
        print()   
        if event["usage"]:
            print("输入：",event["usage"]["prompt_tokens"])
            print("输出：",event["usage"]["completion_tokens"])
            print("合计：",event["usage"]["total_tokens"])

async def run_cli_task(prompt, session_id, read_only, steering_queue): #启动助手
    started_at = time.perf_counter()
    before_tool = None
    visible_tool_names = None

    if read_only:
        before_tool = read_only_guard
        visible_tool_names = READ_ONLY_TOOL_NAMES

    usage_totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "reports": 0,
    }

    async def collect_usage(event): #tokens用量计总
        if event["type"] != "model_response_end":
            return
        
        usage = event["usage"]
        if usage is None:
            return

        usage_totals["prompt_tokens"] += usage["prompt_tokens"]
        usage_totals["completion_tokens"] += usage["completion_tokens"]
        usage_totals["total_tokens"] += usage["total_tokens"]
        usage_totals["reports"] += 1

    listeners.append(collect_usage)

    status = "running" #记录运行状态
    reason = None

    try:
        agent_result = await run_agent(
            prompt,
            session_id=session_id,
            before_tool=before_tool,
            steering_queue=steering_queue,
            visible_tool_names=visible_tool_names,
        )

        if agent_result["completed"] == False:
            status = "incomplete"
            reason = agent_result["reason"]
            print(agent_result["reason"])
        else:
            status = "completed"
            reason = agent_result["reason"]

    except Exception as error:
        status = "error"
        reason = str(error)
        print(f"请求错误{error}")

    except asyncio.CancelledError:
        status = "cancelled"
        reason = "任务已取消"
        raise

    finally:
        elapsed_seconds = time.perf_counter() - started_at
        print(f"任务耗时：{elapsed_seconds:.2f} 秒")

        listeners.remove(collect_usage)
        if usage_totals["reports"] == 0:
            print("本次任务未收到用量统计")
        else:
            print("任务已报告用量统计")
            print(f"输入：{usage_totals['prompt_tokens']} \n输出：{usage_totals['completion_tokens']} \n合计：{usage_totals['total_tokens']}")

        record = { #保存运行记录
            "session_id": session_id,
            "status": status,
            "reason": reason,
            "elapsed_seconds": elapsed_seconds,
            "usage_totals": usage_totals,
        }
        append_run_record(record)

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
    current_session_id = "default" #默认会话

    command_events = asyncio.Queue() #输入区

    def get_prompt(): #输入提示
        return f"[{current_session_id}]请输入任务："

    app, output_area = build_terminal_ui(command_events, get_prompt)
    writer = TerminalWriter(output_area) #流式追加实例

    async def command_loop():
        nonlocal current_session_id
        agent_task = None #运行状态判断
        read_only = False #只读开关
        steering_queue = None #运行队列
        pending_requests = deque() #待执行队列

        def start_next_request(): #启动任务
            nonlocal agent_task, steering_queue
            if agent_task is not None or not pending_requests:
                return
            
            queued_prompt, queued_session_id, queued_read_only = pending_requests.popleft() #取出队首
            steering_queue = asyncio.Queue()
            agent_task = app.create_background_task( #创建任务
                run_cli_task(queued_prompt, queued_session_id, queued_read_only, steering_queue)
            )
            agent_task.add_done_callback(command_events.put_nowait) #任务结束信号

        while True: 
            item = await command_events.get()
            if isinstance(item, asyncio.Task): #队列结束处理
                if item is agent_task:
                    agent_task = None
                    steering_queue = None
                    start_next_request()
                continue

            user_prompt = item.strip()

            if user_prompt:
                print (f"{get_prompt()}{user_prompt}") #命令输出显示

            command, separator, argument = user_prompt.partition(" ")

            if user_prompt == "/reset": #清除对话
                if agent_task is None or agent_task.done() == True:
                    clear_session(session_id=current_session_id)
                else:
                    print("请先/stop停止当前任务")
                    continue

            elif user_prompt == "/exit": #退出
                await cancel_request(agent_task) #先停任务
                app.exit() #关后台运行
                return

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
                        app.invalidate() #刷新输入提示
                    except ValueError:
                        print("会话名不符合规则")
                        continue

            elif user_prompt == "/stop":
                stopped = await cancel_request(agent_task)
                if stopped is True:
                    print("已停止")
                elif stopped is False:
                    print("当前没有运行请求")

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

            elif command == "/queue": #追加任务
                if not argument:
                    print("请输入待办任务")

                else:
                    argument = argument.strip()

                    pending_requests.append((argument, current_session_id, read_only))
                    start_next_request()

            else:
                if agent_task is None or agent_task.done() == True:
                    pending_requests.append((user_prompt, current_session_id, read_only))
                    start_next_request()

                else:
                    print("请先/stop停止当前任务")
                    continue

    def start_command_loop():
        app.create_background_task(command_loop())

    with redirect_stdout(writer):
        await app.run_async(pre_run=start_command_loop) #页面启动时调用


if __name__ == "__main__":
    asyncio.run(main())