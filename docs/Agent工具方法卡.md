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

## 三个容易混淆的区别

### `model_json_schema()` 和 `model_validate()`

- `model_json_schema()`：生成给模型看的参数说明书。
- `model_validate()`：检查某一次实际传入的参数。

### 工具说明和工具执行

- `AgentTool`：描述工具叫什么、做什么、需要什么参数。
- 执行函数：真正读取、列出、写入或修改文件。

### 非流式和流式

- 非流式：等待完整响应后再处理，当前主线使用它。
- 流式：响应分成多个片段陆续到达，适合实时显示，暂列为后续选做。
