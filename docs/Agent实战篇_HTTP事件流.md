# 应用阶段：把Agent事件通过HTTP逐段发送

> 接口更新（2026-10-29）：agent_done仍表示Agent调用已正常返回，其result已改为message/completed/reason三键结果；是否取得完整最终回答由result.completed说明。异常仍用agent_error，取消继续传播。见[进阶第5节](Agent进阶05_运行结果与结束原因.md#9-本节完成结果)。下文保留首次实现及旧返回约定的历史过程。
>
> 当前进展：2026-10-22。普通POST /chat及当前SSE入口均已有学员运行截图。最新结果包含多条text_delta、model_response_end/usage及agent_done/result，事件收发链完成。下一项见[Python HTTP客户端](Agent实战篇_HTTP客户端.md)。
> 教材对照：[实战篇第7章](https://www.dgzhuya.com/modules/pr07-deploy)中的事件订阅与SSE。当前继续使用Python自研运行时。

## 1. 这一节要做什么

当前/chat等run_agent执行结束，再返回一个完整JSON。接下来希望模型产生一段文字就能发送一段，工具开始和结束也能及时通知调用方。

```text
run_agent产生事件 → HTTP监听器放入队列 → 发送函数取出事件 → 流式HTTP响应
```

已有模型和工具事件继续使用；新增的是从Python事件到HTTP响应的连接。SSE是Server-Sent Events（服务器发送事件），在同一个HTTP响应中按约定格式持续发送消息。HTTP响应结束后，本次发送才结束。

## 2. 队列：一端放，另一端取

asyncio.Queue是先进先出的异步队列。在异步函数中，例如：

```python
mailbox = asyncio.Queue()
await mailbox.put("苹果")
item = await mailbox.get()
```

put放入一项；get取出最先放入且尚未取走的一项。队列为空时，await get会等待新项，让其他协程继续运行，不需要自己写sleep轮询。上例只是说明API，项目中放入的是已有事件字典。

每个HTTP请求后续会创建自己的队列，监听器向该队列放事件，发送函数从同一个队列取事件。不能等待整个run_agent结束后才开始取，否则仍然要等到最后才能发送。当前不使用join，因而不需要为这次消费增加task_done流程。

## 3. yield：交出一段，之后还能继续

与本次作业分开的例子：

```python
async def fruit_parts():
    yield "苹果"
    await asyncio.sleep(1)
    yield "梨"
```

yield交出当前这一项并暂停；调用方再次取下一项时，从暂停处继续。return则结束函数。async def中含yield时，得到的是异步生成器，调用后交给async for等消费者逐项读取；不能用await fruit_parts()取得所有结果。

FastAPI提供StreamingResponse。后续用它消费异步生成器，把每次yield出的字符串编码后写入响应；发送函数因此不需要先攒成完整列表。框架会处理字符串的UTF-8编码。发送分段与网络实际接收分块不保证一一对应，调用方按SSE的空行识别消息。

## 4. SSE消息格式

本项目先统一用data字段，事件种类保留在JSON里的type：

```text
data: {"type": "text_delta", "text": "你好"}

```

字符串实际是data:、一个JSON字符串、两个换行符，即data: <JSON>\n\n。最后的空行分隔两条事件。json.dumps(event, ensure_ascii=False)可把事件字典转成保留中文的JSON字符串；这里不用多行缩进JSON，正文自身的换行会被JSON编码转义。

## 5. 当前动手

在code/agent_v1/http_api.py新增异步生成器stream_events(queue)。它应持续从queue按顺序取出事件，每取到一个字典，就按第4节格式交出一条SSE字符串；取到None时结束，不把None发给客户端。队列为空只表示暂时没新事件，不能据此结束。

None是发送端与生产端约定的结束信号，后续由Agent任务结束后的收尾代码放入队列。model_response_end只代表一次模型请求接收循环结束，之后还可能执行工具、再次请求模型，不能拿来结束整次HTTP响应。

这一项只写实际将复用的发送函数，保持现有/chat可用；后续再接监听器、并发运行Agent、任务收尾与StreamingResponse。当前不另写队列实验、测试脚本或调用模型。

## 6. 首版回读与当前修正

首版已正确使用await queue.get、json.dumps(..., ensure_ascii=False)和yield，但当前仅取一项，yield后立即return，因此不能持续发送。需要用循环持续取事件，queue.get放在循环内；仅在取到None时结束，且判断应在JSON转换之前，否则结束信号会变成null被发送。

yield的字符串当前只有JSON与双换行，缺少协议要求的data:前缀。局部变量名data不会自动生成文本中的data:字段，发送内容需要显式包含它。学生修正上述三处后再接入监听器与响应；不代写函数，不另运行脚本或请求模型。

最新回读：循环内读取、编码前None判断及移除无条件return均正确。当前yield写成data：，其中是中文全角冒号；SSE要求英文半角冒号，改为data:即可。这一字符修正与下一项一并完成，不另设运行或确认门槛。

## 7. 当前动手：让已有事件进入队列

在http_api.py导入agent_events中的原listeners列表，新增异步函数run_agent_to_queue(prompt, queue)，负责完整的一次Agent调用及事件转发。

### 直接使用队列的put方法

```python
listener = queue.put
```

这里保存的是当前queue的异步方法，不带括号就不会立即放入东西。把listener加入原listeners后，已有emit执行await listener(event)，就会调用await queue.put(event)，事件因此进入当前队列。函数的参数约定已经匹配，不必为了转发再增加一个函数。

### 调用、登记与收尾

新函数使用现有agent_lock，在取得锁之后登记listener，再等待run_agent(prompt)。登记、Agent调用和移除登记均在同一个锁的范围内，以免等待中的请求收到前一个任务的事件。

正常返回后，向queue放一个字典事件，字段约定为type="agent_done"、result=run_agent的返回值。agent_done表示Agent函数已返回；result为None时仍沿用没有取得最终消息的约定，不把函数返回自动当成成功回答。遇普通Exception时，放type="agent_error"、message为异常文字的事件；取消信号继续向上传递。当前Python的CancelledError不属于Exception，不会被普通异常分支吞掉。

在finally中移除本次登记的listener，并向queue放入None。不论普通成功或异常，发送函数都能读到结束信号；否则发送函数可能一直等待下一项。listeners.remove(listener)表示从原共享列表移除这次登记。

当前只完成这个生产事件的包装函数，同时修正SSE冒号；现有/chat仍保持已能使用的行为。下一项再将每请求队列、后台任务与StreamingResponse接到路由。当前不运行模型或另加测试脚本。

## 8. 补讲：变量从哪里来，具体调用什么

教员此前省略了队列尚待创建与传入、listener和listeners的区别，又把run_agent函数笼统称为“Agent”，导致操作要求缺少可对应的代码。当前补清来源，不据此判断学员未掌握已有知识。

| 名称 | 来源与实际内容 |
| --- | --- |
| queue | run_agent_to_queue的参数；后续由HTTP入口创建asyncio.Queue对象并传进来，目前路由还没有连接这一步 |
| listeners | 文件顶部from agent_events import listeners导入的原列表，保存要在事件发生时调用的方法或函数 |
| listener | 用listener = queue.put这次赋值创建的本地变量，指向当前队列的put方法；它不是框架提供的固定名称 |
| answer或result | await run_agent(prompt)的返回值，用哪个变量名保存均可；当前chat已经使用answer |

“把listener加入listeners”对应listeners.append(listener)：列表里保存一个稍后可调用的方法。已有emit循环执行await listener(event)，这次保存的方法就是queue.put，所以等价于await queue.put(event)。登记时没有调用put，事件产生时才调用。

最新生产端首行写成listeners = queue.put，多了s，会在当前函数内遮蔽导入的列表。应使用单数listener保存方法，复数listeners继续表示原列表。

“Agent返回值”在本节具体指await run_agent(prompt)的返回值。该函数运行既有的历史加载、模型和工具循环、保存流程，成功时return message。它就是当前chat中answer = await run_agent(prompt)得到的同一个结果，不是另一种Agent对象。

向队列放入字典的实际写法，例如：

```python
answer = await run_agent(prompt)
await queue.put({"type": "agent_done", "result": answer})
```

result在这里是自行约定的字典键，answer是保存函数返回值的Python变量；整个字典是put的一项参数。普通异常分支中的error来自except Exception as error，再通过await queue.put({"type": "agent_error", "message": str(error)})传递。finally里的两步分别是listeners.remove(listener)与await queue.put(None)。结束信号让stream_events知道可以退出。

锁内登记、调用与移除的原任务范围保持不变；本次只解释并指出当前变量名，教员不代改源码，不增加运行或理解检查题。

## 9. 生产端首版回读

run_agent_to_queue已正确保存listener = queue.put，并在共享锁内登记。当前仍需修正：

1. result = run_agent(prompt)缺少await，保存的是协程对象；队列会原样存入它，不会替调用方执行。将这一行移入try内并等待，得到真正返回值，同时让run_agent抛出的普通异常进入except。
2. 正常事件的字段tyoe应为type，值仍为agent_done。
3. except当前重复发送agent_done/result，应改为agent_error/message，message保存str(error)。若run_agent抛出异常，没有正常result可供该分支使用。
4. 移除listener及放入None当前是普通后续代码，应移入finally且仍处于锁内，确保取消或异常离开时完成清理并通知发送端结束。

本次只修正现有生产端，不增加路由改造、运行或测试门槛。教员未代改学生源码。

最新回读：await已移入try，正常字段拼写已修，错误分支已保存str(error)，清理已移入finally并在锁内；结构正确。错误分支的type仍为agent_done，改为agent_error后与约定一致。这一字符串修正与下一项一并完成，不单设确认或运行门槛。

## 10. 当前动手：连接HTTP入口与发送任务

### 新增调用的含义

从fastapi.responses导入StreamingResponse。它接收一个异步生成器对象，逐项发送yield交出的内容；media_type="text/event-stream"用于声明响应是SSE事件流。生成器对象由stream_events调用取得，不用await它。

asyncio.create_task接收协程对象，将其安排为可与当前代码交替执行的任务，并返回Task对象。本次保存为task，它代表run_agent_to_queue的执行过程，不是最终回答。后续通过这个对象等待或取消该任务。

### 名称来源与连接顺序

```text
chat(data)创建queue和task
  ├─ task运行run_agent_to_queue(data.prompt, queue)，产生事件
  └─ StreamingResponse消费stream_events(queue, task)，发送事件
```

学生修改chat：每次请求创建一个asyncio.Queue，将run_agent_to_queue(data.prompt, queue)交给create_task并保存返回的task，然后返回StreamingResponse，内容由stream_events(queue, task)提供，media_type为text/event-stream。路由原来的直接await run_agent及async with锁块移除，完整Agent调用的锁已由run_agent_to_queue管理。此时不先await task，否则任务完成后才返回响应，文字仍会积到最后。

### 发送函数管理任务收尾

stream_events增加task参数，原有读取和yield循环放在try内，新增finally负责收尾：若task尚未完成则调用task.cancel，随后await task，并处理该等待所抛的asyncio.CancelledError。cancel提出取消请求，await task等待它退出，生产端已有finally因此能移除监听器和释放锁。这里处理子任务等待产生的取消，不在正常读取循环中吞掉取消信号。

把task传给生成器也使任务对象在整个发送期间有人持有。不要只创建一个无人保存的后台任务，或使用请求结束后才执行的BackgroundTasks来生产这次响应所需的事件。

本次完成范围为异常事件类型的小修、chat路由连接以及发送函数的任务收尾；学生亲写源码，教员只静态审阅，不代启服务或发模型请求。实际使用在连接完成后沿原本机服务继续，不为这些步骤另建测试脚本。

## 11. HTTP连接首版回读

最新源码chat中的队列创建、create_task、StreamingResponse及media_type正确，生产端agent_error类型也已修正。当前尚未通过的是stream_events：

1. 路由已传stream_events(queue, task)，但函数仍只接收queue，调用时会因多传一个参数触发TypeError。需要同步增加task参数。
2. 读取循环仍无try/finally，尚未管理生产任务。将原while置于try内；finally中用task.done()判断任务是否结束，未结束则task.cancel()，随后await task并处理这个等待产生的CancelledError。

两个finally职责不同：生产端移除监听器及放入None；发送端管理chat创建的Task，让它在发送函数退出时结束。本次仅完成原任务遗漏的这两处，不新增功能或运行门槛，教员未代改源码。

最新回读：stream_events已同步接收queue、task，原循环已置于try，finally中的done/cancel、await task及CancelledError处理正确。chat连接、生产端登记/移除及结束信号均静态通过。教员未执行学生源码或请求模型。

## 12. 实际使用事件流入口（已完成）

当前结束一段任务，目标是实际看到HTTP返回的text_delta及最后的agent_done。原启动命令没有自动重载，修改代码后在原Uvicorn终端用Ctrl+C停止，再在项目根目录重新启动：

```powershell
.\.venv\Scripts\python.exe -m uvicorn http_api:app --app-dir code\agent_v1 --host 127.0.0.1 --port 8000 --workers 1
```

保持服务终端运行，另开PowerShell提交一次真实请求：

```powershell
'{"prompt":"Say hello in three short sentences."}' | curl.exe -sS -N -H "Content-Type: application/json" --data-binary "@-" "http://127.0.0.1:8000/chat"
```

curl.exe是本机命令行HTTP客户端；已只读确认本机可用。-N关闭curl自己的输出缓冲；左侧JSON经管道送入curl，--data-binary "@-"从标准输入读取请求正文，-H声明正文为JSON。英文prompt便于本次在不同PowerShell编码及原生命令参数规则下直接提交，不新增请求文件。

正常应看到多条data:开头的SSE消息，text_delta携带文字片段，model_response_end表示一次模型接收结束，agent_done的result携带最终消息，然后请求结束。该使用方式直接展示协议文本；前端逐字聊天界面仍是后续任务。只要求这一项实际新行为，不追加异常、并发或取消用例，不另建测试脚本；教员不代启服务或发送模型请求。

学员最新PowerShell截图已展示多条data/text_delta，随后是含usage的model_response_end，最后是agent_done，result中包含role=assistant及完整自我介绍。记录为当前普通文字任务经HTTP发送事件及返回最终结果的实际成功。单张截图不作为片段到达间隔或所有退出路径的测量证据，不因此追加时序、异常或并发测试。教员未执行服务或模型请求。

## 13. 下一步：Python消费端

服务端已能提供事件流，接下来由学员新增http_client.py，用已有HTTPX的AsyncClient.stream与aiter_lines读取本机/chat，解析data后的JSON，再按事件类型显示文字或取得最终消息。教学目标是把协议事件还原成可读回答，任务见[Python HTTP客户端](Agent实战篇_HTTP客户端.md)。

## 14. 资料

- [教材：把Agent封装成服务](https://www.dgzhuya.com/modules/pr07-deploy)
- [Python 3.12：asyncio.Queue](https://docs.python.org/3.12/library/asyncio-queue.html)
- [Python 3.12：创建与取消Task](https://docs.python.org/3.12/library/asyncio-task.html#creating-tasks)
- [FastAPI：StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [HTML标准：SSE消息格式](https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation)
- [curl：输出缓冲与请求正文](https://curl.se/docs/manpage.html)
