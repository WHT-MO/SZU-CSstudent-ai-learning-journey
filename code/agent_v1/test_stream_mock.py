import asyncio
import httpx

import os
from model_client import stream_message

os.environ["DEEPSEEK_API_KEY"] = "test-key"

#测试流式请求响应失败的返回
async def fake_server_tool_compele(request):
    return httpx.Response(
        500,
        headers={"content-type": "text/event-stream"},
        content=(
            'data: {"choices":[{"delta":{"tool_calls":['
            '{"index":0,"id":"call_1","type":"function",'
            '"function":{"name":"read_file",'
            '"arguments":"{\\"path\\":\\"a.txt\\"}"}}'
            ']}}]}\n\n'
            'data: [DONE]\n\n'
        ).encode("utf-8")
    )

async def abc():
    transport = httpx.MockTransport(fake_server_tool_compele)

    async with httpx.AsyncClient(transport=transport) as client:
        message, completed = await stream_message(
            client,
            messages=[],
            tools=[],
        )

        assert message is None
        assert completed is False

        print(message)
        print(completed)

if __name__ == "__main__":
    asyncio.run(abc())