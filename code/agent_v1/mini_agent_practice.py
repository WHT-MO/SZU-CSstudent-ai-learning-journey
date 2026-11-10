import asyncio
import json

def get_note(topic):
    if topic == "loop":
        return {
            "role": "tool",
            "content": "模型请求工具，收到结果后继续",
        }
    elif topic == "async":
        return {
            "role": "tool",
            "content": "await 等待异步结果",
        }

    else:
        return {
            "role": "tool",
            "content": "无响应",
        }
        
async def fake_model(messages):
    if messages[-1]["role"] == "user":
        reply = {
            "role": "assistant",
            "session_id": "reply_1",
            "content": "",
            "tool_calls": [
                {
                    "id": "note_1",
                    "type": "function",
                    "function": {
                        "name": "get_note",
                        "arguments": '{"topic":}',
                    },
                },
                {
                    "id": "note_2",
                    "type": "function",
                    "function": {
                        "name": "get_note",
                        "arguments": '{"topic": "async"}',
                    },
                },
            ],
        }
        return reply

    if messages[-1]["role"] == "tool":
        reply = {
            "role": "assistant",
            "sessoon_id": "reply_2",
            "content": f"工具结果输出完毕:{[message["content"] for message in messages[-2:]]}",
        }
        return reply

async def run_loop():
    while True:
        message = await fake_model(messages)
        messages.append(message)

        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                try:
                    argument = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    result = {
                        "role": "tool",
                        "content": "参数 JSON 格式错误"
                    }
                else:
                    result = get_note(argument["topic"])
                    
                result["tool_call_id"] = tool_call["id"]
                messages.append(result)

        else:
            print(message["content"])
            break

if __name__ == "__main__":
    messages = [
        {
            "role": "user",
            "content": "",
        },
    ]
    asyncio.run(run_loop())