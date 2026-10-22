import asyncio
from agent_runner import run_agent
from session_store import clear_session
from agent_events import listeners

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


async def main():
    listeners.extend([show_tool_event, show_model_event])

    while True:
        user_prompt = input("请输入任务：").strip()
        if user_prompt == "/reset":
            clear_session()
        elif user_prompt == "/exit":
            break
        elif not user_prompt:
            continue
        else:
            await run_agent(user_prompt)

if __name__ == "__main__":
    asyncio.run(main())