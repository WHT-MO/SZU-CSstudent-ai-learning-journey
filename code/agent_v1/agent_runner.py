import asyncio
import json
import os

import httpx
from pathlib import Path
from pydantic import ValidationError
from dotenv import load_dotenv

from tool_schemas import tool_arg_models, tool_specs
from tools import tool_functions


URL = "https://api.deepseek.com/chat/completions"
SYSTEM_PROMPT = "请始终用中文回答用户。工具调用参数必须使用合法 JSON。"
HISTORY_PATH = Path(__file__).resolve().parent / "session.json"

load_dotenv() #读取API_key

#保存会话历史
def save_messages(messages):
    text = json.dumps(
        messages,
        ensure_ascii=False,
        indent=2,
    )

    temp_path = HISTORY_PATH.with_suffix(".tmp") #原子写入

    try:
        temp_path.write_text(text,encoding="utf-8")
        temp_path.replace(HISTORY_PATH)
    except OSError as error:
        print(f"会话历史保存失败，本轮内容不会被记忆：{error}")

#读取会话历史
def load_messages():
    if not HISTORY_PATH.exists():
        return []

    try:
        text = HISTORY_PATH.read_text(encoding="utf-8")
        messages = json.loads(text)
    except (OSError, json.JSONDecodeError) as error:
        print(f"会话历史读取失败，将从新会话开始：{error}")
        return []

    if not isinstance(messages, list):
        print("会话历史格式错误，将从新会话开始")
        return []

    return messages

#清除会话历史
def clear_session():
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()

    print("会话历史已清除")

#会话长度边界检查
def trim_messages(messages, max_messages=40):
    if len(messages) <= max_messages + 1:
        return messages

    system_message = messages[0]
    history = messages[1:]

    start = len(history) - max_messages

    #不从 assistant/tool 调用中间开始
    while start < len(history) and history[start].get("role") != "user":
        start += 1

    return [system_message, *history[start:]]

#模型读取工具
def build_tools_payload() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tool_specs
    ]

#响应结构边界检查
def extract_message(response: httpx.Response) -> dict:
    try:
        result = response.json()
    except json.JSONDecodeError as error:
        raise ValueError("API 返回的内容不是合法 JSON") from error

    choices = result.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("API 响应缺少 choices")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("API 响应缺少有效的 message")

    return message

#非流式请求与边界检查(流式出错可切换)
async def request_message(client: httpx.AsyncClient, messages: list[dict], tools: list[dict]) -> dict | None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("缺少 DEEPSEEK_API_KEY")
        return None

    request_body = {
        "model": "deepseek-flash",
        "tools": tools,
        "messages": messages,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = await client.post(URL, headers=headers, json=request_body)
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
async def stream_message(client: httpx.AsyncClient, messages: list[dict], tools: list[dict]) -> dict | None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("缺少 DEEPSEEK_API_KEY")
        return None

    request_body = {
        "model": "deepseek-flash",
        "tools": tools,
        "messages": messages,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    content_parts = [] #回复内容
    tool_calls = {} #工具调用
    reasoning_parts = [] #思考过程

    stream_completed = False #会话完整性检查

    try:
        async with client.stream(
            "POST",
            URL,
            headers=headers,
            json=request_body,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines(): #流式输出
                if not line or not line.startswith("data:"):
                    continue

                data = line[5:].strip()

                if data == "[DONE]":
                    stream_completed = True
                    break

                chunk = json.loads(data)
                delta = chunk["choices"][0].get("delta", {})

                content = delta.get("content")
                if content:
                    print(content, end="", flush=True)
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

            if not stream_completed:
                print("流式响应未完整结束，部分内容不会保存")
                return None

            print()
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

            return message

    except httpx.TimeoutException:
        print("流式请求超时")
    except httpx.HTTPStatusError as error:
        print(f"流式 API 请求失败：{error.response.status_code}")
    except httpx.RequestError as error:
        print(f"流式网络请求失败：{error}")
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"流式响应解析失败：{error}")

#并行调用已校验工具
async def execute_validated_tool(
        tool_call_id,
        tool_function,
        validated_args,
):
    try: #文件校验
        tool_content = await asyncio.wait_for(
            asyncio.to_thread(
            tool_function,
            validated_args,
            ),
        timeout=10,
        )
    except asyncio.TimeoutError: #工具独立超时
        tool_content = "工具执行超时"
    except (
        FileNotFoundError, #文件不存在
        ValueError, #路径超出 workspace
        PermissionError, #没有访问权限
        IsADirectoryError, #把目录当成文件读写
        NotADirectoryError, #路径非目录
        UnicodeDecodeError, #文件不是 UTF-8 编码
    ) as error:
        tool_content = f"文件操作失败：{error}"
    except Exception as error:
        tool_content = (
            f"工具执行出现未预期错误：{type(error).__name__}: {error}"
        )

    return make_tool_result(
        tool_call_id,
        tool_content,
    )

#错误工具参数检查
def make_tool_result(tool_call_id: str, content: str) -> dict:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }

#Agent Loop结构
async def run_agent(user_prompt: str, max_turns: int = 10) -> None:
    messages = load_messages()
    if not messages or messages[0].get("role") != "system": #植入agent规则
        messages.insert(0, {
            "role": "system",
            "content": SYSTEM_PROMPT,
        })

    messages = trim_messages(messages)
    messages.append({
        "role": "user",
        "content": user_prompt,
    })
    save_messages(messages)

    tools = build_tools_payload()
    turn_count = 0

    async with httpx.AsyncClient(timeout=30) as client: #发送请求
        message = await stream_message(client, messages, tools)

        while message is not None:
            if not message.get("tool_calls"): #返回回答
                messages.append(message)
                save_messages(messages)
                return

            if turn_count >= max_turns: #循环熔断
                print("达到最大工具调用轮数")
                return

            turn_count += 1
            tool_results = []
            valid_tools = []

            for tool_call in message["tool_calls"]: #工具调用收集循环
                tool_call_id = tool_call.get("id")
                function_data = tool_call.get("function")
                if not tool_call_id or not isinstance(function_data, dict):
                    print("工具调用结构不完整")
                    return

                tool_name = function_data.get("name")
                raw_arguments = function_data.get("arguments")
                if not tool_name or raw_arguments is None:
                    print("工具调用缺少名称或参数")
                    return

                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    print("工具参数不是合法 JSON")
                    print(raw_arguments)
                    return

                argument_model = tool_arg_models.get(tool_name)
                tool_function = tool_functions.get(tool_name)
                if argument_model is None or tool_function is None:
                    print(f"未知工具：{tool_name}")
                    return

                try:
                    validated_args = argument_model.model_validate(arguments)
                except ValidationError as error:
                    tool_results.append(
                        make_tool_result(
                            tool_call_id,
                            f"工具参数校验失败：{error}",
                        )
                    )
                    continue

                valid_tools.append(
                    (
                        tool_call_id,
                        tool_function,
                        validated_args
                    )
                )

            parallel_tasks = [ #执行工具
                execute_validated_tool(
                    tool_call_id,
                    tool_function,
                    validated_args,
                )
                for tool_call_id, tool_function, validated_args in valid_tools
            ]

            tool_results.extend(
                await asyncio.gather(*parallel_tasks)
            )
            messages.append(message)
            messages.extend(tool_results)
            save_messages(messages)
            message = await stream_message(client, messages, tools) #再次请求


if __name__ == "__main__":
    user_prompt = input("请输入任务：").strip()

    if user_prompt == "/reset":
        clear_session()
    elif not user_prompt:
        print("任务不能为空")
    else:
        asyncio.run(run_agent(user_prompt))
