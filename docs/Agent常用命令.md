# Agent 常用命令（Windows PowerShell）

每个新开的 PowerShell 窗口先切到项目根目录。下面的命令使用项目自己的 `.venv`。

```powershell
Set-Location 'D:\code\dsh\python-course'
```

## 启动或重启 HTTP 服务

在服务窗口运行这条命令。

```powershell
.\.venv\Scripts\python.exe -m uvicorn http_api:app --app-dir code\agent_v1 --host 127.0.0.1 --port 8000 --workers 1
```

看到 `Uvicorn running on http://127.0.0.1:8000` 后，保持这个窗口开着。要停止服务，在这个窗口按 `Ctrl+C`。改完服务代码后，停止再执行同一条命令来加载新版本。

`http_api:app` 指 `http_api.py` 里的 `app` 对象。`--app-dir` 告诉 Uvicorn 去哪里找这个文件。`--workers 1` 让会话锁在同一个服务进程里生效。

## 打开 HTTP 客户端

另开一个 PowerShell 窗口，切到项目根目录，再运行下面的命令。做双会话练习时，开两个这样的客户端窗口，共用上面启动的服务。

```powershell
.\.venv\Scripts\python.exe code\agent_v1\http_client.py
```

下面这些命令输入在**客户端**的「请输入任务」处，每次输一条。

| 输入 | 用途 |
| --- | --- |
| `/session study` | 下一次任务使用 `study` 会话 |
| `/session` | 查看当前会话 |
| `/mode readonly` | 下一次任务使用只读模式 |
| `/mode normal` | 切回普通模式 |
| `/stop` | 停止当前客户端请求 |
| `/exit` | 退出客户端 |

第 22 节并行练习中，两个客户端都用 `/mode readonly`。A 选 `/session http_demo_a`，B 选 `/session http_demo_b`。[练习步骤](Agent进阶22_HTTP请求事件隔离.md#运行-两个只读会话)

## 运行其他脚本

在项目根目录按用途选一条执行。

| 用途 | 命令 |
| --- | --- |
| 直接运行 Agent CLI | `.\.venv\Scripts\python.exe code\agent_v1\cli.py` |
| 跑最小 Agent 循环 | `.\.venv\Scripts\python.exe code\agent_v1\minimal_loop.py` |
| 跑最小循环独立变式 | `.\.venv\Scripts\python.exe code\agent_v1\mini_agent_practice.py` |
| 生成代码审阅报告 | `.\.venv\Scripts\python.exe code\agent_v1\review_workflow.py` |
| 跑 A/B 审阅评测 | `.\.venv\Scripts\python.exe code\agent_v1\eval_review.py` |
| 跑本地 MCP 演示 | `.\.venv\Scripts\python.exe code\agent_v1\demo_mcp_client.py` |
| 跑 RAG 演示 | `.\.venv\Scripts\python.exe code\agent_v1\rag_demo.py` |
| 查看项目的 Python 版本 | `.\.venv\Scripts\python.exe --version` |

如果 PowerShell 找不到 `.\.venv\Scripts\python.exe`，先重新执行本文开头的 `Set-Location`。`.venv` 在项目根目录。
