# Agent 第 7 章：把工具通知接回项目

> 2026-10-20 开始通知、四种结束状态与显示、emit 监听器普通异常隔离均已静态检查通过，进入第 8 章。复用已有监听器知识，由学员亲写；不新增独立验证脚本，不由教员代改学生源代码。

## 1. 事件在这里的用途

事件是程序发给其他函数的一条通知。执行器发出“准备执行工具”的字典；显示函数收到后打印。这样执行过程与具体显示方式之间通过通知连接，以后需要日志时可增加接收函数。

本次只增加 tool_start：表示执行包装准备调用底层工具，不承诺工作线程在这一瞬间已开始。实际工具内容仍通过原来的工具结果返回模型。

## 2. 本次由学员完成的范围

新建 `code/agent_v1/tool_events.py`，约定如下：

- `async def show_tool_event(event)`：接收事件字典，遇到 type 为 tool_start 时，打印“准备执行工具：”及 tool_call_id；不修改传入字典，无需返回内容。
- `listeners`：保存监听器函数本身，首项为 show_tool_event；列表内不写函数调用。
- `async def emit(event)`：遍历 listeners，逐个 await listener(event)；不追加聊天消息，不需要返回值。

在 agent_runner.py 导入 emit，在 execute_validated_tool 进入现有工具执行 try 块之前，await emit，传入 `{"type": "tool_start", "tool_call_id": tool_call_id}`。

此处 await 表示等待本次通知处理完再继续；调用 emit 得到协程，等待它完成后不需要接收工具结果。与 execute_validated_tool 返回 role=tool 字典的用途不同。

tool_events.py 被导入时只建立定义和监听器列表，不自行启动 asyncio.run。旧 agent.py 是会在导入时运行演示的练习文件，不将它作为这次通知模块直接导入。

## 3. 当前版本的边界

逐个 await 监听器会让后续工具执行等待通知处理；监听器抛出的异常在未捕获时向外传播。这是本次简单实现的行为，后续实际任务再处理监听器隔离。结束通知与状态的任务见第 4 节，最新实现状态见第 6 节。

完成标准是这条实际调用关系接通：execute_validated_tool → emit → show_tool_event → 原工具执行。学员保存后按请求静态审阅，不把额外测试文件作为通过条件。

2026-10-20 学员回复 ok 后回读：runner 已导入 emit，并在 execute_validated_tool 的 try 前 await 开始通知；tool_events.py 中正确传递 event。开始通知按静态检查通过，教员未运行程序，未独立复现编辑器提示是否消失。

## 4. 下一项动手：结束通知与状态

本次把正常完成、普通错误、等待超时与取消四种结果的通知一起接入。执行包装决定事件内容；监听器决定如何显示，emit 仍只负责分发。

事件约定：`{"type": "tool_end", "tool_call_id": tool_call_id, "status": status}`。这是本项目的程序事件结构，不是模型接口新字段。tool_end 表示本次执行包装结束等待或得到结果；超时与取消不证明工作线程已经停止，也不表示文件操作成功。

| 所走分支 | status |
| --- | --- |
| try 中 await 正常得到工具返回值 | success |
| 文件操作异常或未预期 Exception | error |
| TimeoutError | timeout |
| CancelledError | cancelled |

由学员在 execute_validated_tool 中完成：正常 await 之后记录 success，两个普通异常分支记录 error，超时分支记录 timeout；所有 except 之后、原 return 之前，统一 await 发出 tool_end。该公共通知与 try 同级缩进。

取消分支直接退出，故在原 CancelledError 分支中单独 await 发出 cancelled 的 tool_end，随后保留 raise。取消不会再走到公共结束通知；不把取消转成普通工具结果。现有错误文本与 make_tool_result 返回约定继续使用。

show_tool_event 增加 tool_end 处理，按 status 显示“工具成功”“工具执行失败”“工具等待超时”“工具等待取消”以及调用 ID。开始通知继续保留。不要只根据 tool_end 打印“执行成功”，也不根据工具返回的自然语言推断状态。

