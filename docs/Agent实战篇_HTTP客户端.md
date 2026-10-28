# 应用阶段：用Python读取自己的Agent服务

> 当前进展：2026-10-23。基础文字与工具进度已有运行截图；后续审阅任务也实际展示工具回传、未取得完整回答提示及再次输入，学员确认客户端已接通并收尾。HTTP异常捕获依据静态审阅。下一项为[统一工具注册](Agent第05章_统一工具注册.md)。

## 1. 本节目标

调用自己已运行的POST /chat，把原始data事件读成连续文字，并取得agent_done中的完整消息。

```text
客户端发送prompt → 本机HTTP服务 → 既有run_agent
客户端显示文字 ← 读取并解析SSE ← 模型与工具事件
```

服务端继续负责模型密钥、工具、历史和共享锁；客户端只负责发送用户输入与读取显示。使用已有HTTPX，与agent_runner.py中的stream_message复用同一种流式读取方式。

读取方式可以复用，收发的接口格式需要转换。agent_runner向DeepSeek发送model/messages/tools并解析choices/delta；本节http_client向本机/chat发送prompt，并读取已经整理好的type/text/result事件。真正的工具调用解析、执行与结果回填继续由服务端run_agent完成。

## 2. 本次实际用到的已有调用

| 写法 | 本次作用 |
| --- | --- |
| httpx.AsyncClient(timeout=60) | 创建HTTP客户端，为等待响应数据留出时间；此值不是整项任务的总时限 |
| client.stream("POST", url, json=...) | 发送JSON并保持响应可逐段读取；用async with进入 |
| response.raise_for_status() | 将HTTP失败状态作为异常报告 |
| response.aiter_lines() | 用async for逐行取得服务返回的文字 |
| json.loads(...) | 将一条事件的JSON文字转成Python字典 |

client来自AsyncClient上下文的as client；response来自stream上下文的as response；line来自async for；event由json.loads得到。queue与Task都留在服务端，当前客户端读取HTTP响应即可。

### HTTP请求的正文、头与stream参数

body是请求正文，携带实际任务，本次为{"prompt": prompt}。request_body只是用来保存这个字典的变量名。headers是请求头，用于说明数据格式等附加信息；本次Content-Type: application/json表示发出去的正文为JSON。响应由本机服务返回SSE，因此请求格式与响应格式分别是JSON和text/event-stream。

用户明确询问stream的填写方式后，给出本次请求部分的具体写法：

```python
request_body = {"prompt": prompt}
headers = {"Content-Type": "application/json"}

async with httpx.AsyncClient(timeout=60) as client:
    async with client.stream(
        method="POST",
        url="http://127.0.0.1:8000/chat",
        headers=headers,
        json=request_body,
    ) as response:
        response.raise_for_status()
        # 逐行读取和事件处理接在这个缩进范围内
```

示例显式写出headers便于理解关系；HTTPX使用json参数时已经会自动设置JSON的Content-Type。client.stream表示流式读取响应；本机/chat已经约定返回事件流。当前本机接口没有鉴权步骤，DeepSeek的Authorization仍由服务端模型请求代码负责。

## 3. 事件读取与显示

当前服务每条事件使用一行data:加JSON，消息之间为空行。客户端只处理data:开头的行，取其后的JSON并解析为event字典。本项目此处不泛化多行SSE解析；约定与已经实现的输出一致。

| event["type"] | 当前处理 |
| --- | --- |
| text_delta | 将event["text"]追加打印，使用end=""和flush=True |
| agent_done | 换行，并返回event["result"]，保留完整消息供调用者使用 |
| agent_error | 显示event["message"]，返回None |

当前必做是上面三项。其余已存在事件的职责明确如下，显示进度可选；忽略它们不影响服务端执行工具：

| event["type"] | 可选显示 |
| --- | --- |
| tool_start | 显示event["tool_call_id"]，提示工具开始 |
| tool_end | 显示同一tool_call_id及event["status"]，提示工具结果状态 |
| model_response_end | 显示event["usage"]，表示一次模型响应结束 |

