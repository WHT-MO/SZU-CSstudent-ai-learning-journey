# 进阶第10节：MCP工具接入Agent

> 2026-10-30开始，2026-11-03完成。本地stdio MCP工具经模型选择、Agent执行与结果回填已实际成功，证据见第13节。源码由学员亲写；本节完成，不追加局部验证或新练习。

## 1. 为什么还需要接入

第9节的客户端代码直接按名称调用get_python_version。完整Agent接入还需要把工具说明给模型，接住模型提出的工具调用，再经MCP执行并回填结果。

当前build_tools_payload从AgentTool读取name、description、parameters；MCP目录里的工具对象则有name、description、input_schema。现有process_tool_call还会从本地tool_arg_models、tool_functions查找校验器和函数，execute_validated_tool默认在线程中调用同步函数。

因此，字段转换是第一段。若只向模型提供额外说明，却没有登记对应的执行与校验路径，现有Agent会把调用判成未知工具。后续还要接异步调用和连接生命周期，不通过直接追加全局tool_specs来假装已经完成接入。

## 2. 当前目标：统一工具说明

适配在这里就是把外部SDK提供的数据转换成Agent已经使用的格式。统一后，后面的模型请求构造可以复用现有AgentTool。

| MCP工具对象属性 | AgentTool字段 | 处理 |
| --- | --- | --- |
| name | name | 保留工具名称 |
| description | description | 缺少说明时使用空字符串 |
| input_schema | parameters | 直接使用已有参数schema字典 |

SDK允许description缺失，而AgentTool当前要求str，所以这里需要补齐类型。input_schema已经是参数JSON Schema，无需再调用model_json_schema；对SDK工具对象调用该方法会描述工具对象本身，含义不同。

## 3. 当前动手：mcp_adapter.py

在code/agent_v1新建mcp_adapter.py，从tool_schemas导入AgentTool，定义普通函数convert_mcp_tools(mcp_tools) -> list[AgentTool]。

输入mcp_tools是目录响应里的工具对象列表，即现有tool_result.tools，不是整份响应。遍历每个对象，按上表构造一个AgentTool，收集到新列表并返回。已有tool_registry里构造AgentTool的方式可作参考；description可使用tool.description or ""。

函数只做数据转换，不启动进程或发送请求。配置字段和SDK返回值作为输入，转换结果通过返回值交给调用方，当前不修改本地全局注册表。

## 4. 演示客户端使用转换结果

demo_mcp_client导入convert_mcp_tools，在list_tools取得tool_result后，用convert_mcp_tools(tool_result.tools)得到agent_tools。把目录显示改为遍历agent_tools，分别显示.name、.description、.parameters。

工具调用仍通过当前Client的call_tool完成。演示里使用转换结果只证明数据已按内部格式组织，不表示Agent已经登记它。

## 5. 调用封装：异步调用与文字结果

当前execute_validated_tool取得工具结果后，把字符串交给make_tool_result，再限制字节数并构造role为tool的消息。MCP的call_tool返回CallToolResult对象，含content内容块和is_error标记，需要先转成当前执行器可使用的文字结果。

在mcp_adapter.py新增异步函数call_mcp_tool(client, tool_name: str, arguments: dict) -> str。三个输入分别为已连接的Client、工具名称、参数字典。client由外层async with Client(server_params) as client创建，调用方传入；本函数复用该连接。

按以下顺序实现：

1. await client.call_tool(tool_name, arguments)，保存返回对象。
2. 遍历结果的content，把type为text的块的text收集起来，用换行连接成tool_content。当前接入范围是文字结果工具。
3. 若is_error为True，用RuntimeError抛出失败，错误信息包含tool_content；否则返回tool_content。函数负责返回数据，显示由调用方print。

SDK的is_error是返回对象中的错误标记，并不自动触发Python的except。这里主动把工具失败转换成异常，是为复用现有执行器的except分支和status=error，属于本项目的适配选择。连接和协议异常照常向调用方传播；取消也不在此处吞掉。

demo_mcp_client同时导入convert_mcp_tools与call_mcp_tool，在现有Client上下文内部，把直接call_tool、打印is_error、遍历并打印content的那一段替换为await call_mcp_tool(client, "get_python_version", {})并print返回文字。工具目录显示保留。此处接线复用已经成功的调用，不额外安排测试脚本或模型请求。

