# 第 4 章第一小节：把模型函数传给循环

位置：Agent Loop 与模型请求的边界。

目标：同一份循环分别运行两个已有的模拟模型，选择模型时只修改传入的函数。

## 1. 封装前的代码

当前循环直接写了 `fake_model_always_tool(messages)`。要换回正常回答的模拟模型，就需要修改循环内部的函数名。

两个模型函数都接收消息列表、返回单条 assistant 字典。循环可以通过参数接收要使用的模型函数。

## 2. 一个概念：函数本身可以作为参数

`fake_model` 表示函数本身，`fake_model(messages)` 表示立即调用该函数取得结果。

传入函数后，接收它的函数可以在合适的位置调用它。这和之前工具执行器接收 `tool_function` 的用途相同。

本练习接收模型函数的参数叫 `call_model`；在循环里调用它时，仍传入 `messages`，并取得 `reply`。

## 3. 学员实现任务

把现有消息初始化、轮数初始化、while 循环与最后的显示封装为 `run_loop(call_model, max_tool_rounds=3)`。

- 每次进入 `run_loop` 都有自己的新 `messages` 和 `tool_rounds`。
- 循环调用传入的 `call_model`，保留现有工具执行和停止判断。
- 最大工具执行轮数取自参数。

随后分别调用：

```python
run_loop(fake_model)
run_loop(fake_model_always_tool)
```

第一个应得到笔记回答；第二个应达到工具执行上限后停止。两次运行的消息和计数独立。

当前两个模型函数都是同步函数。真实 HTTPX 请求的异步约定在后续小节统一，再接入主项目。

## 4. 检查重点

- 更换模型时，循环体中是否还有写死的模型函数名？
- 传入的是函数本身，还是提前调用得到的回复字典？
- 两次运行是否分别初始化历史和计数？

这个小节先确认调用边界和函数参数的作用，再继续请求解析、返回约定与重试。

## 5. 本练习与模型数量、并发的关系

两个模拟函数分别代表正常回答和持续工具调用，用来验证同一循环的不同分支。当前真实模型仍只接 DeepSeek；函数可替换是调用边界的练习，不要求现在实现多供应商。

同一个模型可以接收多个互不依赖的请求。在单个工具闭环内，后一次模型请求需要前一步工具结果，因此必须先等待该结果。当前 `run_agent()` 的模型调用顺序是依赖链；`asyncio.gather()` 用在工具执行部分。

下一小步统一异步调用方式：两个模拟模型函数与 `run_loop()` 都改为 `async def`，循环用 `await call_model(messages)`。每次运行独立初始化消息与计数的规则继续保留。

同步入口采用一个事件循环，顺序运行两个场景：

```python
import asyncio

async def main():
    await run_loop(fake_model)
    await run_loop(fake_model_always_tool)

if __name__ == "__main__":
    asyncio.run(main())
```

这里统一的是调用约定，两个场景仍按顺序运行。实际并发用于互不依赖的操作，再按任务需要使用已经学过的并发方法。

## 6. 下一小步：模型请求失败时返回什么

当前项目的 `non_stream_message()` 在取得回复时返回字典，请求失败等情况下返回 `None`。本练习沿用这个约定：成功有消息，失败没有可追加的消息。

学员新增异步模拟函数 `fake_model_failed(messages)`，让它返回 `None`，并在 `main()` 中增加对该场景的调用。

循环接到回复后，先判断是否为 `None`，再追加历史或读取字段。失败时打印“模型请求失败”，直接 `return` 结束 `run_loop()`；当前循环外还有读取 `reply["content"]` 的代码，单独 `break` 会继续走到那里。

预期失败场景只提示并结束，不执行工具，不向历史添加 `None`，也不发生属性或下标访问错误。现有正常回答和达到上限两类场景继续保留。

## 7. 下一小步：观察 HTTP 429 的处理

位置：模型请求函数内部。循环已经能处理失败返回值，接下来判断请求函数在哪些错误下应再次尝试。

HTTP 429 表示服务端返回了限流响应。当前 `summarize_messages()` 的网络异常分支会等待后重试，但 HTTP 状态错误分支打印后立即返回 `None`；外层有三次循环不代表每类错误都会重试。

学员在 `code/agent_v1/test_summary_mock.py` 复用已有的 `MockTransport` 和 `AsyncClient`，导入并调用 `summarize_messages()`。假接口每次先打印“假接口收到请求”，再返回 `httpx.Response(429)`；传入一条普通 user 消息，打印摘要函数的返回值。此步先观察当前行为，保留原流式 mock 文件和实际请求函数。

