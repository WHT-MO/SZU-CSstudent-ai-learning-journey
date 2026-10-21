import asyncio
import json
import os

import httpx
from pathlib import Path
from pydantic import ValidationError
from dotenv import load_dotenv

from tool_schemas import tool_arg_models, tool_specs
from tools import tool_functions
from tool_events import emit


URL = "https://api.deepseek.com/chat/completions"
SYSTEM_PROMPT = "请始终用中文回答用户。工具调用参数必须使用合法 JSON。"
HISTORY_PATH = Path(__file__).resolve().parent / "session.json"

load_dotenv() #读取API_key

#预算分配和输出限制
CONTEXT_BUDGET = 200000
MAX_OUTPUT_TOKENS = 8000
TOKEN_MARGIN = 2000

INPUT_TOKEN_BUDGET = CONTEXT_BUDGET - MAX_OUTPUT_TOKENS - TOKEN_MARGIN

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

#计算tokens估计值
def estimate_request_tokens(messages, tools):
    request_data = {
        "messages": messages,
        "tools": tools,
    }
    text = json.dumps(
        request_data,
        ensure_ascii=False,
    )
    return len(text) // 4

#会话长度边界检查
def trim_messages(messages, tools, max_tokens):
    tokens = estimate_request_tokens(messages, tools)
    if tokens <= max_tokens:
        return messages

    system_message = messages[0]
    history = messages[1:]
    start = 0

    #不从 assistant/tool 调用中间开始
    while len(history) > start:
        if history[start].get("role") != "user":
            start += 1
            continue

        tokens = estimate_request_tokens([system_message, *history[start:]], tools)
        if tokens <= max_tokens // 4:
            break

        start += 1

    return [system_message, *history[start:]]

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

#拆分会话
def split_messages_for_summary(messages):
    for index in range(len(messages) -1 ,0, -1):
        if messages[index]["role"] == "user" :
            current_start = index
            break

    system_message = messages[0]
    old_messages = messages[1:current_start]
    current_turn = messages[current_start:]
    
    return system_message, old_messages, current_turn

#构造聊天请求信息
def build_request_messages(messages, summary_cache):
    if summary_cache["summary"] is None:
        return messages

    request_messages = [
        messages[0],
        {
            "role": "system",
            "content": f"历史摘要：\n{summary_cache["summary"]}",
        },
        *messages[summary_cache["next_message_index"]:]
    ]

    return request_messages

#会话压缩协程
async def prepare_request_messages(client, messages, tools, summary_cache, max_tokens):
    request_messages = build_request_messages(messages, summary_cache)
    if estimate_request_tokens(request_messages, tools) <= max_tokens:
        return request_messages

    system_message, old_messages, current_turn = split_messages_for_summary(request_messages)
    current_start = len(messages) - len(current_turn)

    kept_messages = [system_message, *current_turn]
    if estimate_request_tokens(kept_messages, tools) > max_tokens:
        print("系统提示、当前轮和工具定义合计超过输入预算，本次停止请求")
        return None

    if summary_cache["summary"] is None or current_start > summary_cache["next_message_index"]:
        new_summary = await summarize_messages(client, old_messages)
        if not new_summary:
            print("摘要失败，返回当前轮")
            return kept_messages

        summary_cache["summary"] = new_summary
        summary_cache["next_message_index"] = current_start

    request_messages = build_request_messages(messages, summary_cache)

    if estimate_request_tokens(request_messages, tools) > max_tokens:
        print("摘要超过输入预算，返回当前轮")
        return kept_messages

    return request_messages

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

            print()   
            if usage:
                print("输入：",usage["prompt_tokens"])
                print("输出：",usage["completion_tokens"])
                print("合计：",usage["total_tokens"])

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

#工具收集检查
def process_tool_call(
        index,
        tool_call_id,
        function_data,
        tool_results,
        valid_tools,
):
    tool_name = function_data.get("name")
    raw_arguments = function_data.get("arguments")
    if not tool_name or raw_arguments is None:
        tool_results[index] = make_tool_result(
                tool_call_id,
                "工具调用缺少名称或参数",
        )
        return

    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        tool_results[index] = make_tool_result(
                tool_call_id,
                "工具参数不是合法 JSON",
        )
        return

    argument_model = tool_arg_models.get(tool_name)
    tool_function = tool_functions.get(tool_name)
    if argument_model is None or tool_function is None:
        tool_results[index] = make_tool_result(
                tool_call_id,
                f"未知工具：{tool_name}",
        )
        return

    try:
        validated_args = argument_model.model_validate(arguments)
    except ValidationError as error:
        tool_results[index] = make_tool_result(
                tool_call_id,
                f"工具参数校验失败：{error}",
        )
        return

    valid_tools.append(
        (
            index,
            tool_call_id,
            tool_function,
            validated_args
        )
    )
    return

