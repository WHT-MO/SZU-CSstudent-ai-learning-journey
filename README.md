# Python Agent 学习仓库

从 Python 基础出发，亲手搭建一个能调用模型、执行文件工具、保存会话的 Agent。当前按 [Pi 教程](https://www.dgzhuya.com/modules/ch01-overview) 的思路学习，用 Python 实现并理解循环、工具、消息、事件和上下文管理。

**当前主线：Agent v1 · HTTP事件流与Python客户端。** Python 基础课程与算法题记录见 [历史归档](docs/Python学习阶段归档.md)。

## 当前进度 · 2026-10-22

| 部分 | 当前实现 |
| --- | --- |
| 模型与循环 | DeepSeek API、异步请求、流式正文与工具调用解析、工具轮数限制、连续用户输入 |
| 工具执行 | 参数校验、路径约束、普通错误隔离、等待超时与取消传播 |
| 批次调度 | 含写入、编辑或脚本运行时整批顺序执行；其余只读工具并发执行，按输入顺序返回结果 |
| 执行通知 | 工具开始与结束事件、四种结束状态、逐监听器异常隔离 |
| 读取与搜索 | 按行范围读取、带行号的单文件搜索、单条工具结果默认 50 KiB 体积保护 |
| 会话与摘要 | 原始历史及摘要缓存保存/恢复、当前轮原文保留、覆盖位置、请求视图与摘要增量更新 |
| 预算与完整性 | messages 与 tools 一起粗估 token、输入与输出额度分配、单次 usage 显示、流式及非流式结束原因检查 |
| 本机HTTP入口 | FastAPI POST /chat、共享会话锁；SSE文字片段、用量事件与完整结果已有运行截图 |

**本次停点：** run_python实际使用已完成；本机HTTP事件流已有text_delta、model_response_end及agent_done的运行截图，服务端本节目标完成。具体证据见[当前状态](memory/02_当前状态.md)。

**当前动手：** [Python HTTP客户端](docs/Agent实战篇_HTTP客户端.md)。新增http_client.py，用已有HTTPX流式读取本机/chat，将text_delta显示为连续文字，并返回agent_done.result。客户端当前尚未编写。

## Agent v1 的文件与脚本工具

路径参数相对于 `code/agent_v1/workspace/`，文件工具限制在该目录内。run_python以该目录为工作目录，脚本使用当前账号权限。

| 工具 | 用途 |
| --- | --- |
| `list_files` | 列出目录中的文件名 |
| `read_file` | 读取文件，可指定包含两端的起止行号 |
| `search_file` | 按原样、区分大小写搜索单个文件，返回行号并限制匹配行数 |
| `write_file` | 写入或覆盖文件内容 |
| `edit_file` | 替换唯一匹配的一段文本 |
| `run_python` | 使用当前解释器运行工作区脚本，返回退出码、stdout、stderr；子进程超时设为5秒 |

当前 token 计数仍采用字符数粗估；单条结果的字节限制与整次请求的 token 预算分别处理。工具外层超时或取消表示结束等待，底层线程可能继续执行；run_python另设子进程自身超时。

## 运行

使用 Python 3.12 或更新版本。以下为 Windows PowerShell 示例，在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install httpx "pydantic>=2,<3" python-dotenv
```

在仓库根目录新建 `.env`：

```dotenv
DEEPSEEK_API_KEY=替换为自己的密钥
```

启动：

```powershell
.\.venv\Scripts\python.exe code\agent_v1\cli.py
```

输入任务，例如：“在工作区新建 hello.txt，写入‘你好，Agent’，再读取这个文件。”每条任务完成后继续接收下一条；输入 `/reset` 清除会话历史，输入 `/exit` 退出。启动后处理任务时会加载已有历史。

密钥文件、运行时会话与工作区中的个人文件按 [.gitignore](.gitignore) 排除；示例学习文件按现有规则保留。

### 本机HTTP入口

额外安装FastAPI与Uvicorn，在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn
.\.venv\Scripts\python.exe -m uvicorn http_api:app --app-dir code\agent_v1 --host 127.0.0.1 --port 8000 --workers 1
```

当前/chat已改为SSE事件流，连接及任务收尾静态通过。保持服务终端运行，在另一个PowerShell中提交任务并查看事件：

```powershell
'{"prompt":"Say hello in three short sentences."}' | curl.exe -sS -N -H "Content-Type: application/json" --data-binary "@-" "http://127.0.0.1:8000/chat"
```

text_delta发送文字片段，agent_done.result保存最终消息（未取得时为null），普通未处理异常通过agent_error.message发送。当前沿用同一份session.json，完整任务由进程内共享锁顺序处理，使用单worker运行。普通JSON入口和当前SSE入口均已有学员成功运行截图。

## 项目入口

| 文件 | 职责 |
| --- | --- |
| [cli.py](code/agent_v1/cli.py) | 终端输入、命令分流、显示监听器及登记 |
| [http_api.py](code/agent_v1/http_api.py) | HTTP请求模型、共享锁、事件队列、流式响应与Task收尾 |
| [agent_runner.py](code/agent_v1/agent_runner.py) | 模型请求、流式解析、Agent Loop、工具调度与会话管理 |
| [session_store.py](code/agent_v1/session_store.py) | 会话历史与摘要状态的保存、加载及清除 |
| [tool_schemas.py](code/agent_v1/tool_schemas.py) | 工具说明、参数模型与注册 |
| [tools.py](code/agent_v1/tools.py) | 文件及Python脚本工具实现与路径处理 |
| [agent_events.py](code/agent_v1/agent_events.py) | 监听器列表与事件分发 |

[最小循环练习](code/agent_v1/minimal_loop.py)、[工具依赖实验](code/agent_v1/tool_order_demo.py) 用于理解流程；[流式 mock](code/agent_v1/test_stream_mock.py)、[摘要 mock](code/agent_v1/test_summary_mock.py) 用于学习固定响应和错误处理。流式 mock 当前只保留最后一个场景，运行记录与保留用例分开记录。

## 学习导航

| 内容 | 入口 |
| --- | --- |
| 当前章节路线 | [以 Pi 教程为主线的学习计划](docs/Agent学习计划_按Pi教程.md) |
| 最新进度与下次停点 | [当前状态](memory/02_当前状态.md) |
| 职责、最小循环与模型请求 | [第 2 章](docs/Agent第02章_职责与调用关系.md) · [第 3 章](docs/Agent第03章_固定回复与最小循环.md) · [第 4 章](docs/Agent第04章_把模型函数传给循环.md) |
| 工具、消息与事件 | [第 5 章](docs/Agent第05章_工具执行依赖.md) · [第 6 章](docs/Agent第06章_消息的三种用途.md) · [第 7 章](docs/Agent第07章_工具执行通知.md) |
| 上下文与压缩 | [第 8 章：读取策略、输出限制与上下文预算](docs/Agent第08章_大工具输出与分段读取.md) · [第 9 章：摘要覆盖范围、请求视图与更新](docs/Agent第09章_摘要与当前任务.md) |
| 项目约定 | [第 8 章补充：项目规则与系统提示](docs/Agent第08章_项目规则与系统提示.md) |
| 按需流程 | [第 8 章补充：技能目录与按需加载](docs/Agent第08章_技能目录与按需加载.md) |
| 会话存储与恢复 | [第 10 章：会话状态保存与恢复](docs/Agent第10章_会话状态保存与恢复.md) |
| 复习 | [Agent 复习资料](docs/Agent复习资料.md) · [架构地图](docs/Agent架构地图.md) · [工具方法卡](docs/Agent工具方法卡.md) · [语法模板卡](docs/语法模板卡.md) |
| Python 与算法历史 | [课程和成果归档](docs/Python学习阶段归档.md) · [Python 路线图](docs/我的python路线图.md) · [算法题代码](code/洛谷/) |
| 学习协作与长期路线 | [教学约定](docs/教学机制与协作约定.md) · [学习路线与辅线](docs/学习路线与辅线.md) · [长期目标](docs/职业路线_2027暑假与Agent目标.md) |

`docs/` 保存讲义和复习资料，`code/` 保存学习实现，`memory/` 保存课程进度协议。详细会话纪要与学员档案只留本机，分工见 [memory/README.md](memory/README.md)。
