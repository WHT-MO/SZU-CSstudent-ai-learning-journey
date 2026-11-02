# 进阶第9节：MCP工具服务

> 2026-10-30。本节服务端与独立客户端已实际跑通：发现工具及说明/参数格式，调用成功并返回Python 3.12.10。本节演示完成；工具接入Agent进入第10节，不能将独立客户端成功当作Agent已接入。

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

本节采用官方Python SDK 2.x，本项目约定Python 3.12+，依赖限制在2.x：

```powershell
# 在D:\code\dsh\python-course执行
.\.venv\Scripts\python.exe -m pip install "mcp>=2,<3"
```

当前写法使用from mcp.server import MCPServer。2.x的新项目依照本节来源；网上使用FastMCP及ClientSession初始化的旧版片段应先核对版本，不混入本节。

当前实际已安装mcp 2.3.0。若终端位于code/agent_v1，前面的相对解释器路径会去该目录寻找.venv；项目虚拟环境实际在仓库根目录。可使用完整解释器路径执行命令，或先回项目根目录。后续客户端使用sys.executable及相对脚本文件位置计算服务端路径。

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

本节尚未接动态工具注册、远程服务或MCP权限转换，不把服务脚本写好当作Agent接入已完成。当前服务端回读与客户端任务如下。

## 7. 服务端回读与工具说明

2026-10-30回读demo_mcp_server.py：MCPServer导入、course-tools实例、@server.tool()、返回sys.version及入口保护内stdio启动均正确。函数定义旁的#注释是源码注释，不会成为工具description。

函数体第一条语句、return之前的三引号用途说明已补齐。SDK 2.3.0的Tool.from_function读取显式description或fn.__doc__，以它生成工具说明；源码注释不参与这一步。服务端注册、返回及入口现已静态通过，说明随后可由客户端发现，再由Agent转交模型。

## 8. 当前动手：demo_mcp_client.py

目标是看到远端工具目录，并通过MCP调用取得版本字符串。新建code/agent_v1/demo_mcp_client.py，使用asyncio、sys、Path，以及from mcp import Client, StdioServerParameters；编写异步main并保留通常的脚本入口。

### 8.1 描述如何启动服务端

在main里用Path(__file__).resolve().parent / "demo_mcp_server.py"确定服务脚本路径。__file__表示客户端脚本本身的位置，不依赖终端当前目录；这能避免刚才的相对路径问题。

StdioServerParameters的command填sys.executable，args填含服务脚本路径字符串的列表。command是要运行的程序，args是传给它的命令行参数；合起来相当于“当前Python解释器 服务脚本.py”。这个对象只是启动配置，构造时不启动进程。

sys.executable来自当前运行客户端的Python，因此从项目虚拟环境启动客户端时，服务端也使用该解释器。

### 8.2 建立连接并管理进程生命周期

在main里用async with Client(server_params) as client进入连接，server_params是前一步创建的启动配置。进入上下文时SDK启动服务子进程并建立MCP通信；退出时SDK关闭连接并清理子进程。服务端无需另开终端手动启动。

### 8.3 发现工具

在上下文内await client.list_tools()，把返回对象保存到tools_result。当前安装版返回ListToolsResult，不是裸列表；遍历它的.tools。

每个tool对象读取.name、.description、.input_schema，打印工具名称、用途及参数格式。属性用点号访问，SDK已经解析协议消息。这里应能看到get_python_version，以及前面补充的docstring说明。

当前回读：学员已写启动路径、StdioServerParameters和async with Client，并把list_tools返回值命名为tool_result。第16行写成for name, description, input_schema in tool_result.tools，混淆了“一个对象有三个属性”和“列表元素是三个值组成的一组”。本轮先停在目录读取：一次取一个工具对象，再读它的属性。此前read_file里的file_args.path也是同样的属性访问。

工具目录的层次是：tool_result为响应对象，tool_result.tools为列表，列表每项为一个工具对象；.name、.description和.input_schema属于该工具对象。循环变量可以命名为tool，每次循环它代表列表中的一个元素。末尾尚未完成的tools构造当前不需要，目标是打印SDK已经返回的数据。

server_params只是启动命令配置；进入async with Client时SDK启动服务并连接；await list_tools只是询问有哪些工具，没有执行get_python_version。文件需保留常用的asyncio.run(main())入口。本轮先完成并理解目录显示，下一小步再接8.4调用，不把复制了配置代码当作已经掌握。

最新回读：学员已改为for tool in tool_result.tools并分别打印三个属性，main入口也已补齐，目录读取代码静态正确。学员已主动接8.4工具调用，保留该进展，当前修正内容块读取。

### 8.4 调用工具并读取文本结果

在同一个上下文内await client.call_tool("get_python_version", {})，保存到call_result。第一个参数是服务端工具名，第二个是工具参数字典；当前工具无入参，所以传空字典。

CallToolResult有.is_error和.content等字段。显示.is_error；遍历.content，对于type为text的内容块打印.text。content是内容块列表，不是单个字符串；is_error是SDK工具结果的错误标记。本段只显示该次工具调用结果，连接故障等异常仍可能以异常形式反馈。

首版第24行写成content.type("text").text。type在这里是字符串属性，括号会将字符串当函数调用并产生TypeError。循环内应先以content.type == "text"判断，再打印content.text。call_tool参数、is_error读取及外层遍历正确，无需重写。False表示工具结果未报告错误。

### 8.5 运行客户端

写好后，从任意终端目录使用项目解释器运行客户端：

```powershell
D:\code\dsh\python-course\.venv\Scripts\python.exe D:\code\dsh\python-course\code\agent_v1\demo_mcp_client.py
```

本次调用完全在本机客户端与服务端之间发生，不请求DeepSeek。最新源码已将内容块读取改为字符串比较后读取text，学员也已运行客户端并提供成功截图，形成通信链路的实际证据。不另加测试脚本或模型请求门槛，之后再接Agent注册与执行。

接口核对来源：本地MCP 2.3.0的mcp/client/client.py（Client、list_tools、call_tool）、mcp/client/stdio.py（启动参数）、mcp_types/_types.py（返回字段）及服务端tools/base.py（docstring）。

## 9. 实际运行结果与完成范围

2026-10-30学员截图显示get_python_version、docstring说明、type=object且properties为空的参数schema、is_error=False及Python 3.12.10版本字符串。无参数工具的properties为空符合定义。

结合当前源码使用StdioServerParameters及Client，说明独立客户端已能启动stdio服务、发现工具并通过MCP调用取得结果。没有请求模型，也未修改Agent注册及执行流程；不把这份证据扩展为模型已能选用MCP工具或所有异常路径都已测试。

下一步见[MCP工具接入Agent](Agent进阶10_MCP工具接入Agent.md)，先统一工具说明格式，再接执行桥接。本节无剩余必做项，不重复运行验收。