#并行调用已校验工具
async def execute_validated_tool(
        tool_call_id,
        tool_function,
        validated_args,
):
    await emit({ #工具开始通知
        "type": "tool_start",
        "tool_call_id": tool_call_id,
    })
    
    try: #文件校验
        tool_content = await asyncio.wait_for(
            asyncio.to_thread(
            tool_function,
            validated_args,
            ),
        timeout=10,
        )
        status = "success"

    except asyncio.CancelledError:
        status = "cancelled"
        await emit({
            "type": "tool_end",
            "tool_call_id": tool_call_id,
            "status": status,
        })
        raise #传递取消信号

    except asyncio.TimeoutError: #工具独立超时(不能强制杀掉线程)
        tool_content = "工具执行超时"
        status = "timeout"

    except (
        FileNotFoundError, #文件不存在
        ValueError, #路径超出 workspace
        PermissionError, #没有访问权限
        IsADirectoryError, #把目录当成文件读写
        NotADirectoryError, #路径非目录
        UnicodeDecodeError, #文件不是 UTF-8 编码
    ) as error:
        tool_content = f"文件操作失败：{error}"
        status = "error"

    except Exception as error:
        tool_content = (
            f"工具执行出现未预期错误：{type(error).__name__}: {error}"
        )
        status = "error"

    await emit({ #工具结束通知
        "type": "tool_end",
        "tool_call_id": tool_call_id,
        "status": status,
    })

    return make_tool_result(
        tool_call_id,
        tool_content,
    )

#批次执行工具
async def execute_tool_batch(valid_tools):
    has_write = False #判断是否有文件修改
    for item in valid_tools:
        if item[2] == tool_functions["write_file"] or item[2] == tool_functions["edit_file"]:
            has_write = True

    if has_write == True: #处理工具调度
        executed_results = [ #执行工具
            await execute_validated_tool(
                tool_call_id,
                tool_function,
                validated_args,
            )
            for index, tool_call_id, tool_function, validated_args in valid_tools
        ]
    else:
        parallel_tasks = [ #收集执行工具
            execute_validated_tool(
                tool_call_id,
                tool_function,
                validated_args,
            )
            for index, tool_call_id, tool_function, validated_args in valid_tools
        ]                
        executed_results = await asyncio.gather(*parallel_tasks) #并发执行，按输入顺序返回结果

    return executed_results    

#限制工具单次输出长度
def limit_tool_output(content: str, max_bytes: int = 50 * 1024) -> str:
    encoded = content.encode("utf-8")
    if len(encoded) > max_bytes:
        notice = "\n【结果不完整、只展示开头，可缩小读取范围或搜索条件后重取】"
        body_limit = max_bytes - len(notice.encode("utf-8"))
        limit_content = encoded[:body_limit].decode("utf-8", errors="ignore")
        return notice + limit_content
        
    return content

#生成工具执行结果
def make_tool_result(tool_call_id: str, content: str) -> dict:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": limit_tool_output(content),
    }

#Agent Loop结构
async def run_agent(user_prompt: str, max_turns: int = 10) -> None:
    messages = load_messages()
    if not messages or messages[0].get("role") != "system": #植入agent规则
        messages.insert(0, {
            "role": "system",
            "content": SYSTEM_PROMPT,
        })

    messages.append({
        "role": "user",
        "content": user_prompt,
    })
    save_messages(messages)

    summary_cache = { #摘要缓存
        "summary": None,
        "next_message_index": 1,
        }
    tools = build_tools_payload()
    turn_count = 0

    async with httpx.AsyncClient(timeout=30) as client: #发送请求
        request_messages = await prepare_request_messages( #压缩历史对话
            client,
            messages,
            tools,
            summary_cache=summary_cache,
            max_tokens=INPUT_TOKEN_BUDGET
        )
        if not request_messages:
            return
        
        message, completed = await stream_message(client, request_messages, tools)

        while message is not None:
            if not completed: #响应不完整
                if not message.get("tool_calls"):
                    messages.append(message)
                    save_messages(messages)
                return

            if not message.get("tool_calls"): #返回回答
                messages.append(message)
                save_messages(messages)
                return

            tool_results = [None] * len(message["tool_calls"])
            valid_tools = []

            if turn_count >= max_turns: #循环熔断
                for call_index, tool_call in enumerate(message["tool_calls"]):
                    tool_call_id = tool_call.get("id")
                    if not tool_call_id:
                        print("工具调用结构不完整")
                        return

                    tool_results[call_index] = make_tool_result(
                            tool_call_id,
                            "达到最大工具调用轮数",
                    )
                messages.append(message)
                messages.extend(tool_results)
                save_messages(messages)
                return
            
            turn_count += 1

            for index, tool_call in enumerate(message["tool_calls"]): #工具调用收集循环
                tool_call_id = tool_call.get("id")
                function_data = tool_call.get("function")
                if not tool_call_id:
                    print("工具调用结构不完整")
                    return

                if not isinstance(function_data, dict):
                    tool_results[index] = make_tool_result(
                        tool_call_id,
                        "工具调用结构不完整",
                    )
                    continue

                process_tool_call(
                    index,
                    tool_call_id,
                    function_data,
                    tool_results,
                    valid_tools,
                )

            executed_results = await execute_tool_batch(valid_tools) #执行工具

            for item, result in zip(valid_tools, executed_results):
                index = item[0]
                tool_results[index] = result

            messages.append(message)
            messages.extend(tool_results)
            save_messages(messages)

            request_messages = await prepare_request_messages(
                client,
                messages,
                tools,
                summary_cache=summary_cache,
                max_tokens=INPUT_TOKEN_BUDGET
            )
            if not request_messages:
                return
            
            message, completed = await stream_message(client, request_messages, tools) #再次请求


if __name__ == "__main__":
    user_prompt = input("请输入任务：").strip()

    if user_prompt == "/reset":
        clear_session()
    elif not user_prompt:
        print("任务不能为空")
    else:
        asyncio.run(run_agent(user_prompt))
