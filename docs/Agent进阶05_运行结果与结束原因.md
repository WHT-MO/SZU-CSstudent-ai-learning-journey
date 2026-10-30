# 进阶第5节：运行结果与结束原因

> 2026-10-29。本节已整体静态通过：模型结果、Agent各普通退出、CLI与HTTP原因显示均已完成。源码由学员亲写，本轮未运行代码或请求模型，本节没有剩余必做项。

## 1. 为什么现在做

改动前stream_message返回(message, completed)，遇到缺少密钥、HTTP失败或流不完整等情况时，只保留消息和布尔值。具体原因往往只打印在服务端。

run_agent的无完整响应、输入预算不足、工具轮数达到上限等路径还会统一返回None，HTTP客户端只能显示“任务结束，未取得完整回答”。此前模型finish_reason为length时，客户端已经接通，但客户端无法直接取得这个原因。

目标是把原因作为返回数据逐层传递：模型层说明一次请求的结果，Agent层说明整次任务为何结束，入口根据数据显示。这个练习接回第4章的响应处理及第6章的内部消息与显示数据。

教材关联：[第6章消息系统](https://www.dgzhuya.com/modules/ch06-messages)的助手消息保留停止原因及错误信息。本项目按当前Python结构安排下面的应用练习。

## 2. 当前动手：模型层使用有名称的字段

先用已有的普通字典，不引入新库。stream_message的每个普通返回统一包含三个键：

| 键 | 值 | 含义 |
| --- | --- | --- |
| message | 原助手消息字典或None | 完整或已接收的部分消息；原来会丢弃的不完整工具调用继续不保留 |
| completed | bool | 沿用当前一次模型响应的完整性判断 |
| reason | str或None | 非完整/失败的原因；完整响应为None |

这是函数的返回包装。里面的message才是能加入messages的模型消息；不要把整个包装加入历史或放进下一次模型请求。

例如当前mock的HTTP 500可以返回：

```python
{
    "message": None,
    "completed": False,
    "reason": "流式 API 请求失败：500",
}
```

“有部分正文”和“正常完整”仍通过message与completed组合表达，reason增加解释。False时即使有部分正文，也不代表可执行工具。

## 3. model_client.py的修改范围

只改stream_message，返回类型从tuple[dict | None, bool]改为dict；普通返回都使用上述三个键。extract_message、non_stream_message和summarize_messages保持现有接口。

| 现有分支 | message、completed | reason应说明什么 |
| --- | --- | --- |
| 缺少API key | None、False | 缺少DEEPSEEK_API_KEY |
| 完整响应 | 原message、True | None |
| 流结束条件未满足，含不完整工具调用 | None、False | 按下述完整性原因规则填写 |
| 流结束条件未满足，没有任何可保存正文或思考 | None、False | 同上，仍须给出原因 |
| 流结束条件未满足，有可保存部分内容 | 原partial_message、False | 同上，保留既有部分消息处理 |
| TimeoutException | None、False | 流式请求超时 |
| HTTPStatusError | None、False | 包含实际HTTP状态码，例如500 |
| RequestError | None、False | 网络请求失败，带现有异常说明 |
| 解析异常 | None、False | 响应解析失败，带现有异常说明 |

现有完整性分支同时检查stream_completed与finish_reason。给原因时先区分：

1. stream_completed为False：说明没有收到流的结束标记；此时即使finish_reason为stop，也仍是不完整响应。
2. 已收到结束标记，但finish_reason不属于现有允许值：说明模型的结束原因，并保留原值，例如“模型结束原因：length”。缺失值也应能从说明中识别。

在这个不完整分支内先确定reason，再供原有三个return使用；不复制整套消息构造或改变原来的保存/丢弃选择。原因的中文措辞可以自行组织，能看出发生什么即可。

CancelledError继续raise，取消由已有的Task清理链处理。它不会转换成普通失败结果。现有事件、正文累积、usage、print及请求参数沿用，不同时增加重试或自动续写。

## 4. 同步已有调用方

接口变化必须同步到当前消费者，否则原来的两个变量会错误地解包字典的键。

### 4.1 agent_runner.py的两处调用

首次请求和工具执行后的再次请求均改为：先用一个变量model_result接住返回字典，再从model_result["message"]及model_result["completed"]取值，赋给原来的message与completed。

原循环、保存、工具分发及run_agent的对外dict | None接口先沿用。reason此时保存在model_result中，下一段会将它接入整次Agent任务的结果；本段不要求先猜写CLI/HTTP的改动。

### 4.2 test_stream_mock.py的已有500场景

把原来的二元解包改为接收字典，现有断言和打印分别读取message与completed键。只同步已有消费者，不新增场景、文件或运行门槛。

## 5. 后一段与本段的完成边界

模型结果与Agent/入口两段均已静态通过，下面保留实现说明。模型响应原因与Agent主动停止原因已区分：例如length来自模型，最大工具轮数来自Agent循环。两个入口均读取结果中的reason，最终完成记录见第9节。

本段检查stream_message所有普通返回的三个键、成功与失败的原因值、取消传播、runner两处字段读取及旧mock同步。只审阅源码，运行/测试按学员当次要求安排。不重复验收前四节，不修改会话文件。

## 6. 第一段首版审阅

2026-10-29回读结果：返回注解、共享result字典、成功与四类请求异常返回、取消传播、runner两处取字段及旧mock同步均已写出。共享字典的做法可保留，当前修正以下三处后再推进：

1. 缺少API key的分支仍返回(None, False)，会使已按字典读取的调用方报错。将result初始化移到密钥检查之前，在该分支填入缺密钥的reason并返回result。
2. 不完整分支的三个子分支把completed设为stream_completed。stream_completed只表示收到[DONE]，例如它为True但finish_reason为length时，模型响应仍不完整。删除这三处赋值或明确设False，保留初始化的False；正常成功分支沿用True。
3. 不完整分支的reason目前按“是否有工具/正文”分别设置，前两个丢失停止原因，正文分支也未区分缺少结束标记与模型停止原因。进入父级不完整分支后统一设置reason：缺少标记时说明缺少结束标记，否则包含实际finish_reason；随后三个子分支只决定message并返回，不再覆盖reason。

本次未修改或运行学生源码，未新增用例、请求模型或Git上传。CLI/HTTP显示仍在下一段处理，不提前增加其他改动。

## 7. Agent任务结果与两个入口

2026-10-29第二次回读：result初始化已移到密钥检查前，该分支返回字典；不完整分支保持completed=False，父分支统一区分缺少结束标记与异常finish_reason；正常响应和各异常返回、取消传播以及调用方读取均正确。缺密钥时赋stream_completed此时恒为False，正常分支赋stream_completed此时恒为True，均可保留。第一段整体静态通过，不加运行门槛。

### 7.1 一次模型响应与整次任务

run_agent也统一返回message、completed、reason三个键，返回注解改为dict。其completed表示这次Agent调用是否取得完整的最终回答；模型返回完整工具调用仅表示一次模型响应完整，Agent还要执行工具并继续请求。

因此不能在每次stream_message返回后直接return。完整最终回答才是正常结束；模型失败/中断及Agent主动停止均返回completed=False并给原因。已有工具错误、参数错误和只读拒绝继续反馈给模型，按现有流程处理，不因一个工具结果就直接结束整个任务。

### 7.2 覆盖run_agent现有退出位置

| 位置或条件 | 返回内容 |
| --- | --- |
| 完整响应且没有tool_calls | 保存message后，直接返回当前model_result；此时completed为True |
| not completed且有部分message | 按现有逻辑保存可保留部分后，返回当前model_result，保留原reason |
| 首次或后续prepare结果为空，共两处 | 三键字典：message=None、completed=False、reason说明输入预算不足 |
| 工具轮数达到上限 | 保留原调用/工具结果回填与保存，再返回三键字典：message=None、completed=False、reason说明最大工具调用轮数 |
| 两处缺少tool_call_id而直接结束 | 三键字典：message=None、completed=False、reason说明工具调用结构不完整 |
| message为None，while未进入或因最新请求失败而结束 | while之后返回最新的model_result，保留模型错误原因 |

特别注意最后一行：当前while message is not None会跳过message=None的失败，循环内的not completed分支接不到它。在while结束后、与while同级补return model_result，使首次失败和工具执行后的失败都能返回原因。

已有messages.append(message)、工具结果和save_session的顺序沿用，返回包装不加入历史。若需要一个单独的Agent结果变量可命名为agent_result；当前工具结果循环已有result这个名称，避免拿它兼作共享任务结果而被循环覆盖。

### 7.3 cli.py显示返回原因

run_cli_task目前直接await run_agent，改为用agent_result接收返回字典。await正常返回后，completed为False时显示reason，例如“任务未完成：达到最大工具调用轮数”。completed为True时正文已由text_delta显示，保留当前流式显示方式。

现有异常显示及CancelledError传播沿用。任务返回字典与抛异常是两种已有路径，取消继续交给/stop及退出清理处理。

### 7.4 HTTP透传及客户端显示

http_api.py现有run_agent_to_queue已接收run_agent返回值，并放入agent_done的result中，可直接透传新字典。agent_done表示本次调用已返回；其中result的completed说明是否取得完整最终回答。

例如达到工具轮数上限时，事件形状为：

```json
{
    "type": "agent_done",
    "result": {
        "message": null,
        "completed": false,
        "reason": "达到最大工具调用轮数"
    }
}
```

http_client.py的request_agent在agent_done分支中，用agent_result接收event["result"]。原来的“result is None”判断改为检查agent_result["completed"]；为False时显示agent_result["reason"]，最后不论True或False均返回agent_result。正文继续由text_delta显示，不重复打印返回消息。

agent_error及HTTP异常继续按现有方式显示；request_agent在agent_error路径仍返回None，因此客户端函数的dict | None注解可以保留。run_request无需因返回包装单独调整。

### 7.5 本段完成边界

当前实际源码修改范围为agent_runner.py、cli.py和http_client.py；HTTP服务端已有透传结构只需对照理解。第一段模型代码和旧mock已通过，不重做。不新增测试、事件类型、自动重试、会话格式或模型请求。

静态检查各个既有退出、while之后的返回、部分消息保存、正常正文显示和两个入口的原因读取。未捕获的普通异常仍交给现有入口异常分支，取消继续传播，不为凑“统一返回”新增大范围except。

## 8. 第二段首版审阅（历史记录）

2026-10-29首版回读结果：run_agent注解已为dict，正常最终回答和部分回复均在保存后返回model_result，while之后的返回位置正确，CLI接收结果并显示reason也正确。HTTP服务端已有透传继续可用。首版当时还需修以下两类问题：

1. Agent主动停止的五处仍直接返回model_result。第一次预算不足在模型调用之前，会引用尚未赋值的局部变量并触发UnboundLocalError；后一次预算不足、轮数上限及两处缺tool_call_id时，model_result往往还是已完整接收的工具请求，completed=True、reason=None，不能代表Agent已经取得完整最终回答。分别新构造message=None、completed=False的任务结果，reason按预算不足、轮数上限或调用结构不完整填写；原有回填和保存顺序保留。
2. HTTP客户端已按completed判断并返回结果，但未完成时仍打印原来的笼统文字。需打印结果中的reason，才能完成本节的客户端目标。当前agent_ressult拼写虽在各引用处一致、不会因此报未定义，可顺手统一为agent_result，不以拼写单独阻塞。

本次只修Agent主动停止与HTTP显示，已正确的模型结果透传、CLI及循环后返回不重做。未代改或运行源码，没有新增测试、模型请求或Git上传。

## 9. 本节完成结果

2026-10-29最终回读：run_agent在每次调用内新建独立的失败结果字典，message始终为None、completed始终为False；预算两处、轮数上限、缺tool_call_id两处均先写具体reason再返回。集中创建本次调用的失败结果并在分支填原因正确，不要求各分支重复写字典。

正常最终回答、可保留部分回复及while之后的模型失败均返回当前model_result；历史只保存原message和工具结果。CLI显示未完成原因，HTTP服务端沿用agent_done.result透传，HTTP客户端已显示具体reason并在完成/未完成时均返回agent_result，变量拼写也已统一。

本节整体静态通过。run_agent的普通返回均为message/completed/reason三键字典；模型层completed表示一次响应完整，Agent层completed表示取得完整最终回答。未捕获的异常及取消仍沿现有入口处理，不改变为普通返回。HTTP客户端的agent_error路径仍返回None。

README、计划、架构地图与相关早期讲义的接口更新说明已同步。本次未代写或运行学生源码、未新增测试或请求模型、未修改会话或推送GitHub；静态通过不记为实跑。本节没有待改源码或额外必做项。