本机当前tool_start/tool_end没有工具参数或完整工具结果，客户端按实际字段显示。服务端执行工具并把结果交回模型后，可能继续产生文字或工具事件；agent_done才是整项正常结束。agent_done.result中的完整回答已经通过片段显示，保留为返回值即可。

## 4. 当前动手

在已创建的code/agent_v1/http_client.py中定义异步函数request_agent(prompt: str) -> dict | None，向http://127.0.0.1:8000/chat提交{"prompt": prompt}，按第2、3节读取、显示与返回结果。prompt来自函数参数；启动入口用input取得用户文字再传入。沿用已有asyncio、json、httpx。

增加受if __name__ == "__main__"保护的启动入口，读取一次用户输入，通过asyncio.run调用该函数。当前安排一次任务的完整客户端，不新增连续输入、远端部署或会话管理功能。先亲写这一项，源码审阅后直接进入实际使用。

2026-10-23继续时先复原整条数据流：用户文字进入prompt参数，HTTPX发送JSON；response.aiter_lines逐行提供line，去除data:后用json.loads得到event；显示文字片段并在agent_done处返回完整消息。比如data: {"type": "notice", "text": "已连接"}去掉前5个字符及首尾空白后，是合法JSON文字，解析后才能按字典字段读取。客户端调用的是本机/chat，本次响应直接使用type/text/result字段。这个功能作为一项完整动手任务，不再拆成多轮纯讲解确认。

最新回读与补讲：首稿复制了整个DeepSeek stream_message，包括API key、model/tools/messages、choices/delta和工具参数拼接，还没有完成本机接口适配。学员指出body、headers、stream结构和工具事件处理都未讲清；当前先按第2节具体代码和第3节必做/可选分工补齐前置，再修改草稿，不把一批随复制引入的未定义变量拆成重复审阅任务。

## 5. 本机客户端首版回读

请求正文、Content-Type、客户端创建、stream参数及text_delta/agent_done/agent_error分支均已写出。学员在本轮继续修改时，已把直接赋值aiter_lines改为async for；最新源码按这个已修版本审阅，不再重复要求加循环。

当前只修三组实际问题：

1. URL写成http//127.0.0.1:8000/chat，协议名后缺少冒号，改为http://127.0.0.1:8000/chat。
2. 每条SSE事件后都有空行，当前直接json.loads会在空行处失败。循环内先判断是否以data:开头，不是就continue，再切片解析。这个判断覆盖正常响应中的分隔空行，不是额外异常用例。
3. 启动判断应使用__name__ == "__main__"，当前误写"__file__"导致直接运行时不进入；request_agent需要prompt参数，启动处读取一次input，再将文字传入request_agent(prompt)交给asyncio.run。

教员仅静态审阅及更新讲义，未代改源码、运行客户端或请求模型。上述修正后再直接使用现有服务，不新建验证脚本。

最新回读：URL、data:过滤、__main__与input均已修正。最后一行仍为asyncio.run(request_agent())，缺少函数必需的prompt参数；改为asyncio.run(request_agent(prompt))。输入保存到同名变量不会自动传入函数，调用时需显式给参数。其余主体静态通过，这一行修完直接实际使用，不再为一行修改设单独确认。

## 6. 使用Python客户端（已完成）

修正最后一行后，启动已有单worker服务并保持其终端运行：

```powershell
& "D:\code\dsh\python-course\.venv\Scripts\python.exe" -m uvicorn http_api:app --app-dir "D:\code\dsh\python-course\code\agent_v1" --host 127.0.0.1 --port 8000 --workers 1
```

在另一个PowerShell运行客户端：

```powershell
& "D:\code\dsh\python-course\.venv\Scripts\python.exe" "D:\code\dsh\python-course\code\agent_v1\http_client.py"
```

