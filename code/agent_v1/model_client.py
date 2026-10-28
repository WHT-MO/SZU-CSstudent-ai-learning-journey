import json
import os
import httpx
import asyncio

from dotenv import load_dotenv
from agent_events import emit

URL = "https://api.deepseek.com/chat/completions"
load_dotenv() #读取API_key

MAX_OUTPUT_TOKENS = 20000

#非流式响应结构边界检查
def extract_message(
        response: httpx.Response,
        allowed_finish_reasons=("stop", "tool_calls"),
        ) -> dict:
    try:
        result = response.json()
    except json.JSONDecodeError as error:
        raise ValueError("API 返回的内容不是合法 JSON") from error

    choices = result.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("API 响应缺少 choices")
    if not isinstance(choices[0], dict):
        raise ValueError("API 响应中的 choices[0] 不是对象")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("API 响应缺少有效的 message")

    finish_reason = choices[0].get("finish_reason")
    if finish_reason not in allowed_finish_reasons:
        raise ValueError(f"本轮响应异常结束：{finish_reason}")

    return message

#非流式请求与边界检查(仅做参考)
async def non_stream_message(client: httpx.AsyncClient, messages: list[dict], tools: list[dict]) -> dict | None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("缺少 DEEPSEEK_API_KEY")
        return None

    request_body = {
        "model": "deepseek-flash",
        "tools": tools,
        "messages": messages,
        "stream": False,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = await client.post(
            URL,
            headers=headers,
            json=request_body
        )
        response.raise_for_status()
        return extract_message(response)
    except httpx.TimeoutException:
        print("请求超时")
    except httpx.HTTPStatusError as error:
        print(f"API 请求失败：{error.response.status_code}")
        print(error.response.text)
    except httpx.RequestError as error:
        print(f"网络请求失败：{error}")
    except ValueError as error:
        print(f"响应解析失败：{error}")

    return None

#流式请求与边界检查
async def stream_message(client: httpx.AsyncClient, messages: list[dict], tools: list[dict]) -> tuple[dict | None, bool]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("缺少 DEEPSEEK_API_KEY")
        return None, False

    request_body = {
        "model": "deepseek-flash",
        "tools": tools,
        "messages": messages,
        "stream": True,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    content_parts = [] #回复内容
    tool_calls = {} #工具调用
    reasoning_parts = [] #思考过程

    stream_completed = False #流结束检查

    try:
        async with client.stream(
            "POST",
            URL,
            headers=headers,
            json=request_body,
        ) as response:
            response.raise_for_status()

            usage = None #deepseek默认在最后一个JSON块返回tokens统计
            finish_reason = None #区分流完整结束和异常结束

            async for line in response.aiter_lines(): #流式输出
                if not line or not line.startswith("data:"):
                    continue

                data = line[5:].strip()

                if data == "[DONE]":
                    stream_completed = True
                    break

                chunk = json.loads(data)
                chunk_usage = chunk.get("usage")
                if chunk_usage:
                    usage = chunk_usage

                finish_reason = chunk["choices"][0].get("finish_reason")

                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content")
                if content:
                    event = {"type": "text_delta", "text": content}
                    await emit(event)
                    content_parts.append(content)

                for call_delta in delta.get("tool_calls", []):
                    index = call_delta["index"]

                    call = tool_calls.setdefault( #索引不到返回默认值
                        index,
                        {
                            "id": "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": "",
                            },
                        },
                    )

                    if call_delta.get("id"):
                        call["id"] = call_delta["id"]

                    function_delta = call_delta.get("function", {})

                    call["function"]["name"] += function_delta.get("name", "")
                    call["function"]["arguments"] += function_delta.get("arguments", "")

                reasoning = delta.get("reasoning_content")
                if reasoning:
                    reasoning_parts.append(reasoning)

            event = {"type": "model_response_end", "usage": usage}
            await emit(event)

            if not stream_completed or finish_reason not in ("stop", "tool_calls"):
                if tool_calls:
                    print("\n流式响应未完整结束，不保存不完整工具调用")
                    return None, False

                if not content_parts and not reasoning_parts:
                    return None, False

                partial_message = {
                    "role": "assistant",
                    "content": (
                        "".join(content_parts)
                        + "\n[本轮响应未完整结束，内容不完整]"
                    ),
                }

                if reasoning_parts:
                    partial_message["reasoning_content"] = "".join(reasoning_parts)

                print(f"\n本轮响应未完整结束，保存已收到内容，异常结束原因：{finish_reason}")
                return partial_message, False

            message = {
                "role": "assistant",
                "content": "".join(content_parts),
            }

            if tool_calls:
                message["tool_calls"] = [
                    tool_calls[index]
                    for index in sorted(tool_calls)
                ]

            if reasoning_parts:
                message["reasoning_content"] = "".join(reasoning_parts)

            return message, True

    except asyncio.CancelledError: #传递取消信号->run_agent()
        raise

    except httpx.TimeoutException:
        print("流式请求超时")
        return None, False

    except httpx.HTTPStatusError as error:
        print(f"流式 API 请求失败：{error.response.status_code}")
        return None, False

    except httpx.RequestError as error:
        print(f"流式网络请求失败：{error}")
        return None, False

    except (json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"流式响应解析失败：{error}")
        return None, False

#生成旧历史摘要
async def summarize_messages(client, messages):
    summary_prompt = """
请把下面的历史对话压缩成简短摘要，保留：
1.用户目标
2.已完成的操作
3.重要文件和结果
4.错误原因
5.未完成任务和下一步

若输入已有历史摘要，请在其基础上合并后续记录，保留仍有效的目标、约束与决策。
只返回摘要正文，不要调用工具。
"""

    summary_messages = [
        {
            "role": "system",
            "content": summary_prompt,
        },
        {
            "role": "user",
            "content": json.dumps(
                messages,
                ensure_ascii=False,
            ),
        },
    ]

    request_body = {
        "model": "deepseek-flash",
        "messages": summary_messages,
        "stream": False,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }

    headers = {
        "Authorization": f"bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json",
    }
    for attempt in range(3): #重试边界结构
        try:
            response = await client.post(
                URL,
                headers=headers,
                json=request_body
            )
            response.raise_for_status()

            message = extract_message(
                response,
                allowed_finish_reasons=("stop",),
                )
            summary = message.get("content")

            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("模型没有返回有效摘要")

            return summary

        except asyncio.CancelledError:
            raise

        except (httpx.TimeoutException, httpx.RequestError) as error:
            if attempt == 2:
                print(f"请求最终失败：{error}")
                return None

            await asyncio.sleep(2 ** attempt)

        except httpx.HTTPStatusError as error:
            if error.response.status_code != 429:
                print(f"API 请求失败：{error.response.status_code}")
                print(error.response.text)
                return None

            if error.response.status_code == 429 and attempt == 2:
                print(f"请求最终失败：{error}")
                return None

            await asyncio.sleep(2 ** attempt)

        except ValueError as error:
            print(f"响应解析失败：{error}")
            return None

    return None