## 6. 本段完成条件

说明转换：静态确认输入列表层次、三字段映射、description缺失处理、返回新的AgentTool列表及演示调用位置。此部分已完成。

调用封装：静态确认复用已打开Client、异步等待call_tool、只收集文字并拼接、工具失败保留原因并抛出、成功返回字符串、demo在连接上下文中await并打印。此部分已静态通过，小规模封装不追加独立测试或模型请求，也不重做已经成功的stdio通信演示。

### 当前回读（2026-11-02）

mcp_adapter.convert_mcp_tools及demo使用已静态通过。call_mcp_tool已在for前创建parts，在循环中收集content.text，在循环后join、检查is_error并返回；原两处错误已修正。demo仍在Client上下文中await新函数并打印，调用封装静态通过。未据此声称Agent已接入，也未代改或执行学生源码。

## 7. 执行器支持普通函数和异步函数

### 先分清工具本体与调用入口

现有tools.py中的read_file、write_file、list_files、edit_file、search_file、run_python全部使用普通def。异步的是外层execute_validated_tool：它await to_thread返回的协程，把同步工作交给工作线程；工具本体仍然同步。之前gather等待的也是这层异步包装，同步函数可以在线程中并发执行，同步与整批串行是不同层面的判断。

MCP这次增加的是异步客户端入口call_mcp_tool，它等待与服务进程的通信。服务端get_python_version仍使用普通def。客户端等待方式与服务器函数的实现方式可以不同：本地路径为异步执行器→工作线程→同步read_file；MCP路径为异步客户端→通信→服务进程执行get_python_version→返回结果。

同步函数适合直接调用现有同步API，例如Path.read_text、write_text和subprocess.run，也适合立即取sys.version的短逻辑。仅把def改成async def不会把内部read_text之类的阻塞操作变成异步I/O；如果在事件循环中直接执行，等待期间仍会占住事件循环。当前按类型选择的是Agent手里要调用的入口：本地同步函数走线程，MCP异步入口直接等待，不依据服务端内部函数类型做这个选择。

### 当前修改

现有execute_validated_tool把所有tool_function交给asyncio.to_thread。普通同步文件工具适合这条路径；async def函数被线程调用时只会生成协程对象，不会在该线程内自动等待其完成，外层就会把协程对象误当工具结果。

先让执行器按函数类型选择执行方式，再把MCP连接和工具名称接入。当前改动位置为agent_runner.py的execute_validated_tool中try取得tool_content的那一段。

