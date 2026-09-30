# Agent 工具与方法卡

## 使用标准

遇到新方法或工具，先说清五件事：

1. 用途：它解决什么问题？
2. 输入：传入什么值？
3. 输出：返回什么对象或值？
4. 副作用：会不会改数据、写文件或访问网络？
5. 错误：一个常见失败情形是什么？

不要求背内部实现，但要能把它放回 Agent 架构中的正确位置。

## 当前已用方法

### `httpx.AsyncClient.post`

- 用途：向 DeepSeek API 发送 HTTP 请求。
- 输入：URL、请求头、JSON 请求体。
- 输出：HTTP 响应对象 `Response`。
- 副作用：访问网络，可能产生 API 用量。
- 常见错误：地址错误、密钥无效、超时、非 `200` 状态码。
- 架构位置：模型请求。

```python
response = await client.post(
    url,
    headers=headers,
    json=request_body,
)
```

### `os.getenv`

- 用途：读取环境变量中的配置或密钥。
- 输入：环境变量名，例如 `"DEEPSEEK_API_KEY"`。
- 输出：字符串；变量不存在时通常是 `None`。
- 副作用：只读取当前进程环境，不写文件。
- 常见错误：变量名拼错或没有设置，导致密钥为空。
- 架构位置：程序启动配置。

```python
api_key = os.getenv("DEEPSEEK_API_KEY")
```

### `list.pop`

- 用途：取出并删除列表中的一个元素。
- 输入：列表下标，例如 `0`。
- 输出：被取出的元素。
- 副作用：原列表会改变。
- 常见错误：列表为空或下标不存在。
- 架构位置：模拟 Agent Loop 中取出下一条响应。

```python
current_response = responses.pop(0)
```

### `json.loads`

- 用途：把 JSON 文本转换成 Python 对象。
- 输入：JSON 字符串。
- 输出：通常是字典或列表。
- 副作用：不修改原字符串。
- 常见错误：字符串不是合法 JSON，触发解析错误。
- 架构位置：解析模型返回的 `tool_calls[].function.arguments`。

```python
arguments = json.loads(tool_call["function"]["arguments"])
```

### `BaseModel.model_validate`

- 用途：用 Pydantic 模型校验一次工具参数。
- 输入：字典或其他可校验数据。
- 输出：参数模型实例。
- 副作用：不执行文件操作。
- 常见错误：缺少必填字段、字段类型不符合，触发 `ValidationError`。
- 架构位置：工具执行前的参数校验。

```python
validated_args = argument_model.model_validate(arguments)
```

### `Path.read_text` / `Path.write_text` / `Path.replace`

- 用途：读取、写入文本，以及用临时文件原子替换正式文件。
- 输入：编码、文本或目标路径。
- 输出：读取返回字符串；写入和替换返回 `None`。
- 副作用：读写本地文件；`replace` 会覆盖目标文件。
- 常见错误：路径不存在、权限不足、临时文件和目标文件不在同一文件系统。
- 架构位置：会话持久化。

### `httpx.AsyncClient.stream` 与 `Response.aiter_lines`

- 用途：建立流式 HTTP 请求并逐行读取 SSE 数据。
- 输入：HTTP 方法、URL、请求头和 JSON 请求体。
- 输出：异步上下文中的响应对象，以及一行行的字符串。
- 副作用：访问 API 并产生用量；连接结束后释放响应资源。
- 常见错误：网络中断、超时、非 2xx 状态、某一行不是合法 JSON。
- 架构位置：流式模型请求。

### `asyncio.to_thread`

- 用途：在线程中运行同步文件工具，避免阻塞事件循环。
- 输入：同步函数及其参数。
- 输出：`await` 后得到该函数的返回值或异常。
- 副作用：会创建/使用线程并执行真实文件操作。
- 常见错误：函数本身抛异常；线程执行超过单工具超时。
- 架构位置：工具执行器。

### `asyncio.gather`

- 用途：并发等待一批工具任务并按传入顺序收集结果。
- 输入：多个 awaitable；常用 `return_exceptions=True` 做错误隔离。
- 输出：结果列表，或列表中的异常对象。
- 副作用：任务会同时开始执行，可能同时读写不同文件。
- 常见错误：未开启错误隔离时，一个异常可能让整批等待提前失败。
- 架构位置：多工具调用批次。

### `asyncio.wait_for`

- 用途：给单个工具设置最长执行时间。
- 输入：awaitable 和秒数 `timeout`。
- 输出：按时完成时返回工具结果；超时抛 `TimeoutError`。
- 副作用：超时时取消等待中的协程；线程里的同步函数可能仍需自行结束。
- 常见错误：只捕获网络异常，漏掉 `TimeoutError`，导致 Agent Loop 直接中断。
- 架构位置：单工具边界保护。

## 三个容易混淆的区别

### `model_json_schema()` 和 `model_validate()`

- `model_json_schema()`：生成给模型看的参数说明书。
- `model_validate()`：检查某一次实际传入的参数。

### 工具说明和工具执行

- `AgentTool`：描述工具叫什么、做什么、需要什么参数。
- 执行函数：真正读取、列出、写入或修改文件。

### 非流式和流式

- 非流式：等待完整响应后再处理，解析简单，保留为回退路径。
- 流式：响应分成多个片段陆续到达，当前 Agent v1 主线已使用；需要拼接正文、推理和工具参数，并处理 `[DONE]`、中断和解析错误。
