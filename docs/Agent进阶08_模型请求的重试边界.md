# 进阶第8节：模型请求的重试边界

> 2026-10-30。本节整体静态通过：错误分类、摘要有限重试、流式独立缓冲及正文发送边界、终止原因和取消传播均已接齐，遗漏引号已补好。本次未运行源码或模型请求，不新增验证门槛。

## 1. 目标与现状

重试策略同时回答三个问题：错误是否可能暂时发生、本轮结果已经交给谁、最多再请求几次。只写“遇到异常就再来一次”会把参数错误、主动取消及部分输出混为一谈。

起步时summarize_messages已有range(3)和等待逻辑。现在它已接入集中错误分类，对候选错误有限重试，非候选错误或最后一次失败直接返回。stream_message仍遇网络或状态异常就返回失败，当前接下文第7节的流式重试。

## 2. 错误分类：哪些值得再次尝试

本项目先采用以下候选规则：

| 情况 | 是否列入重试候选 | 原因 |
| --- | --- | --- |
| 429 | 是 | 速率或并发限制，等待后再尝试 |
| 500、503 | 是 | 服务端出错或繁忙，官方建议稍后再试 |
| HTTPX TimeoutException | 是 | 超时可能是暂时状况，仍受次数和输出状态限制 |
| HTTPX NetworkError | 是 | 连接或网络读写故障可能是暂时状况 |
| 400、401、402、422 | 否 | 格式、身份、余额或参数问题需要改变条件 |
| JSON/结构解析错误 | 本段不自动重试 | 按当前响应解析失败路径处理 |
| finish_reason为length | 本段不自动重试 | 已触及输出或上下文限制，需要处理预算或任务策略 |
| 用户取消 | 否 | 保持CancelledError向上传播 |

以上是当前项目的候选白名单，不表示一定恢复，也不是所有供应商共同遵守的完整策略。HTTPX的RequestError还覆盖不支持协议、重定向过多等异常，本段用更具体的TimeoutException和NetworkError，不将所有请求异常都视作暂时故障。