引入标准库inspect。inspect.iscoroutinefunction(tool_function)判断传入函数是否为协程函数；对于当前使用的普通def和async def，分别返回False和True。这里检查函数对象本身，不提前调用它。见[Python 3.12官方说明](https://docs.python.org/3.12/library/inspect.html#inspect.iscoroutinefunction)。

| 工具函数类型 | 如何取得待等待的协程对象tool_coroutine |
| --- | --- |
| async def | 调用tool_function(validated_args) |
| 普通def | 调用asyncio.to_thread(tool_function, validated_args) |

两个分支都只取得协程对象，随后统一用await asyncio.wait_for(tool_coroutine, timeout=10)取得tool_content，再设置status为success。选择分支时先不await，确保异步调用也受这层超时控制。to_thread本身返回可等待的协程，见[官方说明](https://docs.python.org/3.12/library/asyncio-task.html#asyncio.to_thread)。

本次沿用后面的异常、取消、事件通知和make_tool_result。MCP连接及工具名称随后接入；call_mcp_tool当前需要三个参数，还不能直接充当只接收validated_args的tool_function。静态核对分支、协程变量、统一超时及缩进即可，不追加测试或模型请求。

当前执行器回读（2026-11-02）：else已补齐，to_thread赋值已缩进到else内；异步直接调用与同步线程路径互斥，随后统一wait_for，静态通过。

两种表达式的共同点是返回一个可等待的协程，执行方式不同。async def函数被调用时自己生成协程，等待后由事件循环执行；普通def直接调用会立即在当前线程执行，to_thread为它生成一层协程，等待这层协程时才在线程调用原函数并取得结果。if与else中的tool_function实际类型不同，不能据相同变量名把两条表达式当作任意可互换的写法。外层wait_for只需接收可等待对象，所以两条路径能在此汇合；异步直接调用不因此获得线程能力。

## 8. 当前动手：把MCP调用整理为单参数入口

### 已补齐的前置：单个入口（2026-11-02）

学员尚未改动适配器或demo，并表示不理解；上轮把partial和字典构造同时作为实现任务，前置跨度过大。先用当前get_python_version说明三个参数如何传递，再在demo只接单个入口。以下原批量构造目标保留，当前暂不要求先写build_mcp_functions。

执行器将来只调用tool_function(validated_args)，而MCP辅助函数的调用形态为call_mcp_tool(client, "get_python_version", arguments)。前两个值在连接和工具登记时已确定，模型每次只需提供最后的arguments。

version_tool = partial(call_mcp_tool, client, "get_python_version")会保存原函数及两个已知参数，得到一个可调用入口；此时没有工具结果，也没有发送请求。之后await version_tool({})相当于await call_mcp_tool(client, "get_python_version", {})。参数未消失，前两个由入口保存，调用时补上第三个。version_tool是入口的变量名，可以自选，不是SDK提供的新类型名称。

当前只由学员在demo_mcp_client导入partial，并在原Client上下文里创建上述单个入口，用await version_tool({})替换原直接调用，打印保留。暂不建字典或新增函数。之后字典只负责按get_python_version名称保存这个入口，批量构造函数会对目录每项重复这一动作；无须引入另一套调用机制。此处先解释与写接线，不新增运行或理解确认门槛，原完整Agent接入目标继续保留。

单入口回读（2026-11-02）：demo已导入partial，第26行预填call_mcp_tool/client/get_python_version正确，位置在Client上下文内。第27行已改为tool_content = await version_tool({})，再print(tool_content)，单入口接线静态通过；不据此声称独立掌握或新增运行证据。当前恢复批量构造任务，不追加验证。

### 当前动手：批量构造

现有执行器只传validated_args，而call_mcp_tool需要client、tool_name、arguments三个参数。client在连接打开时确定，tool_name在登记目录中的每项工具时确定，arguments才随每次模型调用变化。预先保存前两个参数，可以继续沿用执行器只传本次工具参数的接口。

标准库functools.partial负责预填一部分参数，返回一个新的调用入口；创建它时不执行原函数，之后传入剩余参数才调用原函数。这个机制也适用于异步函数，调用后仍需await；Python3.12的inspect.iscoroutinefunction能识别包住异步函数的partial对象。参见[partial官方说明](https://docs.python.org/3.12/library/functools.html#functools.partial)与[inspect官方说明](https://docs.python.org/3.12/library/inspect.html#inspect.iscoroutinefunction)。

概念例子与当前作业分开：普通add(a, b)返回a+b，add_ten = partial(add, 10)只保存函数和第一个参数；add_ten(3)才相当于add(10, 3)。新入口可以保存在字典中，再按名称取出调用。

学员在mcp_adapter.py导入partial，并新增普通函数build_mcp_functions(client, agent_tools) -> dict。agent_tools是此前convert_mcp_tools返回的AgentTool列表。函数建立新字典，遍历列表，以tool.name为键；值是用partial预填call_mcp_tool的client与tool.name后得到的调用入口，最后返回字典。这里只组装字典和入口，不进行通信，因此build_mcp_functions使用普通def。

字典值保存可调用入口，不保存调用结果或已经创建的协程。登记时不传arguments、不await，也不修改本地全局tool_functions；连接由调用方管理，入口使用期间Client需要保持打开。

字典的单项可先理解为mcp_functions["get_python_version"] = version_tool，键为名称，值为前一步已经会创建的入口。批量函数会为agent_tools里的每项做同样的登记，工具名称取当前tool.name。

demo_mcp_client导入build_mcp_functions，在原Client上下文中取得agent_tools后，调用该函数建立mcp_functions。替换手动创建version_tool到打印的原三行：先mcp_functions = build_mcp_functions(client, agent_tools)，再tool_function = mcp_functions["get_python_version"]，接着tool_content = await tool_function({})并print(tool_content)。先取入口再调用，明确字典查找和函数执行是两个动作。目录显示保留。此处只是现有调用的接线调整，静态检查即可，不额外运行测试或模型请求。

完成条件：普通函数返回名称到入口的字典，partial保存正确的函数和前两个参数，循环逐项使用对应工具名称，demo在连接上下文中按名称取出并await调用。后续才把此映射交给Agent的工具处理流程。

批量入口回读（2026-11-02）：重复AgentTool构造已删除，build_mcp_functions循环内只按名称登记partial，return位于for外；demo建立映射、按名取函数、await传{}及打印均正确。批量入口和demo接线静态通过，不追加验证，也不将此当作完整Agent调用成功。

## 9. 工具说明构造函数接收列表

build_tools_payload当前直接遍历模块级tool_specs。MCP转换结果同样是AgentTool列表，因此把输入列表交给调用方选择，即可让同一个格式转换函数服务本地工具和MCP工具，也便于为本次连接组装对应的工具集。

学员在agent_runner.py完成两处相连的改动：给build_tools_payload增加参数available_tools，使其列表推导式遍历available_tools；在run_agent原调用处显式传入现有tool_specs，即tools = build_tools_payload(tool_specs)。函数仍返回模型请求使用的字典列表，参数是AgentTool列表，两者不要混淆。

此步先完成显式输入接线。MCP说明与本地说明的合并安排在对应执行路径接齐后，确保给模型的工具目录能对应到可执行入口。两处静态核对即可，不安排独立测试、模型请求或重复MCP运行。

回读（2026-11-02）：函数已接收并遍历传入列表，run_agent显式传tool_specs，静态通过。学员实际变量拼写为avaliable_tools，声明与使用一致，当前不影响行为，不设为新的修改门槛。

## 10. 工具处理函数识别MCP入口

当前process_tool_call解析模型arguments后只查本地tool_arg_models/tool_functions，因此MCP名称会被当作未知工具。前面build_mcp_functions返回的字典是名称到已预填Client/名称的入口，后续由连接入口交给run_agent，再由run_agent传给process_tool_call；当前先接这条传递和分流路径。

1. run_agent末尾增加可选参数mcp_functions=None；函数体开始处在None时创建空字典，供尚未传MCP的现有调用使用。不要使用共享的可变字典默认值。
2. process_tool_call在valid_tools之后、before_tool默认参数之前增加必传参数mcp_functions；run_agent现有调用中以mcp_functions=mcp_functions显式传入。左边是被调函数参数，右边是本次run_agent收到并准备好的映射。
3. JSON解析成功后，以tool_name是否在mcp_functions中分支。MCP分支从映射取tool_function，确认arguments为dict，否则用make_tool_result写入tool_results[index]并return；成功时validated_args取arguments。else内放原本地工具查找、未知工具返回和Pydantic校验那一段。两分支完成后共同进入原before_tool检查及valid_tools.append，不在MCP分支提前执行工具或跳过权限。

本地分支的validated_args是参数模型实例；MCP分支是准备交给服务端的参数字典。此处仅确认JSON对象结构，MCP具体字段由服务端按工具定义校验。已核对本项目安装SDK的tools/base.py，调用工具前会validate_arguments；MCP规范也要求服务端验证工具输入。不能将此讲成MCP不需要校验。参见[官方工具规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#security-considerations)。

本次尚未创建Agent使用的MCP连接，也未合并模型工具目录。静态确认传参链、两路变量和共享权限检查即可，不新建测试、运行源码或请求模型。

参数分流回读（2026-11-02）：run_agent的默认值归一化、process签名及caller传递正确。缺失字段检查和JSON解析已移到两路分支之前；MCP分支从映射取入口、检查arguments为dict、失败填结果并return、成功赋validated_args均正确；本地Pydantic分支及共享before_tool/收集也正确，静态通过。学员曾混淆JSON字符串解析与服务端字段校验，已用合法JSON但字段类型错误的例子区分，不能据讲解直接判掌握。

## 11. 当前动手：接齐目录、调度和连接内运行

前面的两份数据分别用于不同阶段：MCP的AgentTool列表交给模型请求目录，mcp_functions映射供执行阶段按名称查找。两者由同一连接发现并构造，作为本次run_agent输入传入；连接需要覆盖整个await run_agent期间。

### 11.1 run_agent组装本次工具说明

在run_agent参数末尾增加mcp_tools=None；与mcp_functions的None处理放在一起，为None时创建空列表。此时mcp_tools就是demo中的agent_tools列表，mcp_functions是对应执行入口字典。

遍历传入MCP工具说明，确认每个tool.name没有出现在本地tool_functions中，且能在mcp_functions中找到执行入口；不满足时raise ValueError并写清原因。这是目录与执行表对应关系的配置检查，避免同名工具指向不明确或给模型提供无法执行的名称。

创建本次available_tools，内容为本地tool_specs加mcp_tools，再交给build_tools_payload。使用列表相加创建新列表，工具集合属于本次调用，不修改全局tool_specs。

### 11.2 本次串行工具集合

当前尚未为外部工具逐项分类读写能力，本项目先将MCP入口纳入已有整批串行策略；这是项目选择，不是MCP协议限制。

在run_agent构造serial_functions，内容为现有serial_tool_functions加list(mcp_functions.values())。execute_tool_batch增加必传参数serial_functions，内部判断item[2]是否在这个传入集合中，run_agent调用时把本次列表一并传入。保留原有含串行工具则整批顺序、否则gather并发及按输入顺序回填的逻辑。不要向全局serial_tool_functions追加绑定连接的入口。

### 11.3 demo在打开的连接里运行Agent

demo_mcp_client导入run_agent，保留现有Client上下文、工具发现、说明转换和build_mcp_functions。在mcp_functions建立后，用await run_agent替换原来手动取get_python_version入口并调用的那一段。任务文字为“请调用get_python_version，告诉我工具服务进程的Python版本。”，session_id使用mcp_demo，mcp_tools传agent_tools，mcp_functions传本次映射。

按已有运行结果约定显示：completed为True时显示message的content，否则显示reason。Agent调用及结果显示放在原async with Client内；await run_agent完成后才离开上下文并关闭MCP连接/子进程。run_agent内部httpx.AsyncClient是模型HTTP连接，外部MCP Client是工具连接，二者职责不同。

此处是现有demo的新行为，不新增测试脚本或额外入口。原CLI/HTTP没有传MCP时仍走默认空集合；本节不扩展这些入口或多服务器配置。

## 12. 本段完成条件与运行证据

最后接线回读（2026-11-02）：三处均已修正：mcp_tools为None时归一化为[]；逐项以tool.name检查本地重名和执行入口；execute_tool_batch签名及caller均已传serial_functions，内部使用一致。本次目录、串行集合、demo的Agent调用/结果显示和Client作用域静态通过。当时只读确认sessions/session_mcp_demo.json尚不存在，尚无新调用链运行证据；随后结果见第13节。

学员先亲写上述接线，静态回读确认目录/执行入口对应、每次运行的列表、调度传参、demo结果处理及连接作用域。此前未证明的实际新行为，是模型选择MCP工具后经Agent执行并回填结果；接线静态通过后由学员运行现有demo一次，结合输出与mcp_demo会话存档确认工具名称及对应tool结果，不以最终回答单独推定调用成功。不追加故障注入、独立测试脚本或重复的纯MCP手动调用。教员不代跑模型。

当前运行命令（PowerShell，可从任意目录执行）：

```powershell
D:\code\dsh\python-course\.venv\Scripts\python.exe D:\code\dsh\python-course\code\agent_v1\demo_mcp_client.py
```

正常情况下demo先显示工具目录，Agent完成后显示最终答案；当前没有登记终端流式事件监听器。会话存档路径由session_store确认，为code/agent_v1/sessions/session_mcp_demo.json。运行后由教员读取相关调用/结果核实，不要求学员另写日志或验证脚本。

## 13. 实际运行结果：本节完成（2026-11-03）

学员运行既有demo并提供终端截图，最终回答给出工具服务进程的Python版本3.12.10。只读核对sessions/session_mcp_demo.json，文件保存时间为2026-11-03 00:02:07，共5条消息：system、user、assistant工具调用、tool结果、assistant最终回答。

模型发起get_python_version，arguments为{}，调用编号call_00_ET_QHmF8cuxBGMR0XKsxIhH1423；下一条tool消息使用相同编号，返回3.12.10及完整sys.version构建信息，随后assistant最终回答与截图一致。结合已审阅的真实Client执行路径，确认本轮模型提出调用、Agent经MCP执行、结果回填、模型生成答复的链路实际成功。

第10节完成。已验证范围是本地stdio服务、文字结果工具和demo中的Agent入口；本节没有扩展CLI/HTTP的MCP连接配置。其他工具参数、并发、失败与取消情形没有据本次单个成功案例追加运行结论，也不将其设为本节新的验收门槛。教员只读核实存档并维护文档，未代写或运行源码、请求模型或Git上传。
