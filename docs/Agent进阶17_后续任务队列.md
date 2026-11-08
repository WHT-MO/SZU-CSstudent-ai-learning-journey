# 进阶第17节 后续任务队列

/steer在当前任务的下一次模型请求前补充消息。后续任务队列将保存一项新的请求，等当前任务结束后再启动。CLI的command_loop现在通过提交队列等待回车，后台任务结束时也需要给它一条通知，才能在没有新按键时继续调度。

## 当前动手 让命令循环收到结束通知

1. 在cli.py的main里把submitted_inputs改名为command_events，并作为队列传给build_terminal_ui。界面按回车时送入字符串，后台Task结束时送入Task对象。
2. 在创建agent_task之后，调用agent_task.add_done_callback(command_events.put_nowait)。注册的是put_nowait方法，Task结束时由asyncio把它自己作为参数传给该方法。正常结束、异常和取消都属于完成状态。[Python Task文档](https://docs.python.org/3.12/library/asyncio-task.html#asyncio.Task.add_done_callback) · [回调参数](https://docs.python.org/3.12/library/asyncio-future.html#asyncio.Future.add_done_callback)
3. 在command_loop的while开头先取item = await command_events.get()。若isinstance(item, asyncio.Task)，就处理结束通知。只有item is agent_task时将agent_task与steering_queue清空，然后continue。其他消息是界面提交的字符串，用item.strip()取得user_prompt后进入原命令处理。
4. 将/stop分支末尾的agent_task清理移到完成通知的分支。/stop仍取消并等待当前任务。Task标识保证较晚到达的旧结束通知只会处理它自己的任务。

2026-11-08 23:12首版回读确认队列传递、完成回调和/stop清理位置正确。第155行get已经取出消息，普通输入直接用item.strip()。先判断isinstance(item, asyncio.Task)，再在内部判断item is agent_task，清理当前任务引用。continue放在类型判断内，与身份判断同级，处理完任意结束通知都回到等待。

2026-11-08 23:25回读确认所有Task通知先分流，只有当前任务的通知清理状态。字符串直接strip。完成通知接线静态通过。

## 当前动手 排队并启动下一项

在cli.py导入collections.deque。在command_loop中、while之前建立pending_requests = deque()。每条请求用(prompt, session_id, read_only)保存提交时的任务文字、会话和模式。append放到队尾，popleft取队首。

在command_loop内、while之前定义普通函数start_next_request，声明nonlocal agent_task, steering_queue。agent_task有引用或等待队列为空时返回。空闲且有等待请求时，popleft并解包三个字段，创建新的steering_queue，使用这次出队的参数调用run_cli_task。沿用app.create_background_task和add_done_callback，将原普通输入分支的启动逻辑移到这里。

在当前Task的结束通知分支清空agent_task和steering_queue后调用start_next_request。在/steer和最终else之间增加command == "/queue"分支。用argument.strip()取任务文字，空文字提示输入待办任务，非空则append请求三元组并调用start_next_request。普通输入获准启动时也append其三元组，再调用同一个启动函数。两种入口从同一队首调度。

/stop取消当前任务，完成通知使下一项继续启动。/exit等待当前任务取消后关闭应用，待执行请求存于这次CLI的内存队列。接好后用一次运行中排入下一项的操作核对自动衔接。

2026-11-09源码静态通过。两个提交入口都以单个三元组入队，启动函数创建各自的steering_queue并登记完成回调。命令循环收到当前Task的结束通知后清理并从队首启动下一项。核对时运行日志尚无本节记录。课程接到[审阅工作流检查点](Agent进阶18_审阅工作流检查点.md)。
