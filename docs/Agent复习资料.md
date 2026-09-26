# Agent 开发复习资料

这份资料总结当前已经完成的基础 Agent：模型能够根据用户请求选择工具，程序执行工具，把结果交给模型，模型再生成最终回答。

## 一、完整架构

```text
用户输入
    ↓
Agent 组装 messages 和 tools
    ↓
请求模型
    ↓
模型返回普通回答，或返回 tool_calls
    ↓
解析工具名和 arguments
    ↓
校验参数
    ↓
执行工具
    ↓
生成 role=tool 的工具结果消息
    ↓
把 assistant 消息和工具结果加入对话历史
    ↓
再次请求模型
    ↓
没有 tool_calls 时输出最终回答
```

核心思想：模型负责决定下一步，程序负责执行真实操作。

模型不能直接读取电脑文件。模型只能提出：

```json
{
  "name": "read_file",
  "arguments": {"path": "ideas/todo.txt"}
}
```

程序收到后才真正调用 `read_file()`。

## 二、当前文件职责

```text
code/agent_v1/
├── tool_schemas.py  参数模型、工具说明、工具注册信息
├── tools.py         workspace 路径安全和四个文件工具
├── agent_runner.py  API 请求、Agent Loop、工具分发
├── agent.py         第一周事件系统实验
└── workspace/       Agent 允许访问的工作区
```

划分原则是“一类职责一个模块”，不是“一个函数一个文件”。

## 三、四个文件工具

### `read_file`

读取 workspace 内的文件。

### `write_file`

写入或覆盖文件内容。

### `list_files`

列出目录的直接子项。

### `edit_file`

找到唯一的旧文本并替换成新文本。

`edit_file` 的边界：

- `old_text` 不能为空
- 找不到旧文本时失败
- 旧文本出现多次时失败
- 只替换一次，避免误改多个位置

## 四、工具调用的两张表

### 参数模型表

```python
tool_arg_models = {
    "read_file": ReadFileArgs,
    "write_file": WriteFileArgs,
}
```

作用：根据工具名找到 Pydantic 参数模型。

```python
validated_args = argument_model.model_validate(arguments)
```

### 执行函数表

```python
tool_functions = {
    "read_file": read_file,
    "write_file": write_file,
}
```

作用：根据工具名找到真正执行的 Python 函数。

完整关系：

```text
工具名
  ├─ tool_arg_models → 参数模型 → 校验 arguments
  └─ tool_functions  → 执行函数 → 得到工具结果
```

## 五、Agent Loop

```python
while True:
    if 没有 tool_calls:
        输出 content
        break

    逐个执行 tool_call
    把工具结果加入 messages
    再次请求模型
```

为什么需要循环：模型可能先列目录，再读取文件，再根据文件内容继续操作。工具调用次数不能假设只有一次。

为什么需要 `max_turns`：模型可能重复调用工具，因此设置最大轮数防止无限循环。

## 六、消息结构

### 用户消息

```python
{"role": "user", "content": "请读取文件"}
```

### 模型工具调用消息

```python
{
    "role": "assistant",
    "tool_calls": [...],
}
```

### 工具结果消息

```python
{
    "role": "tool",
    "tool_call_id": tool_call_id,
    "content": tool_content,
}
```

`tool_call_id` 必须和模型发出的调用 ID 对应，否则模型无法知道结果属于哪个调用。

## 七、已经处理的边界

### 输入和配置

- API Key 缺失
- 空用户输入
- `.env` 文件配置

### 模型响应

- HTTP 请求超时
- 网络请求失败
- API 返回 4xx/5xx
- 返回内容不是合法 JSON
- 缺少 `choices`
- `choices` 为空
- 缺少有效 `message`

### 工具调用

- 缺少调用 ID
- 缺少 function 对象
- 缺少工具名
- 缺少 arguments
- arguments 不是合法 JSON
- 未知工具
- 参数字段缺失或类型错误
- 一次返回多个 tool_calls
- 最大循环次数限制

### 文件操作

- 文件不存在
- 路径超出 workspace
- 路径是目录而不是文件
- 没有访问权限
- 文件不是 UTF-8
- 编辑文本为空
- 编辑文本不存在
- 编辑文本出现多次

## 八、路径安全

Agent 只允许访问：

```text
code/agent_v1/workspace/
```

安全检查步骤：

```python
workspace_path = workspace_root.resolve()
candidate_path = (workspace_path / relative_path).resolve()
candidate_path.relative_to(workspace_path)
```

`resolve()` 会把相对路径和 `..` 解析成真实路径；`relative_to()` 用来确认解析后的路径仍然位于 workspace 内。

## 九、重要 Python 方法

| 方法或语法 | 作用 |
|---|---|
| `os.getenv()` | 读取环境变量，不把密钥写进代码 |
| `httpx.AsyncClient` | 创建异步 HTTP 客户端 |
| `client.post()` | 向 API 发送 POST 请求 |
| `await` | 等待异步操作完成 |
| `async with` | 自动管理异步资源的打开和关闭 |
| `response.raise_for_status()` | 让 4xx/5xx 变成异常 |
| `response.json()` | 把 JSON 响应转成 Python 对象 |
| `dict.get()` | 安全读取字典键，缺失时使用默认值 |
| `list.append()` | 把一个元素加入列表 |
| `list.extend()` | 把另一个列表的元素逐个加入 |
| `list.pop(0)` | 取出并删除列表第一个元素 |
| `json.loads()` | 把 JSON 字符串转成 Python 对象 |
| `model_validate()` | 按 Pydantic 模型校验参数 |
| `Path.resolve()` | 得到规范化的绝对路径 |
| `Path.relative_to()` | 检查路径是否位于指定目录内 |
| `Path.read_text()` | 读取文本文件 |
| `Path.write_text()` | 写入文本文件 |
| `Path.iterdir()` | 遍历目录直接子项 |
| `str.count()` | 统计子字符串出现次数 |
| `str.replace()` | 替换字符串内容 |
| `asyncio.run()` | 从同步入口启动异步函数 |

## 十、流式和非流式

当前使用非流式请求：

```python
"stream": False
```

特点：等待模型完整生成后一次性收到结果，适合先学习 Agent Loop 和工具调用。

流式请求会分多段收到模型输出，适合实时显示文字，但要额外处理分片、拼接、工具调用结束等问题。等非流式 Agent 稳定后再学习流式。

## 十一、当前学习进度

已完成：

1. Python 异步基础
2. 任务、Future 和异常
3. 事件状态和监听器
4. Pydantic 参数模型
5. 工具说明和 JSON Schema
6. 工具调用解析
7. 多工具调用
8. Agent Loop
9. 文件工具
10. 路径安全
11. API 和文件错误处理
12. `.env` 密钥管理
13. Agent 代码模块化

后续方向：

- 让用户输入动态进入 Agent
- 增加更完整的工具错误回传
- 流式响应
- 对话历史和上下文管理
- 工具调用日志
- 更完整的测试
- 将 Agent 做成可复用项目
