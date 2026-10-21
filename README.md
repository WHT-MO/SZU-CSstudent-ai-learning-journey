# Python Agent 学习仓库

从 Python 基础出发，亲手搭建一个能调用模型、执行文件工具、保存会话的 Agent。当前按 [Pi 教程](https://www.dgzhuya.com/modules/ch01-overview) 的思路学习，用 Python 实现并理解循环、工具、消息、事件和上下文管理。

**当前主线：Agent v1 · 第 9 章上下文压缩与摘要更新。** Python 基础课程与算法题记录见 [历史归档](docs/Python学习阶段归档.md)。

## 当前进度 · 2026-10-22

| 部分 | 当前实现 |
| --- | --- |
| 模型与循环 | DeepSeek API、异步请求、流式正文与工具调用解析、工具轮数限制 |
| 工具执行 | 参数校验、路径约束、普通错误隔离、等待超时与取消传播 |
| 批次调度 | 含写入或编辑时整批顺序执行；其余只读工具并发执行，按输入顺序返回结果 |
| 执行通知 | 工具开始与结束事件、四种结束状态、逐监听器异常隔离 |
| 读取与搜索 | 按行范围读取、带行号的单文件搜索、单条工具结果默认 50 KiB 体积保护 |
| 会话与摘要 | 原始历史保存/恢复、当前轮原文保留、任务内摘要缓存、覆盖位置、请求视图与摘要增量更新 |
| 预算与完整性 | messages 与 tools 一起粗估 token、输入与输出额度分配、单次 usage 显示、流式及非流式结束原因检查 |

**本次停点：** 第 9 章的消息切分、请求视图、摘要复用与增量更新已通过源码静态审阅。本次新增实现未单独运行回归；既有闭环和 mock 运行记录见 [当前状态](memory/02_当前状态.md)。

**下次继续：** 摘要与覆盖位置的持久化、恢复，与第 10 章会话管理衔接。当前摘要缓存只在单次任务内保留。

## Agent v1 的文件工具

工具操作范围为 `code/agent_v1/workspace/`，参数中的路径相对于该目录。

| 工具 | 用途 |
| --- | --- |
| `list_files` | 列出目录中的文件名 |
| `read_file` | 读取文件，可指定包含两端的起止行号 |
| `search_file` | 按原样、区分大小写搜索单个文件，返回行号并限制匹配行数 |
| `write_file` | 写入或覆盖文件内容 |
| `edit_file` | 替换唯一匹配的一段文本 |

当前 token 计数仍采用字符数粗估；单条结果的字节限制与整次请求的 token 预算分别处理。工具超时表示结束等待，底层线程可能继续执行。

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
.\.venv\Scripts\python.exe code\agent_v1\agent_runner.py
```

输入任务，例如：“在工作区新建 hello.txt，写入‘你好，Agent’，再读取这个文件。”输入 `/reset` 可清除会话历史。当前入口每次启动接收一个任务；再次启动会加载已有历史。

密钥文件、运行时会话与工作区中的个人文件按 [.gitignore](.gitignore) 排除；示例学习文件按现有规则保留。

## 项目入口

| 文件 | 职责 |
| --- | --- |
| [agent_runner.py](code/agent_v1/agent_runner.py) | 模型请求、流式解析、Agent Loop、工具调度与会话管理 |
| [tool_schemas.py](code/agent_v1/tool_schemas.py) | 工具说明、参数模型与注册 |
| [tools.py](code/agent_v1/tools.py) | 文件工具实现与路径检查 |
| [tool_events.py](code/agent_v1/tool_events.py) | 工具事件显示与监听器调用 |

[最小循环练习](code/agent_v1/minimal_loop.py)、[工具依赖实验](code/agent_v1/tool_order_demo.py) 用于理解流程；[流式 mock](code/agent_v1/test_stream_mock.py)、[摘要 mock](code/agent_v1/test_summary_mock.py) 用于学习固定响应和错误处理。流式 mock 当前只保留最后一个场景，运行记录与保留用例分开记录。

## 学习导航

| 内容 | 入口 |
| --- | --- |
| 当前章节路线 | [以 Pi 教程为主线的学习计划](docs/Agent学习计划_按Pi教程.md) |
| 最新进度与下次停点 | [当前状态](memory/02_当前状态.md) |
| 职责、最小循环与模型请求 | [第 2 章](docs/Agent第02章_职责与调用关系.md) · [第 3 章](docs/Agent第03章_固定回复与最小循环.md) · [第 4 章](docs/Agent第04章_把模型函数传给循环.md) |
| 工具、消息与事件 | [第 5 章](docs/Agent第05章_工具执行依赖.md) · [第 6 章](docs/Agent第06章_消息的三种用途.md) · [第 7 章](docs/Agent第07章_工具执行通知.md) |
| 上下文与压缩 | [第 8 章：读取策略、输出限制与上下文预算](docs/Agent第08章_大工具输出与分段读取.md) · [第 9 章：摘要覆盖范围、请求视图与更新](docs/Agent第09章_摘要与当前任务.md) |
| 复习 | [Agent 复习资料](docs/Agent复习资料.md) · [架构地图](docs/Agent架构地图.md) · [工具方法卡](docs/Agent工具方法卡.md) · [语法模板卡](docs/语法模板卡.md) |
| Python 与算法历史 | [课程和成果归档](docs/Python学习阶段归档.md) · [Python 路线图](docs/我的python路线图.md) · [算法题代码](code/洛谷/) |
| 学习协作与长期路线 | [教学约定](docs/教学机制与协作约定.md) · [学习路线与辅线](docs/学习路线与辅线.md) · [长期目标](docs/职业路线_2027暑假与Agent目标.md) |

`docs/` 保存讲义和复习资料，`code/` 保存学习实现，`memory/` 保存课程进度协议。详细会话纪要与学员档案只留本机，分工见 [memory/README.md](memory/README.md)。
