# Python Agent 学习仓库

从 Python 基础出发，亲手搭建一个能调用模型、执行文件工具、保存会话的 Agent。当前按 [Pi 教程](https://www.dgzhuya.com/modules/ch01-overview) 的思路学习，用 Python 实现并理解循环、工具、消息、事件和上下文管理。

**当前主线：Agent 进阶 · 工具决策钩子与只读模式。** Python 基础课程与算法题记录见 [历史归档](docs/Python学习阶段归档.md)。

## 当前进度 · 2026-10-27

| 部分 | 当前实现 |
| --- | --- |
| 模型与循环 | DeepSeek API、异步请求、流式正文与工具调用解析、工具轮数限制、连续用户输入 |
| 模块边界（进阶） | 模型请求、解析与摘要在model_client中，runner保留上下文、工具和循环，输出额度来源统一；已静态通过 |
| 执行策略（进阶） | 正在实现工具执行前允许或拒绝的回调，先接核心机制，再接两个入口的只读模式选择 |
| 工具执行 | 参数校验、路径约束、普通错误隔离、等待超时与取消传播 |
| 批次调度 | 含写入、编辑或脚本运行时整批顺序执行；其余只读工具并发执行，按输入顺序返回结果 |
| 执行通知 | 工具开始与结束事件、四种结束状态、逐监听器异常隔离 |
| 读取与搜索 | 按行范围读取、带行号的单文件搜索、单条工具结果默认 50 KiB 体积保护 |
| 会话与摘要 | 原始历史及摘要缓存保存/恢复、当前轮原文保留、覆盖位置、请求视图与摘要增量更新 |
| 多会话（进阶） | 独立会话存档、Agent传递、CLI及HTTP客户端选择、服务端接收均已静态通过 |
| 请求控制（进阶） | HTTP客户端与直接CLI的异步输入、单后台Task、/stop及退出清理均已静态通过；CLI /reset受空闲判断保护 |
| 预算与完整性 | messages 与 tools 一起粗估 token、输入与输出额度分配、单次 usage 显示、流式及非流式结束原因检查 |
| 本机HTTP入口 | FastAPI POST /chat、共享会话锁；SSE及Python客户端文字、工具进度显示均已有运行截图 |

**本次停点：** 模型调用模块迁移已整体静态通过；当前开始执行前决策回调与只读策略，尚未实现。多会话及两个入口主动停止保持完成，具体记录见[当前状态](memory/02_当前状态.md)。

**当前动手：** [工具决策钩子与只读模式](docs/Agent进阶04_工具决策钩子与只读模式.md)。由学员定义read_only_guard，并让run_agent将before_tool交给工具调用检查；拒绝或检查失败时生成tool结果，原调用不进入执行列表。

**已完成：** [主动停止当前任务](docs/Agent进阶02_主动停止当前请求.md#11-本节完成结果)。请求在后台运行，/stop取消并等待当前Task收尾，输入循环继续接收命令；两个入口都保留单活跃任务。

**上一节结果：** [多会话存储与入口选择](docs/Agent进阶01_多会话存储.md#12-本节完成结果)。入口选定会话名后，加载与保存始终指向同一段历史；默认会话继续使用原存档。

**本次调整：** 撤下Python专用搜索工具练习。现有list_files、search_file与read_file可以组合完成定位和阅读；批量目录搜索按实际需要再扩展，见[方案说明](docs/Agent第08章_跨Python文件搜索.md)。

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
.\.venv\Scripts\python.exe -m pip install -r requirement.txt
```

新环境首次配置时，在仓库根目录复制模板：

```powershell
Copy-Item .env.example .env
```

再编辑 `.env`，将占位值换为自己的密钥：

```dotenv
DEEPSEEK_API_KEY=替换为自己的密钥
```

启动：

```powershell
.\.venv\Scripts\python.exe code\agent_v1\cli.py
```

输入任务，例如：“在工作区新建 hello.txt，写入‘你好，Agent’，再读取这个文件。”任务在后台运行，期间可以输入控制命令；忙碌时普通新任务会提示先停止当前任务。输入 `/stop` 取消并等待当前任务收尾，`/session study` 选择下一次任务的会话，`/session` 显示当前选择，`/reset` 在空闲时清除当前会话历史，`/exit` 退出并由运行器清理剩余Task。启动时选择default，处理任务时加载所选会话已有的历史；多会话和主动停止功能依据静态审阅。

密钥文件、运行时会话与工作区中的个人文件按 [.gitignore](.gitignore) 排除；固定工作区约定AGENTS.md与review_python/SKILL.md已允许纳入后续提交。

### 本机HTTP入口

上方依赖清单已包含FastAPI与Uvicorn，在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn http_api:app --app-dir code\agent_v1 --host 127.0.0.1 --port 8000 --workers 1
```

当前/chat返回SSE事件流。保持服务终端运行，在另一个PowerShell中运行Python客户端：

```powershell
.\.venv\Scripts\python.exe code\agent_v1\http_client.py
```

输入任务后，客户端在后台处理一个请求，同时接收输入。输入/session study选择下一次请求的会话，/session查看当前选择，/stop取消并等待当前客户端请求收尾，/exit先清理请求再退出；忙碌时提示先停止当前请求再启动新任务。text_delta发送文字片段，agent_done.result保存最终消息（未取得时为null），普通未处理异常通过agent_error.message发送。服务端按请求的session_id选择历史，省略时使用default；客户端发送所选会话名。服务端完整任务由进程内共享锁顺序处理，使用单worker运行。普通JSON入口、SSE及Python客户端文件任务均已有学员成功运行截图，多会话及主动停止流程依据静态审阅。

## 项目入口

| 文件 | 职责 |
| --- | --- |
| [cli.py](code/agent_v1/cli.py) | 终端输入、命令分流、显示监听器及登记 |
| [http_api.py](code/agent_v1/http_api.py) | HTTP请求模型、共享锁、事件队列、流式响应与Task收尾 |
| [http_client.py](code/agent_v1/http_client.py) | 输入任务、读取本机SSE、显示文字及取得最终消息 |
| [agent_runner.py](code/agent_v1/agent_runner.py) | 上下文准备、Agent Loop、工具调度与会话管理，调用模型模块 |
| [model_client.py](code/agent_v1/model_client.py) | 模型HTTP请求、流式与非流式解析、摘要生成及模型输出事件 |
| [session_store.py](code/agent_v1/session_store.py) | 会话历史与摘要状态的保存、加载及清除 |
| [tool_schemas.py](code/agent_v1/tool_schemas.py) | AgentTool结构及工具参数模型 |
| [tool_registry.py](code/agent_v1/tool_registry.py) | 集中登记工具资料，生成参数类、函数、模型说明及顺序策略 |
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
