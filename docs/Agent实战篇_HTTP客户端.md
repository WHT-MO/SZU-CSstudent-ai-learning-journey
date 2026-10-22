# 应用阶段：用Python读取自己的Agent服务

> 当前进展：2026-10-22。服务端SSE已有学员运行截图；本节客户端尚未编写。源码由学员亲写，当前只安排实际客户端功能，不另建测试脚本。

## 1. 本节目标

调用自己已运行的POST /chat，把原始data事件读成连续文字，并取得agent_done中的完整消息。

```text
客户端发送prompt → 本机HTTP服务 → 既有run_agent
客户端显示文字 ← 读取并解析SSE ← 模型与工具事件
```

服务端继续负责模型密钥、工具、历史和共享锁；客户端只负责发送用户输入与读取显示。使用已有HTTPX，与agent_runner.py中的stream_message复用同一种流式读取方式。

## 2. 本次实际用到的已有调用

| 写法 | 本次作用 |
| --- | --- |
| httpx.AsyncClient(timeout=60) | 创建HTTP客户端，为等待响应数据留出时间；此值不是整项任务的总时限 |
| client.stream("POST", url, json=...) | 发送JSON并保持响应可逐段读取；用async with进入 |
| response.raise_for_status() | 将HTTP失败状态作为异常报告 |
| response.aiter_lines() | 用async for逐行取得服务返回的文字 |
| json.loads(...) | 将一条事件的JSON文字转成Python字典 |

client来自AsyncClient上下文的as client；response来自stream上下文的as response；line来自async for；event由json.loads得到。queue与Task都留在服务端，当前客户端读取HTTP响应即可。

## 3. 事件读取与显示

当前服务每条事件使用一行data:加JSON，消息之间为空行。客户端只处理data:开头的行，取其后的JSON并解析为event字典。本项目此处不泛化多行SSE解析；约定与已经实现的输出一致。

| event["type"] | 当前处理 |
| --- | --- |
| text_delta | 将event["text"]追加打印，使用end=""和flush=True |
| agent_done | 换行，并返回event["result"]，保留完整消息供调用者使用 |
| agent_error | 显示event["message"]，返回None |

当前目标先完成文字与整项结果；model_response_end和工具事件可读过后继续。agent_done.result中的完整回答已经通过片段显示，不再把它重复打印一遍。本服务的整项结束事件是agent_done。

## 4. 当前动手

在code/agent_v1新建http_client.py。定义异步函数request_agent(prompt: str) -> dict | None，向http://127.0.0.1:8000/chat提交{"prompt": prompt}，按第2、3节读取、显示与返回结果。沿用已有asyncio、json、httpx。

增加受if __name__ == "__main__"保护的启动入口，读取一次用户输入，通过asyncio.run调用该函数。当前安排一次任务的完整客户端，不新增连续输入、远端部署或会话管理功能。先亲写这一项，源码审阅后直接进入实际使用。

## 5. 参考

- 本项目agent_runner.py中的stream_message：已有client.stream、aiter_lines与data行解析。
- [HTTPX异步流式响应](https://www.python-httpx.org/async/#streaming-responses)
- [服务端事件流](Agent实战篇_HTTP事件流.md)
