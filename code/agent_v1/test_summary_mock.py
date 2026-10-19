import asyncio
import httpx

import os
from agent_runner import summarize_messages

os.environ["DEEPSEEK_API_KEY"] = "test-key"

#请求重试测试

async def fake_response(request):
    request_count["value"] += 1
    print("假接口收到请求")
    return httpx.Response(429)

async def fake_response_then_success(request):
    request_count["value"] += 1
    if request_count["value"] == 1:
        print("假接口收到请求")
        return httpx.Response(429)
    
    return httpx.Response(
        200,
        json=
        {
            "choices": 
            [
                {
                    "message":
                    {
                        "role": "assistant",
                        "content": "摘要测试成功",
                    },
                },
            ],
        },
    )

async def fake_response_unauthorized(request):
    request_count["value"] += 1
    return httpx.Response(401)

async def fake_response_cancelled(request):
    request_count["value"] += 1
    raise asyncio.CancelledError

async def check_cancellation():
    request_count["value"] = 0
    transport = httpx.MockTransport(fake_response_cancelled)
    cancelled = False
    try:
        async with httpx.AsyncClient(transport=transport) as client:
            message = await summarize_messages(
                client,
                messages=[
                    {
                        "role": "user",
                        "content": content,
                    },
                ],
            )
    except asyncio.CancelledError:
        cancelled = True

    assert cancelled is True
    assert request_count["value"] == 1

    print("取消传递成功")

async def abc(response, expected_message, expected_count):
    request_count["value"] = 0
    transport = httpx.MockTransport(response)

    async with httpx.AsyncClient(transport=transport) as client:
        message = await summarize_messages(
            client,
            messages=[
                {
                    "role": "user",
                    "content": content,
                },
            ],
        )

        assert message == expected_message
        assert request_count["value"] == expected_count

        print(message)

async def main():
    await abc(fake_response, None, 3)
    await abc(fake_response_then_success, "摘要测试成功", 2)
    await abc(fake_response_unauthorized, None, 1)
    await check_cancellation()

request_count = {"value": 0}

if __name__ == "__main__":
    content = "普通用户信息"
    asyncio.run(main())