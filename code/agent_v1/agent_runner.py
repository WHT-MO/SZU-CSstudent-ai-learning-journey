import asyncio
import json
import os

import httpx
from pydantic import ValidationError
from dotenv import load_dotenv

from tool_schemas import tool_arg_models, tool_specs
from tools import tool_functions


URL = "https://api.deepseek.com/chat/completions"
SYSTEM_PROMPT = "请始终用中文回答用户。工具调用参数必须使用合法 JSON。"

load_dotenv()


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


def make_tool_result(tool_call_id: str, content: str) -> dict:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


async def run_agent(user_prompt: str, max_turns: int = 10) -> None:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    tools = build_tools_payload()
    turn_count = 0

    async with httpx.AsyncClient(timeout=30) as client:
        message = await request_message(client, messages, tools)

        while message is not None:
            if not message.get("tool_calls"):
                print(message.get("content", ""))
                return

            if turn_count >= max_turns:
                print("达到最大工具调用轮数")
                return

            turn_count += 1
            tool_results = []

            for tool_call in message["tool_calls"]:
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

                try:
                    tool_content = tool_function(validated_args)
                except (
                    FileNotFoundError,
                    ValueError,
                    PermissionError,
                    IsADirectoryError,
                    NotADirectoryError,
                    UnicodeDecodeError,
                ) as error:
                    tool_content = f"文件操作失败：{error}"

                tool_results.append(make_tool_result(tool_call_id, tool_content))

            messages.append(message)
            messages.extend(tool_results)
            message = await request_message(client, messages, tools)


if __name__ == "__main__":
    user_prompt = input("请输入任务：").strip()

    if not user_prompt:
        print("任务不能为空")
    else:
        asyncio.run(run_agent(user_prompt))