预期当前假接口只被调用一次，函数返回 `None`。后续再按错误类型实现有限重试，并验证先 429 后成功的场景。

## 8. 只为 HTTP 429 补上有限重试

固定 429 的基线已由学员截图确认：一次请求后返回 `None`。当前只修改 `summarize_messages()` 的 `except httpx.HTTPStatusError` 分支，保留外层 `for attempt in range(3)`：

1. 取得 `error.response.status_code`，不是 429 时打印错误并返回 `None`。
2. 是 429 且 `attempt == 2` 时，已经用完三次尝试，打印最终失败并返回 `None`。
3. 其余 429 情况沿用 `await asyncio.sleep(2 ** attempt)`；分支结束后让原有 `for` 进入下一次尝试。

假接口继续固定返回 429。学员运行后预期打印三次“假接口收到请求”，最后返回 `None`，两次等待分别为 1 秒和 2 秒。成功场景下一小步再加；本步不代写或执行学员代码。

## 9. 第一次限流，第二次成功

固定 429 的三次尝试已由学员运行截图确认，重试分支静态核对正确。下一步保留现有失败场景，另写 `fake_response_then_success(request)` 和对应的异步测试场景，验证取得有效摘要后立即返回。

新场景使用函数外的 `request_count = {"value": 0}` 保存调用次数，假接口内每次把 `request_count["value"]` 加一。初始化不能放在假接口内部，否则每次调用都会从零开始；每次运行新测试场景前将计数复位。

第一次返回 429，之后返回 200。成功响应可通过 `httpx.Response(200, json=...)` 构造：这里的 `json` 接收字典，将其编码为响应 JSON 正文。数据结构是 `choices` 列表，第一项包含 `message` 字典，其中 `role` 为 `assistant`，`content` 为“摘要测试成功”。

新测试复用原有 MockTransport 与 AsyncClient 接线，检查函数返回值等于“摘要测试成功”、计数等于 2。同步入口使用已学的单个异步 main，顺序 await 原有失败场景和新成功场景。学员亲写和运行，教员仅审阅；不提前记为通过。

若复用同一个测试函数，应把预期结果和预期次数作为参数：固定 429 场景预期 `None`、3 次，恢复成功场景预期摘要字符串、2 次。每个场景开始时复位计数，两个假接口各自在每次被调用时递增；计数放在 main 的测试调用之后只会统计场景，不会统计请求。构造 `httpx.Response(...)` 后必须 `return` 给 MockTransport，单独创建对象不会自动返回。

## 10. 认证错误只请求一次

位置仍是模型请求层的重试策略。HTTP 401 表示认证未通过；当前策略是在收到这种响应后结束请求，返回 `None`。

保留两个已有场景，学员新增异步 `fake_response_unauthorized(request)`：按已有方式把请求计数加一，然后返回 `httpx.Response(401)`。在 main 增加 `await abc(fake_response_unauthorized, None, 1)`，复用每场景复位与两项断言。

该场景验证实际请求函数已有的非 429 分支。预期请求一次就返回 `None`，不进入等待重试。与前两个场景一起覆盖本轮策略：限流重试耗尽、重试后成功、认证失败立即结束。

## 11. 取消异常传给调用方

重试的三个场景已保留，学员报告成功，教员静态核对正确。接下来验证请求函数的另一项约定：普通请求失败返回 `None`，取消以 `asyncio.CancelledError` 向外传播，由调用方处理。实际 `summarize_messages()` 已有捕获取消后原样 `raise` 的分支。

学员新增异步 `fake_response_cancelled(request)`，每次请求把计数加一，随后 `raise asyncio.CancelledError`。这个假接口在模拟请求被取消时抛出的异常。

再新增独立异步测试 `check_cancellation()`，复位计数并复用现有 MockTransport 与 AsyncClient 结构；初始局部变量 `cancelled = False`，调用摘要函数时捕获 `asyncio.CancelledError` 并设为 `True`，随后检查 `cancelled is True` 和请求次数为 1。若函数意外正常返回（包括返回 None），取消标记仍为 False，断言应失败。在 main 顺序追加该测试，保留原三个场景。

这一小步检查模拟取消异常的传播。外部 Task.cancel 的实际投递以及退避等待期间的取消，需要后续另外观察，不能用本步的结果代替。

2026-10-19：学员已实现并报告测试成功，教员静态核对调用方捕获、取消标记和单次请求断言均正确；未独立运行。有限重试与本次模拟取消传播这组练习收束，下一小步转到第 5 章工具执行依赖。