本任务已部分保存，最新静态检查见第 6 节。保存后审阅实际分支与通知位置，不增加独立测试脚本；监听器异常隔离后续再处理。

## 5. 为什么使用监听器，而不直接 print

只需固定终端输出的小程序，直接 print 足够。当前显示函数仍使用 print；监听器让执行器通过事件把信息交给显示函数，执行过程和展示方式各有位置。

只有一个显示监听器时，实际输出效果与直接 print 可以相同。以后有日志或界面需求时，可增加接收同一事件的函数并注册到 listeners，执行器已有的各状态分支仍使用原来的事件。调整显示文字也集中在显示函数中。这里采用此结构同时是把教材的事件思路接回现有项目，不把它说成所有 Agent 必须具备的框架。

代价是多一层传递和注册管理，没有自动提升速度。当前 emit 逐个 await，慢监听器会推迟主流程；异常未捕获时也会向外传播。监听器异常处理留给后续实际任务。

## 6. 当前静态检查与修正任务

学员回复完成并询问监听器用途。回读已保存源码：success、timeout 和两类 error 的赋值正确，公共 tool_end 位于 except 之后、return 之前。仍有两处未接完整：

1. CancelledError 分支仅设置 status 后 raise，不会到达公共结束通知；应在 raise 前单独 await 发出 cancelled 的 tool_end。
2. show_tool_event 仍仅处理 tool_start；需增加 tool_end，按 success/error/timeout/cancelled 显示“工具成功”“工具执行失败”“工具等待超时”“工具等待取消”及调用 ID。

本轮先回答设计取舍，再直接衔接以上修正，不增加验证脚本，不提前记为整项完成。教员未代改或执行学生源代码。

后续学员回复完成，回读确认：取消分支已在 raise 前 await 发出 cancelled 的 tool_end；显示函数已覆盖 success、timeout、error、cancelled。两项修正均静态检查通过，未运行程序，继续第 7 节。

## 7. 当前动手：隔离监听器普通异常

当前通知在执行包装的工具 try 前和工具结果 return 前运行。监听器普通异常向外传播时，可能阻止工具开始，或者让已完成的工具无法返回结果。显示与日志接收函数是观察者，其普通失败采用打印原因、继续下一监听器的策略。

相关原理一次讲清：

- 执行器根据工具状态产生事件，观察者读取事件，不修改事件字典或借此决定是否允许工具运行。多个监听器收到同一字典，修改会影响后面的接收者。
- 当前 emit 顺序 await，前一个处理完再叫下一个，工具也会等待 emit 完成。普通异常隔离不会自动解决监听器一直不返回的情况；复杂排队或后台分发按真实需求以后再选。
- CancelledError 继续 raise，允许整个任务响应取消；普通显示或日志错误则捕获 Exception，打印原因后继续。不将取消当作普通显示失败吞掉。
- 将来需要“允许/拒绝执行”的回调时，要单独规定返回值和失败处理；那类决策回调影响执行，不能直接沿用观察者失败忽略的规则。当前不增加这种接口。
- 当前 listeners 在模块加载时建立一次；每次运行 Agent 不重复追加同一显示函数。将来动态注册按使用范围配对移除，避免重复通知或残留资源。本节不新增注册与清理接口。

由学员只修改 tool_events.py 的 emit：把 try 放进 for 循环，包住单次 await listener(event)；CancelledError 分支 raise；Exception 分支直接 print 错误类型和原因，然后让循环继续。错误提示使用 print，不再调用 emit，避免再次触发同一个出错监听器。这里的 asyncio 导入用于识别 CancelledError。

学员首次保存时 try 包住整个 for，错误后会跳过剩余监听器。学员随后已调整为 for 外层、try 与两个 except 内层：CancelledError 向外 raise、Exception 打印原因后继续下一监听器，最新静态检查通过。未运行程序，不增加独立测试或故障注入任务；监听器卡住、反复取消等情况不据此宣称已处理。

本节基础实现已收束，直接进入 [第 8 章：大工具输出与分段读取](Agent第08章_大工具输出与分段读取.md)。
