import asyncio

async def fake_model(messages):
    if messages[-1]["role"] == "user":
        reply = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_note",
                        "arguments": "{}",
                    },
                },
            ],
        }
        return reply
    if messages[-1]["role"] == "tool":
        reply = {
            "role": "assistant",
            "content": f"笔记内容：{messages[-1]["content"]}",
        }
        return reply

def get_note():
    return "今天学习Agent Loop"   

async def fake_model_always_tool(messages):
    reply = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "get_note",
                    "arguments": "{}",
                },
            },
        ],
    }
    return reply

async def run_loop(call_model, max_tool_rounds=3):
    messages = [
        {
            "role": "user",
            "content": "请调用工具",
        }
    ]

    tool_rounds = 0
    while True:

        reply = await call_model(messages)
        if not reply:
            print("模型请求失败")
            return
        messages.append(reply)

        if not reply.get("tool_calls"):
            break
        if tool_rounds >= max_tool_rounds:
            print("达到最大轮数")
            return

        messages.append(
            {
                "role": "tool",
                "tool_call_id": reply["tool_calls"][0]["id"],
                "content": get_note(),
            },
        )
        tool_rounds += 1

    print(reply["content"])

async def fake_model_failed(messages):
    return None

async def main():
    await run_loop(fake_model)
    await run_loop(fake_model_always_tool)
    await run_loop(fake_model_failed)

if __name__ == "__main__":
    asyncio.run(main())