提示输入时发送“你好，用一句话介绍自己”。预期直接显示连续文字，agent_done处换行并结束本次客户端调用。客户端此时读取的是服务端SSE，显示的是解析后的正文；最终消息作为函数返回值保留，不重复打印字典。

学员截图已展示提示输入、完整自我介绍正文及返回PowerShell提示符，最新源码也已确认request_agent(prompt)传参正确。本次客户端实际请求、读取显示及正常退出成功。截图不单独测量每一片段的到达时间，也不扩展为工具或异常路径的运行证据；不追加这类测试。教员未代启服务、执行客户端或发送模型请求。

## 7. 显示工具进度（已完成）

基础文字收发完成后，继续显示已有tool_start与tool_end事件，让调用方在等待工具时知道当前过程。这一项沿用第7章事件消费者的分工，不改变工具执行位置或请求格式。

在http_client.py现有event类型的if/elif处理中增加两个分支：tool_start取event["tool_call_id"]，独占一行提示准备执行；tool_end取同一tool_call_id与event["status"]，独占一行显示状态。status直接显示原值即可，当前可能为success、error、timeout、cancelled。超时与取消状态沿用现有等待语义。

打印工具提示时先换行，使它与前面可能输出的文字片段分开。后续文字继续由text_delta处理，最终返回仍由agent_done负责。服务端已负责工具调用解析、参数校验、执行及结果回填，客户端在此只显示通知。

最新回读：tool_start已打印tool_call_id，tool_end已打印tool_call_id与status，两个分支都在逐事件循环内，提示前也已换行；处理后继续读取后续事件，静态通过。教员未代改源码或运行客户端。

换行释疑：print默认在末尾输出换行，字符串开头的\n则先输出一次换行。正文分片使用end=""，工具提示前的\n能结束尚未换行的正文；若上一条提示已换行，就会多出一行空白。当前保留这种简单排版即可，不为消除空行增加输出状态管理。main中的异常提示仅在HTTP调用抛异常时执行，不会在每次request_agent正常返回后额外打印。

## 8. 读取工作区文件（已完成）

保持已有服务端运行，重新运行客户端，在输入提示处发送：

```text
请调用 read_file 读取 AGENTS.md，然后用一句话概括内容。
```

已确认code/agent_v1/workspace/AGENTS.md存在；工具使用的路径相对于这个工作区，因此任务中填写AGENTS.md。客户端收到工具事件时显示开始和状态，之后继续显示模型根据文件内容生成的回答，最终在agent_done处结束。这次将已写好的显示分支用于现有文件任务，不新增源码或测试脚本。

学员最新截图展示上述输入、一次工具开始提示、同一tool_call_id的success结束状态，以及概括AGENTS.md的正文。本次文件读取任务的工具通知与回答已实际连通，HTTP客户端阶段完成。下一项整理项目依赖清单，不追加运行用例。

## 9. 连续输入任务

目标是启动一次HTTP客户端后，可以连续发送任务，每项完成后回到输入提示，输入/exit退出。现有服务端已在run_agent中加载和保存会话历史，因此每次请求仍发送本次prompt，连续任务的历史由服务端维护。

沿用cli.py中已经写过的输入循环，在D:/code/dsh/python-course/code/agent_v1/http_client.py中定义async def main()：

1. 在while True中用input读取prompt并strip去除首尾空白。
2. 输入/exit时退出循环；其余输入执行await request_agent(prompt)。
3. 将底部启动入口改为asyncio.run(main())，入口保留__main__判断。

main负责接收下一条任务；request_agent仍负责一次HTTP调用，处理到agent_done返回后，main继续下一轮。已有request_agent的收发及事件显示可以直接复用，本次不增加会话标识、重置接口或新协议。

这一项由学员亲写；静态正确即继续，不另加测试脚本或重复运行门槛。

首版回读：main、while、/exit退出和底部asyncio.run(main())均已写出，但循环内误用asyncio.run(request_agent(prompt))，外层事件循环已在运行，再调用asyncio.run会抛出RuntimeError。同步启动入口用asyncio.run建立并管理事件循环，进入异步函数后用await调用并等待协程。

