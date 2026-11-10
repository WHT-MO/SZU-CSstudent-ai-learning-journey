# 阶段实战 最小循环独立变式

原来的 `minimal_loop.py` 演示一轮中执行一个工具。这次由学员新建 `code/agent_v1/mini_agent_practice.py`，用同一个假模型在一条回复中发起两次工具调用，练习把整批结果交回去。

1. 写一个同步 `get_note(topic)`，从字典返回笔记。例如 `loop` 对应「模型请求工具，收到结果后继续」，`async` 对应「await 等待异步结果」。
2. 写一个 `async def fake_model(messages)`。第一次回复带两个 `get_note` 调用，ID 分别为 `note_1`、`note_2`，`function.arguments` 分别是 JSON 字符串 `'{"topic": "loop"}'` 和 `'{"topic": "async"}'`。收到这两个 ID 对应的工具结果后，返回一条包含两条笔记的普通回答。
3. 写 `run_loop()`。先把模型的 `assistant` 回复放入历史。遍历这一批 `tool_calls`，逐个用 `json.loads()` 解析参数，执行 `get_note()`，把结果用 `role="tool"` 和对应的 `tool_call_id` 放回历史。整批处理完后再请求模型，拿到普通回答就结束。

运行一次固定输入「查两条笔记」。最终回答应包含两条不同的笔记，历史顺序是 `user → assistant（两条调用）→ tool（note_1）→ tool（note_2）→ assistant（最终回答）`。整个过程是两次模型请求，中间执行同一批中的两个工具调用。

2026-11-10，正常批次实跑通过。学员截图显示最终回答同时包含 `loop` 和 `async` 两条笔记。

## 单条参数出错时继续处理整批

在假模型里把 `note_1` 的参数临时改成不完整的 JSON 字符串 `'{"topic":'`。`note_2` 继续使用原来的 `async` 参数。

在遍历 `tool_calls` 的 `for` 内，用 `try` 包住 `json.loads()`。`except json.JSONDecodeError` 给 `result` 赋值为 `{"role": "tool", "content": "参数 JSON 格式错误"}`。`else` 里用解析成功的 `argument` 调用 `get_note()`，同样把结果赋给 `result`。两条路径都在 `try/except/else` 之后补 `tool_call_id` 并追加到历史，这两行放在 `for` 内。

运行后应收到 `note_1` 的参数错误和 `note_2` 的正常笔记。`try` 放在每条调用内，才能把错误留在这一条调用上。要重跑正常批次，把 `note_1` 的参数改回 `'{"topic": "loop"}'`，循环中的错误处理可以继续使用。

2026-11-10，异常批次实跑通过。截图同时显示「参数 JSON 格式错误」和「await 等待异步结果」。源码确认两条分支都经过同一个 `tool_call_id` 回填位置。
本次保存的脚本默认运行异常批次。
