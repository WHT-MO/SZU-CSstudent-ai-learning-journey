# Agent v1 架构地图

## 一句话定义

Agent = **模型 + 会话状态 + 工具注册表 + 工具执行器 + 循环控制**。

模型负责判断下一步要回答还是要调用工具；程序负责校验、执行工具，并把结果交回模型。

## 最小数据流

```text
用户问题
  ↓
messages（会话状态）
  ↓
请求模型（默认走流式；非流式保留为回退）
  ↓
模型响应
  ├─ content：模型已经能回答 → 输出并结束
  └─ tool_calls：模型需要工具
        ↓
      读取工具名和 arguments
        ↓
      Tool Registry（工具注册表）查找工具
        ↓
      Pydantic 参数模型校验
        ↓
      执行真实工具
        ↓
      生成 role=tool 的结果消息
        ↓
      追加回 messages，再次请求模型
```

## 五个模块

### 1. 会话状态 `messages`

保存用户消息、模型消息和工具结果。模型每次只能根据传入的消息理解上下文。

### 2. 模型请求

程序把 `model`、`messages`、工具说明和请求选项发送给 API。当前主路径用 SSE 流式读取；非流式 `request_message()` 作为简单回退。流式解析会分别累加正文、`reasoning_content` 和工具调用分片，结束后才形成完整 assistant 消息。

### 3. 工具注册表

根据工具名找到对应的参数模型和执行函数。例如：

```python
tool_arg_models = {
    "read_file": ReadFileArgs,
    "write_file": WriteFileArgs,
    "list_files": ListFilesArgs,
    "edit_file": EditFileArgs,
}
```

### 4. 参数校验与工具执行

模型返回的 `arguments` 先从 JSON 字符串转换成 Python 字典，再用参数模型校验。校验通过后，才执行真实文件操作。

工具说明书告诉模型“怎么调用”；执行函数才真正读写文件。两者不是同一件事。

### 5. Agent Loop

循环不是“不断运行代码”这么简单，它表示：

```text
模型要工具 → 执行工具并回传结果 → 再问模型
模型给最终回答 → break
```

必须有停止条件，例如最终 `content`、最大轮数或错误停止，避免工具调用死循环。

## 当前学习位置

- W1：异步任务、Future、事件通知已完成。
- W2 第 4 格：四个文件工具的参数 schema 已完成。
- W2 第 5 格：已练习模拟 `tool_calls`、注册表、参数校验和 Agent Loop 判断。
- W2：四个文件工具、真实工具调用和 Agent Loop 已完成。
- W3：会话保存、`/reset`、裁剪、原子写入、流式响应和 reasoning 保存已完成。
- W4：多工具并行、单工具超时和错误隔离已完成；当前进入架构复盘和后续可靠性设计。

## 当前不做的事情

- 上下文压缩、成本账、429 退避和多会话管理尚未进入 Agent v1 主闭环，按计划作为后续可靠性课题。
- Pydantic schema 不会自动执行工具。
- 模型提出 `tool_calls` 不代表文件已经被读取或修改。
