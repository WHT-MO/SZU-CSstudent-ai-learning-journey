# 进阶第2节：主动停止当前请求

> 2026-10-27。本节两个入口已整体静态通过：HTTP客户端及直接CLI均已接入异步输入、后台任务和主动停止。源码由学员亲写，本次未新增实际运行证据。完成结果见第11节，多会话上一节保持已完成。

## 1. 为什么现在还没有停止入口

改造前，http_client.py的main直接await request_agent，任务结束后才回到下一次input。网络等待期间事件循环可以处理其他异步工作，但main自己停在await处，暂时不会读下一条命令。

如果把请求改成后台Task后仍直接调用input，input等待键盘时又会阻塞事件循环，后台请求也难以继续。因此这一项要同时完成两件事：请求单独作为Task运行；键盘输入放到线程中等待。

架构位置：客户端接收控制命令 → 取消本次HTTP请求Task → 退出请求流 → 服务端检测断连后执行已有任务清理。本节先在http_client.py完成控制入口。

## 2. 输入怎样允许请求继续运行

已有的asyncio.to_thread也能调用input。独立示例：

```python
entry = (await asyncio.to_thread(input, "命令：")).strip()
```

第一个参数input是要在线程中执行的函数，后面的提示字符串传给它。主事件循环在等待键盘输入时仍可处理HTTP收流；await取得用户输入后，外面的strip清除两端空格。

项目中将提示文字换成已有的当前会话提示，结果继续存入prompt。一次只启动一个输入读取，不另外创建输入轮询任务。