最新回读：循环内已改为await request_agent(prompt)，底部仍由asyncio.run(main())启动，连续输入静态通过。已有事件处理及服务端历史可以复用，未增加运行验证。

## 10. 请求失败后继续输入

main逐条等待HTTP任务。如果服务端没启动而连接失败，或读取响应时超时，HTTPX会抛出Python异常；未捕获时异常会穿过main，使整个客户端退出。本节让它显示原因，再回到下一次输入。

httpx.HTTPError是HTTPX请求异常与HTTP状态异常的共同父类：连接失败、读取超时，以及raise_for_status报告的失败状态都能由它捕获。error来自except httpx.HTTPError as error，保存本次异常，打印它就能看到原因。

已有agent_error是服务端通过SSE发来的任务错误通知，需要先收到事件才能处理。HTTPError由客户端的HTTP调用直接抛出，因此在等待request_agent的调用处处理。

在http_client.py的main中，当前else分支内完成：

1. 将await request_agent(prompt)放进try。
2. 使用except httpx.HTTPError as error捕获HTTP异常，打印“请求服务失败：”及error。提示前可加换行，与已经显示的正文分开；这是显示格式，不作为功能审阅门槛。

try/except位于while循环内部，一次请求报错并显示后，自然进入下一轮输入；/exit仍正常退出。已有httpx导入可以使用，不需要创建error变量或增加其他依赖。这是围绕本项目连续输入的使用整理，不是教材新增章节。

本项由学员亲写，静态审阅后推进，不增加故障注入、测试脚本或额外模型请求。

最新回读：main的else内已用try包围await request_agent(prompt)，except httpx.HTTPError as error打印请求失败原因，整个处理位于while内部，静态通过。当前异常提示没有前置\n，属于排版选择，不要求补改。

## 11. 未取得完整回答时提示

run_agent成功时返回assistant消息，响应不完整、达到工具轮数上限或其他已有提前退出路径可能返回None。run_agent_to_queue会将正常返回值放入agent_done.result，因此result为None也是当前接口会产生的结果，并不是HTTPError异常。修改前客户端在此只执行print()再返回，调用方看不到结束情况说明。

在http_client.py的agent_done分支中，现有return之前判断event["result"] is None：是None时显示“任务结束，未取得完整回答。”，随后仍返回原结果。成功消息的正文已由text_delta显示，沿用已有返回流程。

这条提示只说明没有完整回答，不将所有None归为网络错误，也不推断具体停止原因。当前沿用既有dict | None接口，不修改服务端协议或run_agent。由学员亲写这处条件显示，静态正确即继续，不要求另造失败场景。

最新回读：result为None时已先显示未取得完整回答的提示，再单独return；单独return等价于返回None。非None时返回原消息，成功正文不重复打印，静态通过。tool_end前置换行已按学员排版选择去除，不设为问题。

## 12. 本节完成与应用

基础收发及文件读取有实际运行截图；后续[审阅任务](Agent阶段实战_HTTP客户端审阅.md)虽因模型生成长度限制未产出报告，已实际展示工具回传、None提示和重新输入。学员确认这些证据足以证明客户端接通，本节结束，报告不作为继续门槛。HTTP异常捕获仍按静态通过记录。当前进入[统一工具注册](Agent第05章_统一工具注册.md)。

## 13. 参考

- 本项目agent_runner.py中的stream_message：已有client.stream、aiter_lines与data行解析。
- [HTTPX异步流式响应](https://www.python-httpx.org/async/#streaming-responses)
- [HTTPX异常分类与HTTPError](https://www.python-httpx.org/exceptions/)
- [Python 3.12：asyncio.run的调用范围](https://docs.python.org/3.12/library/asyncio-runner.html#asyncio.run)
- [服务端事件流](Agent实战篇_HTTP事件流.md)
