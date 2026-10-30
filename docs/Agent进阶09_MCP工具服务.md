# 进阶第9节：MCP工具服务

> 2026-10-30。前八节已静态通过。新主题按官方Python SDK 2.x安排，使用MCPServer；本节当前只由学员安装依赖并编写独立服务端，客户端连接和接入Agent随后处理。当前虚拟环境尚未安装mcp，服务端脚本尚未编写。

## 1. 目标：调用独立程序提供的工具

MCP是Model Context Protocol，中文为模型上下文协议。它约定应用如何发现工具、提交工具调用并取得结果。SDK是实现这些约定的开发库。

现有工具由tool_registry保存Python函数，Agent直接调用它们。MCP让工具由另一个程序提供，Agent使用客户端代码与它通信；工具服务能被兼容的应用复用，调用方通过协议取得工具名称、说明和参数信息。

本次用get_python_version作为最小工具，观察独立进程提供能力的方式。它返回工具服务进程的Python版本；新的能力是服务端与客户端之间的标准通信链路。

## 2. 各方负责什么

| 参与方 | 职责 |
| --- | --- |
| 模型 | 根据Agent提供的工具说明，提出工具调用 |
| Agent中的MCP客户端代码 | 连接工具服务、发现工具、发送调用和读取结果，再由Agent组织模型请求 |
| MCP工具服务 | 声明工具、执行函数、返回结果 |

模型不会直接读取Python对象或连接工具服务；Agent仍负责把工具说明与结果放入模型接口的请求中。现有http_client.py是人向/chat发任务的客户端，与这里连接工具服务的MCP客户端职责不同。

工具发现、MCP调用、结果转换与Agent注册会分段接入。本次写好服务端不代表模型已经能调用它。

## 3. 本次通信方式：stdio

stdio指标准输入与标准输出。本次由客户端将服务脚本作为子进程启动，通过该进程的stdin/stdout交换MCP消息。服务端run进入循环，等待客户端消息；后续会复用已经学过的子进程与异步上下文概念。

stdout属于协议通道，工具结果使用return交给SDK。普通print写入stdout会混入协议消息；需要运行日志时用logging或stderr。当前练习只返回版本字符串，SDK负责协议收发。

参考：[官方SDK服务运行方式](https://py.sdk.modelcontextprotocol.io/run/)、[官方日志说明](https://py.sdk.modelcontextprotocol.io/handlers/logging/)。

## 4. 依赖与版本

官方Python SDK当前稳定线为2.x，要求Python 3.11+。本项目约定Python 3.12+，本节依赖限制在2.x：

```powershell
# 在D:\code\dsh\python-course执行
.\.venv\Scripts\python.exe -m pip install "mcp>=2,<3"
```

当前写法使用from mcp.server import MCPServer。2.x的新项目依照本节来源；网上使用FastMCP及ClientSession初始化的旧版片段应先核对版本，不混入本节。

参考：[官方安装说明](https://py.sdk.modelcontextprotocol.io/get-started/installation/)、[SDK 2.x变化](https://py.sdk.modelcontextprotocol.io/whats-new/)。

## 5. 当前动手：demo_mcp_server.py

在code/agent_v1新建demo_mcp_server.py。用以下已核对的SDK入口组织服务，具体脚本由学员编写：

- 导入MCPServer，创建server = MCPServer("course-tools")。它负责注册工具和处理MCP消息，作用类似此前创建FastAPI应用对象。
- 定义普通函数get_python_version() -> str，通过sys.version返回当前工具进程的Python版本字符串。
- 函数前使用@server.tool()登记为MCP工具。它类似已经学过的路由登记；客户端以后可以按工具名称调用。
- 函数内写一句三引号用途说明（docstring），说明返回的是工具服务所在进程的Python版本。
- 在if __name__ == "__main__"保护下调用server.run(transport="stdio")，进入工具服务循环。

run是同步的服务启动方法。当前先完成文件，下一段的客户端会负责启动它；单独运行后等待消息属于服务状态，不代表自动执行了get_python_version。

参考：[官方服务端示例](https://py.sdk.modelcontextprotocol.io/get-started/real-host/)。

## 6. 完成条件与下一步

静态审阅依赖版本与导入、工具登记、函数返回及启动入口。当前不增加独立模型请求或测试脚本；接下来编写客户端，通过发现工具和实际调用取得版本字符串，再接入已有Agent注册、校验与执行流程。

本节暂未实现客户端、动态工具注册、远程服务或MCP权限转换，不把服务脚本写好当作Agent接入已完成。
