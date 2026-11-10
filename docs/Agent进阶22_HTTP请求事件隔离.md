# 进阶第22节 HTTP 请求的事件隔离

每次 `/chat` 请求已经创建自己的事件队列。当前 `run_agent_to_queue()` 将 `queue.put` 登记到全局 `listeners`，`emit()` 会调用表里的每个监听器。如果请求 A 和 B 同时登记，A 生成的一段文字就会进两个队列。`agent_lock` 让 HTTP 请求逐个执行，避免同时登记。

希望不同会话可以各自等待模型，同一个会话的任务按顺序更新存档。先让事件进入各自的请求队列，再把锁的范围缩到同一会话。

## 动手 按当前任务投递事件

继续用学过的 `ContextVar`。`event_source` 保存来源字符串，新增的 `task_listener` 保存当前任务的异步接收函数。`asyncio.create_task()` 默认复制创建者的上下文，请求可以各自设置接收函数。[Python asyncio 文档](https://docs.python.org/3.12/library/asyncio-task.html#asyncio.create_task)

1. 在 `agent_events.py` 中定义 `task_listener = ContextVar("task_listener", default=None)`。在 `emit()` 的循环前用 `listeners.copy()` 得到 `active_listeners`。用 `task_listener.get()` 取得当前接收函数，有值就加到这个副本。把 `for listener in listeners` 改为遍历 `active_listeners`。
2. 在 `http_api.py` 中改为导入 `task_listener`。在现有 `async with agent_lock` 内，把 `listener = queue.put` 和 `listeners.append(listener)` 的登记合并为 `listener_token = task_listener.set(queue.put)`，放在 `try` 之前。在 `finally` 用 `task_listener.reset(listener_token)` 替换 `listeners.remove(listener)`。

这里存的是 `queue.put` 函数本身。稍后 `emit()` 执行 `await listener(sub_event)` 时才把事件放进队列，`stream_events()` 再从该队列读取。

2026-11-10，接线静态通过。`emit()` 只在取到当前任务的监听器时调用 `append()`，HTTP 任务在 `finally` 恢复上下文。

## 动手 按会话加锁

两次请求如果同时从同一个存档读出旧历史，各自追加并保存，后保存的会覆盖先保存的历史。只读模式也会保存会话，所以同一会话的锁要覆盖整个 `await run_agent(...)`。

在 `http_api.py` 模块顶部添加 `session_locks = {}` 和 `from contextlib import nullcontext`。在 `run_agent_to_queue()` 中用 `session_id.lower()` 查字典。有锁就复用，首次访问才创建 `asyncio.Lock()` 并存回字典。锁键统一为小写，避免 Windows 默认大小写不敏感的文件名让两个名字写入同一个存档。[Microsoft 文件名大小写说明](https://learn.microsoft.com/en-us/windows/wsl/case-sensitivity)

用 `workspace_guard = nullcontext() if read_only else agent_lock` 选择工作区锁。把原 `async with agent_lock:` 换成 `async with session_lock, workspace_guard:`。普通请求会同时取得会话锁和全局工作区锁，只读请求的第二个上下文直接通过。监听器登记、`run_agent()` 和收尾清理都在这行下。[Python nullcontext 文档](https://docs.python.org/3.12/library/contextlib.html#contextlib.nullcontext)

会话锁留在字典中供等待中和后续的请求复用。不同只读会话可以并行。共享工作区允许只读请求看到其他请求写入的内容，本节并行场景使用两个只读会话。

2026-11-10，会话锁实现静态通过。监听器登记、Agent 执行与收尾都在同一锁范围内。

## 运行 两个只读会话

按 README 启动一份服务和两个 HTTP 客户端。如果服务已经在运行，重启以加载修改。两个客户端都输入 `/mode readonly`，分别输入 `/session http_demo_a` 和 `/session http_demo_b`。

A 提交「请读取 `minimal_loop.py`，逐个解释函数的用途，开头写会话 A」。A 还在输出时，在 B 提交「只回复会话 B」。观察 B 能否在 A 结束前显示自己的回复，以及两边是否各自只显示本请求的事件。

2026-11-10，学员反馈双会话运行正常。截图显示 A 收到代码讲解，B 收到「会话 B」。两份存档分别更新，B 为 14:08:15，A 为 14:08:29（Asia/Shanghai）。第 22 节完成，实跑范围是两个不同的只读会话。同一会话排队和普通任务之间排队的结论来自源码检查。