依据：[Python 3.12 asyncio.to_thread](https://docs.python.org/3.12/library/asyncio-task.html#asyncio.to_thread)。

## 3. Task就是本次请求的控制对象

在main的while前增加request_task = None，表示启动时还没有请求Task。普通任务创建Task时，把create_task的返回值保存到这个变量。

| 操作 | 含义 |
| --- | --- |
| asyncio.create_task(协程对象) | 安排协程运行，返回可持有的Task对象 |
| request_task.done() | 判断是否已结束，成功、失败或取消都属于结束 |
| request_task.cancel() | 请求取消，使协程有机会处理取消并清理资源 |
| await request_task | 等待该Task收尾；取消通常以CancelledError传回等待方 |

调用cancel后仍要await，等客户端流退出和资源清理完成，再显示停止结果。这里只让请求Task处理取消，main仍继续接收命令。

依据：[Python 3.12 Task取消](https://docs.python.org/3.12/library/asyncio-task.html#asyncio.Task.cancel)。

## 4. 本次动手：两个助手函数和main控制流程

### 4.1 后台请求助手run_request

新增异步函数run_request(prompt, session_id)，内部等待已有request_agent，并传入会话名。

把main里原有的HTTPError显示放进这个助手：后台Task已经独立运行，main创建Task时的try无法捕获之后才发生的请求异常。另捕获普通Exception并显示错误类型和原因，避免解析等普通失败留成无人处理的后台异常。

CancelledError继续向外传播，不把它显示成普通请求失败。后面的取消助手会在等待本次Task时接住它。request_agent内部已有HTTP/SSE收发功能继续被该助手调用。

### 4.2 取消助手cancel_request

新增异步函数cancel_request(task) -> bool。这里的task由main传入request_task：

1. 没有Task，或Task已经done时，返回False，表示当前没有正在进行的请求。
2. 仍在运行时调用task.cancel，然后await task等待它收尾。
3. 只在这次等待处接住asyncio.CancelledError，随后返回True，表示已处理本次停止。

这里的布尔返回值供/stop选择提示文字。函数接收的是Task对象，不是session_id，也不是提示词。

### 4.3 main接收输入并处理命令

保留已有current_session_id，在while前再保存request_task；输入改用第2节的await to_thread(input, 提示文字)，然后strip、partition，沿用/session与空输入分流。

| 输入情形 | 本节行为 |
| --- | --- |
| 普通任务且没有活跃请求 | create_task启动run_request，保存返回的Task，然后继续等键盘输入 |
| 普通任务且已有未结束请求 | 提示已有请求在运行，可先/stop；保留原Task引用 |
| /stop | await cancel_request(request_task)，按布尔结果显示已停止或当前无运行请求，再将request_task置None |
| /exit | await cancel_request(request_task)完成客户端收尾，再退出循环 |
| /session | 沿用查看与切换，选择供下一次普通任务使用 |

创建后台任务时，将当前prompt和current_session_id作为参数传给run_request。已经创建的请求保留它收到的会话名；之后切换会话影响下一次请求。

判断忙碌时，先确认request_task不是None，再看它是否尚未done。已完成的Task引用可以留到下次启动新请求时替换，不需要额外完成回调。后台助手已经处理普通失败，取消由cancel_request等待和接收。

注意普通任务分支是创建Task，不在那里立即await它；/stop和/exit才需要等待取消收尾。这样main才能在请求期间继续接收控制命令。

## 5. 服务端已经具备的清理链路及实际边界

request_agent使用async with client.stream，退出上下文时HTTPX关闭响应。服务端stream_events的finally会取消其持有的Agent Task并等待，run_agent_to_queue的finally移除监听器、放入队列结束标志，退出锁。这些逻辑已存在。

本机依赖源码也已只读核对：当前Uvicorn的HTTP实现提供ASGI 2.3；Starlette在该分支同时等待断连并取消响应发送任务。这支持上述清理链路的静态判断，尚未记录这次/stop的实际运行结果。HTTPX的stream源码也使用finally调用response.aclose。

依据：[HTTPX异步流式响应](https://www.python-httpx.org/async/#streaming-responses)，以及本项目http_api.py和本机安装的starlette/responses.py、uvicorn/protocols/http、httpx/_client.py。

这里停止的是客户端请求及服务端可协作取消的异步流程。已经开始的to_thread工具线程、同步子进程仍可能继续；已写入文件不会回滚。当前取消时保留已保存历史，尚未保存的流式片段不会自动补存。

本节使用/stop和/exit作为明确控制入口。普通input与后台流式print会交错显示，终端排版不是本节完成条件。

## 6. 本节完成条件

第一段由学员完成http_client.py两个助手函数和main控制流程，教员静态核对异步输入、Task引用、失败显示、忙碌判断、停止等待及退出收尾。每个入口只保留一个进行中的任务，不增加排队系统、停止HTTP接口或服务器任务注册表。

### 6.1 直接CLI也接入同一控制方式

学员追问cli.py是否需要调整，明确将两个入口都纳入本节。它们是独立程序：cli.py直接调用run_agent，http_client.py调用request_agent后通过HTTP到达服务端；输入循环和Task引用各自独立。

HTTP客户端第一段通过后，在cli.py完成同样的异步输入、Task持有、/stop取消并等待、/exit收尾。CLI的后台助手可命名run_cli_task(prompt, session_id)，内部await run_agent并传会话名，显示普通异常，让CancelledError继续传播；取消助手接收这个后台Task，逻辑与前文相同。

CLI已有/reset会直接删除历史，因此仅在当前任务已结束或已停止后执行；任务运行中提示先/stop，避免清除后又被该任务保存历史。/session沿用供下一次任务选择会话的语义。

两种入口的控制流程静态正确后，本节完成；不追加独立演示脚本、故障注入、运行截图或付费请求作为门槛。多会话上一节保持已完成状态。

## 7. HTTP客户端首版静态审阅

run_request已等待request_agent并处理HTTP及普通异常，CancelledError分支继续抛出取消；cancel_request已包含空/结束判断和cancel后await；main已正确使用to_thread读取输入，Task和会话变量均在while前初始化，/exit也已等待清理。已有多会话选择及请求字段保持正确。

首版待修三处，记录如下：

1. http_client.py第109行起的普通任务分支尚未检查已有活跃Task。需在create_task前判断request_task不是None且尚未done，忙碌时提示先/stop并回到输入；否则新输入会覆盖旧Task引用，之前的请求仍在运行却不能再由/stop找到。
2. 第103至107行/stop先取消再询问y/n，且这个input是同步阻塞。这里应接收取消助手的布尔返回值，True显示已停止，False显示当前没有运行请求，然后把request_task置None。布尔值表示操作结果，不是询问用户是否批准停止；/stop本身就是停止指令。
3. 第62至72行cancel_request当前只在except CancelledError中返回True；await task若正常收尾会隐式返回None。except只接收取消信号，完成这次等待后在try/except外统一return True，补齐已约定的bool返回路径。

第60行raise asyncio.CancelledError可以传播取消，不将该写法或done()==True等风格差异作为错误。普通异常打印是否含类型不新增为本次门槛。

cli.py目前仍是同步input和直接await run_agent，尚未实现本节第二段。先修以上客户端控制流程，再接CLI；未代改源码、运行/测试或请求模型。

## 8. 第二次审阅：空闲条件与取消边界

/stop已接布尔值显示结果，并在之后清空request_task；同步确认输入已移除。cancel_request的return True已放到try/except之后，位置正确。

第二次回读时剩余两处，记录如下：

1. http_client.py第114行的if负责判断“可以创建任务”，应为request_task is None or request_task.done()。没有任务、已有任务结束，两种情况任一满足即可。当前写and，在None时会继续调用None.done而报错；有Task时又会因左侧为False跳过done判断。or左侧为True时会跳过右侧，正好避免访问None。
2. 第71至72行cancel_request捕获取消后仍raise，会使取消继续传到main，/stop反而结束整个客户端。此处接住后用pass，继续执行后面的return True。run_request里的raise继续保留：后台任务负责报告自己被取消，取消助手负责接住这个预期结果，让交互主循环继续运行。

这两处是当前控制链路的修正，没有新增功能或测试要求。CLI仍待客户端通过后再接。

最新回读：第114行已为None or done，取消助手第72行已接住后pass，第74行返回True；/stop结果提示和清空引用、/exit等待、后台异常处理及异步输入均正确，HTTP客户端这一段静态通过。未运行新停止场景。

## 9. 直接CLI主动停止（已静态通过）

现在将已经写对的控制模式用于cli.py。这个入口直接等待run_agent，不经过HTTP；显示继续由现有listeners接收Agent事件。

### 9.1 两个助手函数

1. 新增异步run_cli_task(prompt, session_id)，内部await run_agent(prompt, session_id=session_id)。普通Exception显示错误，CancelledError继续传播，让取消助手收到任务已取消的结果。
2. 在CLI加入与客户端相同逻辑的cancel_request(task) -> bool：无Task或已done回False；否则cancel后await，接住CancelledError，继续return True。

### 9.2 main控制Task

在现有while前增加agent_task = None，保留当前会话名及监听器登记。输入与客户端一样使用(await asyncio.to_thread(input, 提示文字)).strip()。

| 输入 | 行为 |
| --- | --- |
| 普通任务，当前空闲 | create_task运行run_cli_task，保存返回值到agent_task，继续接收输入 |
| 普通任务，当前忙碌 | 提示先/stop，保留原agent_task |
| /stop | await cancel_request(agent_task)，按布尔值显示结果，再置agent_task为None |
| /exit | 退出while，当前脚本的asyncio.run负责取消并等待剩余Task |
| /reset，当前空闲 | clear_session传当前会话名，清除对应历史 |
| /reset，当前忙碌 | 提示先/stop，不在运行期间删除历史 |
| /session | 沿用查看与切换，选择供下一次任务使用 |

普通任务和/reset都可用同一个空闲条件：agent_task is None or agent_task.done()。任一满足表示没有正在执行的任务；否则分别提示先停止。

普通任务的create_task内部调用run_cli_task(user_prompt, current_session_id)。参数在创建协程时传入，之后的/session切换影响下一次任务。创建后不在该分支立即await；停止分支等待取消收尾，脚本退出由asyncio.run完成收尾。

本次完成cli.py这组改动后静态回读，即可完成本节；不重复验收已通过的HTTP客户端，不新增运行或测试要求。

## 10. CLI首版静态审阅

CLI首版已加入run_cli_task和正确的取消助手，main的异步输入、Task引用、空闲判断、/stop显示及清空引用均已正确。该次待修两处，记录如下：

1. cli.py第37行await run_agent(prompt, session_id)误用位置参数。run_agent的参数顺序是user_prompt、max_turns、session_id，因此字符串被当作max_turns，真实会话名仍使用default；遇工具调用的轮数比较还会造成int与str比较错误。改为显式传session_id=session_id。
2. 第70至71行/reset仍直接清除历史，需复用普通任务分支的空闲条件agent_task is None or agent_task.done()：空闲时清除当前会话，忙碌时提示先/stop，避免正在运行的任务随后保存历史。

/exit当前直接break的写法在此脚本入口可接受：末尾asyncio.run(main())关闭运行器时，会取消并等待剩余Task。已核对[CPython 3.12 runners.py](https://github.com/python/cpython/blob/3.12/Lib/asyncio/runners.py)中的Runner.close及_cancel_all_tasks，不把“没有手动调用取消助手”误报为此入口完全不清理。

只修上述两处后完成本节静态审阅，不增加格式要求、测试或模型请求。

最新回读：第37行已显式传session_id=session_id；第71行/reset已使用None or done空闲条件，忙碌时提示先stop。取消助手仍保留cancel与await，CLI整体静态通过。

## 11. 本节完成结果

| 行为 | 已实现并静态核对的结果 |
| --- | --- |
| 等待键盘输入 | 两个入口均用to_thread等待input，事件循环可继续处理后台任务 |
| 普通任务 | 空闲时创建并保存Task，已有活跃任务时提示先stop，保留原引用 |
| /stop | 主动cancel并await本入口当前Task，接住取消结果、显示状态，继续输入 |
| /exit | HTTP客户端显式等待取消助手；直接CLI由脚本asyncio.run退出时清理剩余Task |
| /session | 选择下一次任务的会话；已创建Task保留其收到的会话名 |
| CLI /reset | 仅空闲时清除当前会话，忙碌时提示先stop |
| 后台异常 | 助手显示普通失败；后台任务传播取消，取消控制助手接住预期取消 |

此前学员追问task.cancel是否必要，已说明：/stop后事件循环继续运行，需要主动取消选中Task；asyncio.run的自动清理发生在程序退出时，不能替代运行中的停止命令。

本节实现完成，没有待改源码或额外必做项。本次依据为静态审阅，未新增运行、测试或模型请求，也未上传GitHub。线程工具或同步子进程仍可能继续，已写文件不回滚；终端输入与流式输出仍可能交错显示，实际边界见第5节。