参考：[DeepSeek错误码](https://api-docs.deepseek.com/quick_start/error_codes/)、[HTTPX异常层级](https://www.python-httpx.org/exceptions/)。

## 3. 流式请求还要看输出边界

即使错误属于候选，也不能只凭错误类型自动重发。若本轮已向用户显示“你好”，网络随后断开，重新请求又从开头输出，用户可能看到“你好你好，完整回答……”。

本项目的初始策略是：本轮尚未对外发送text_delta、错误属于候选且尝试次数未用尽，才允许自动重试；已发送正文则沿失败路径结束本轮。模型内部收到但尚未交给用户的片段，重试时需要丢弃并重新组装。本规则只处理请求重发，不声称已经实现断点续传或界面替换。

重试的单位是一轮模型HTTP请求。不能通过重新调用整个run_agent来代替，否则前面已经执行过的文件写入等工具也可能重复执行。工具要在完整模型响应校验后才执行，这条边界继续保留。

再次请求可能产生额外生成与费用，因此必须限制次数。沿用摘要现有的最多3次请求，即首次加最多2次重试；两次等待分别为1秒、2秒。用户取消仍立即向上传播，不当作服务故障重试。

## 4. 当前动手：统一分类并接入摘要

只修改model_client.py，完成两项：

### 4.1 新增普通判断函数

定义is_retryable_model_error(error) -> bool，规则如下：

- error是httpx.HTTPStatusError时，读取error.response.status_code，仅429、500、503返回True。
- error是httpx.TimeoutException或httpx.NetworkError时返回True。
- 其他情况返回False。

这只是错误分类，不发请求、不等待。普通函数即可；调用方取得True后，还要结合次数及输出状态决定是否再次请求。HTTP状态检查仍通过raise_for_status产生HTTPStatusError。

### 4.2 摘要循环使用该判断

在summarize_messages现有三次循环中，把网络类与HTTP状态的两段捕获合并为except httpx.HTTPError as error。调用新增判断函数：不属于候选，或已是最后一次尝试时，显示错误并返回None；其余情况await原来的等待，进入下一次循环。

保持成功时返回摘要、解析失败时返回None、CancelledError继续raise的语义。现有range(3)、等待时长及摘要请求体继续使用。本段会让500和503进入有限重试，并让非候选请求错误直接结束。

## 5. 完成条件与下一段

静态检查判断函数和摘要循环的异常分支、最后一次边界及返回语义，即完成本段。不要求新建测试或发起模型请求。

流式函数的重试循环、正文发送状态和每次尝试的缓冲清理属于下一段，本次尚未接入。讲解了边界不等于代码已经具有自动流式重试能力。

## 6. 首版回读：类型判断已修正，摘要通过

2026-10-30回读：摘要保留range(3)，合并捕获HTTPError，非候选或attempt==2时返回None，其余等待后重试；取消继续raise，解析失败返回None。这部分接线正确。

分类函数首版的三处error is httpx.HTTPStatusError/TimeoutException/NetworkError曾导致实际异常落到False，摘要第一次失败就退出。error是except绑定的异常实例；is比较两个值是不是同一个对象，不能判断实例属于哪个异常类别。

学员已将三处条件改为isinstance，分类函数和摘要循环现已静态通过。isinstance同时识别子类，例如ReadTimeout也属于TimeoutException。摘要调用处的is_retryable_model_error(error) is False比较实际布尔返回值，写法正确。不追加运行步骤。

## 7. 当前动手：流式请求的有限重试

只修改stream_message，继续使用现有is_retryable_model_error及最多3次请求。模型调用的参数和message/completed/reason返回结构沿用现有接口。

### 7.1 请求准备与尝试循环

函数开头的result初始化、密钥检查、request_body和headers准备位于尝试循环之前；缺少密钥时仍能直接设置reason并返回result。

准备好请求后，增加for attempt in range(3)。把现有请求、流读取、响应组装及try/except整段置于循环内。每次尝试先重新初始化以下状态，再进入try：

| 状态 | 本次尝试的初值 |
| --- | --- |
| content_parts | 空列表 |
| tool_calls | 空字典 |
| reasoning_parts | 空列表 |
| stream_completed | False |
| usage | None |
| finish_reason | None |
| has_emitted_text | False |

这些初始化应属于每次尝试。否则第一次失败留下的半截正文、工具名或参数可能拼进下一次响应。函数原有的stream_completed及缓冲初始化移到这里即可。

### 7.2 标记正文发送

has_emitted_text是本次尝试的局部布尔值，表示是否已经进入正文对外发送阶段。在if content分支中，构造text_delta事件后、await emit(event)之前，将它设为True。

标记先于await，可以在交出事件前确定已经跨过自动重试边界。当前reasoning_content和工具片段仅在本函数内部组装，没有作为正文发给用户，因此不据它们设置这个标记。

### 7.3 合并HTTP异常并决定重试

将原来的超时、HTTP状态和请求异常三段合并为except httpx.HTTPError as error。只有以下条件全部满足，才await asyncio.sleep(2 ** attempt)，然后continue重新尝试：

- is_retryable_model_error(error)返回True；
- has_emitted_text仍是False；
- attempt小于2。

条件不满足时，记录包含异常类名和信息的失败reason，显示错误并返回result。重试分支先作决定，不提前把临时失败写进result的reason，避免后一次成功仍残留前一次错误原因。

每次请求仍使用async with client.stream，抛出HTTP异常后先退出响应上下文，再等待和开始下一次请求。

### 7.4 保留的结束语义

成功仍立即返回完整结果；length、缺结束标记等非完整响应仍走现有保存/失败返回路径，本段不将它们变成自动重试。JSON或字段解析失败仍返回失败；CancelledError继续raise，包括等待重试期间的取消。

HTTP异常发生在已发送正文之后时，本段沿现有HTTP失败路径返回，不在此扩展部分回复保存机制。model_response_end及正常响应组装保持在当前流读取结束的位置。自动重试不调用run_agent，也不重新执行工具批次。

### 7.5 本段完成条件

静态确认循环及try/except缩进、逐次缓冲重置、正文发送标记位置、三个重试条件和终止返回。不要求新增测试脚本、模型请求或服务启动；当前首版结果见下一节。

## 8. 流式首版回读：最后补充失败原因

2026-10-30回读：请求准备在循环外，每次尝试重置三种缓冲及完成、usage、finish_reason、has_emitted_text；正文emit前置True，合并HTTPError后以“非候选或最后一次或已经发正文”终止，等价于第7节的三个重试条件。取消、解析失败及正常/不完整响应返回均保留，主体静态正确。

学员在sleep后没有显式continue，当前结构下except结束便到循环体结尾，会自然进入下一次尝试，正确，不要求补写continue。if分支中continue使用不同宽度的缩进但仍在if块内，不应误报成Python语法错误。

首版终止失败reason只拼接str(error)，超时文字为空时缺少具体类别。学员已补上type(error).__name__并先设置reason、再打印和返回，该处静态正确。

随后解析异常分支的reason赋值曾遗漏结束双引号。最新回读确认第257行已补齐，先赋值再打印和返回的顺序正确。本节整体静态通过，没有剩余必做代码项；未运行模型请求，不把静态结论记为实测。

## 9. 下一项

进入[MCP工具服务](Agent进阶09_MCP工具服务.md)，学习让独立进程通过标准协议提供工具。现有有限重试不等于输出断点恢复或工具重复执行保护；后续按具体行为展开。
