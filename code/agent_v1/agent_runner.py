import asyncio
import json
import httpx

from pathlib import Path
from pydantic import ValidationError

from tool_registry import tool_arg_models, tool_functions, tool_specs, serial_tool_functions
from tools import workspace_root
from agent_events import emit
from session_store import save_session, load_session
from model_client import stream_message, summarize_messages
from model_config import AGENT_MODEL_CONFIG

SYSTEM_PROMPT = "请始终用中文回答用户。工具调用参数必须使用合法 JSON。"
AGENTS_PATH = Path(workspace_root) / "AGENTS.md"
SKILLS_PROMPT = """
名称：review_python
用途：审阅 Python 文件的逻辑错误和潜在异常
路径：skills/review_python/SKILL.md
指令：任务匹配时，先用 read_file 读取技能文件，再按其中流程处理。
"""

#预算分配和输出限制
CONTEXT_BUDGET = 200000
TOKEN_MARGIN = 10000

INPUT_TOKEN_BUDGET = CONTEXT_BUDGET - AGENT_MODEL_CONFIG.max_output_tokens - TOKEN_MARGIN

#加载AGENTS.md和skills
def build_system_prompt():
    if not AGENTS_PATH.exists():
        return f"{SYSTEM_PROMPT}\n【skills】{SKILLS_PROMPT}"

    return f"{SYSTEM_PROMPT}\n【skills】{SKILLS_PROMPT}\n【工作区约定】{AGENTS_PATH.read_text(encoding="utf-8")}"
    
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

#工具收集检查
def process_tool_call(
        index,
        tool_call_id,
        function_data,
        tool_results,
        valid_tools,
        before_tool = None,
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

    try:
        reason = None
        if before_tool is not None:
            reason = before_tool(tool_name, validated_args)

        if reason is None: #在规定权限内
            valid_tools.append(
                (
                    index,
                    tool_call_id,
                    tool_function,
                    validated_args
                )
            )
            return

        tool_results[index] = make_tool_result(
            tool_call_id,
            reason,
        )
        return
    
    except Exception as error:
        tool_results[index] = make_tool_result(
            tool_call_id,
            f"权限检查失败：{error}"
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
        if item[2] in serial_tool_functions:
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

#取出队列信息
def drain_steering_messages(steering_queue):
    temp_messgae = []
    if steering_queue is None:
        return temp_messgae

    while not steering_queue.empty():
        text = steering_queue.get_nowait() #取出最早队列
        temp_messgae.append(
            {"role": "user", "content": text}
        )
    return temp_messgae

#Agent Loop结构
async def run_agent(
        user_prompt: str,
        max_turns: int = 10,
        session_id: str = "default",
        before_tool = None,
        steering_queue = None,
        ) -> dict:
    messages, summary_cache = load_session(session_id=session_id)

    if not messages or messages[0].get("role") != "system": #植入agent规则
        messages.insert(0, {
            "role": "system",
            "content": build_system_prompt(),
        })
        summary_cache = { #摘要缓存
            "summary": None,
            "next_message_index": 1,
            }

    messages[0]["content"] = build_system_prompt()
    messages.append({
        "role": "user",
        "content": user_prompt,
    })
    save_session(messages, summary_cache, session_id=session_id)

    tools = build_tools_payload()
    turn_count = 0

    default_model_result = { #无响应时默认返回字典
        "message":  None,
        "completed": False,
        "reason": None,
    }

    async with httpx.AsyncClient(timeout=30) as client: #发送请求
        while True:
            steering_messages = drain_steering_messages(steering_queue)
            if steering_messages:
                messages.extend(steering_messages)
                save_session(messages, summary_cache, session_id=session_id)
            
            request_messages = await prepare_request_messages( #压缩历史对话
                client,
                messages,
                tools,
                summary_cache=summary_cache,
                max_tokens=INPUT_TOKEN_BUDGET
            )
        
            save_session(messages, summary_cache, session_id=session_id)

            if not request_messages:
                default_model_result["reason"] = "输入预算不足"
                return default_model_result
        
            model_result = await stream_message(client, request_messages, tools) #响应返回字典
            message = model_result["message"]
            completed = model_result["completed"]

            if message is None:
                return model_result

            if not completed: #响应不完整
                if not message.get("tool_calls"):
                    messages.append(message)
                    save_session(messages, summary_cache, session_id=session_id)
                return  model_result

            if not message.get("tool_calls"): #返回回答
                messages.append(message)
                save_session(messages, summary_cache, session_id=session_id)
                if steering_queue is not None and not steering_queue.empty():
                    continue
                return model_result

            tool_results = [None] * len(message["tool_calls"])
            valid_tools = []

            if turn_count >= max_turns: #循环熔断
                for call_index, tool_call in enumerate(message["tool_calls"]):
                    tool_call_id = tool_call.get("id")
                    if not tool_call_id:
                        default_model_result["reason"] = "工具调用结构不完整"
                        print(default_model_result["reason"])
                        return default_model_result

                    tool_results[call_index] = make_tool_result(
                            tool_call_id,
                            "达到最大工具调用轮数",
                    )
                messages.append(message)
                messages.extend(tool_results)
                save_session(messages, summary_cache, session_id=session_id)
                
                default_model_result["reason"] = "达到最大工具调用轮数"
                return default_model_result
            
            turn_count += 1

            for index, tool_call in enumerate(message["tool_calls"]): #工具调用收集循环
                tool_call_id = tool_call.get("id")
                function_data = tool_call.get("function")
                if not tool_call_id:
                    default_model_result["reason"] = "工具调用结构不完整"
                    print(default_model_result["reason"])
                    return default_model_result

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
                    before_tool=before_tool,
                )

            executed_results = await execute_tool_batch(valid_tools) #执行工具

            for item, result in zip(valid_tools, executed_results):
                index = item[0]
                tool_results[index] = result

            messages.append(message)
            messages.extend(tool_results)
            save_session(messages, summary_cache, session_id=session_id)