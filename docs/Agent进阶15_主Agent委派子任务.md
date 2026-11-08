# 进阶第15节：主Agent委派子任务

> 2026-11-05开始。第14节固定分工、独立会话、TaskGroup与父流程汇总已完成。本节将单个只读审阅子任务作为主Agent可调用的工具，源码由学员编写。

## 1. 新增行为

第14节由Python预先决定启动逻辑、异常两个任务。本节增加delegate_review工具：主模型根据用户任务决定是否调用、审阅哪个文件以及采用哪个方向；工具函数负责启动子Agent并将结果返回，主Agent继续自己的循环。模型决定任务安排，Python执行明确的调用，两者职责分开。

输入沿用已学会的参数模型、JSON Schema、校验和工具注册。子Agent仍使用同一个模型、独立会话和read_only_guard；结果继续复用结构化审阅及证据校验。实际用途前提必须显式传入，不能假定子Agent继承父聊天。

## 2. 已完成：定义委派工具的输入

在tool_schemas.py导入typing.Literal，新增DelegateReviewArgs(BaseModel)。三个字段都必填，均用Field(description=...)说明意义：

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| path | str | 相对workspace的目标Python文件路径 |
| focus | Literal["logic", "exceptions"] | 逻辑/控制流程/返回值，或异常处理/资源清理 |
| review_context | str | 代码用途、运行入口、支持范围及必要约定，供子任务确定什么算当前缺陷 |

Literal将取值限定为列出的几个值，例如Literal["fast", "careful"]只接受fast或careful；不是要求自己写if校验。Pydantic会把该约束写进JSON Schema并验证模型传来的参数。focus的description需明确logic与exceptions各指什么，path及review_context同样给出模型可读的说明。

2026-11-05 22:57回读确认：Literal导入、三个必填字段、限定值及Field说明均已写好，静态通过。主模型随后依据工具说明填这三个参数，现有参数校验器生成DelegateReviewArgs对象，再交给执行函数。

## 3. 已完成：实现委派工具函数

在code/agent_v1新建delegation_tools.py，实现async def delegate_review(args: DelegateReviewArgs) -> str。args是现有校验器生成的参数对象；函数复用review_workflow，最终返回报告文字，交给主Agent读取。

函数完成一条完整的数据流：按args.path读取源码；按args.focus选择上节两个审阅方向中的一个，与args.review_context组成scope；为本次委派生成新session_id；await collect_review_findings取得ReviewResult；validate_review_evidence核对原文；render_review_report生成文字并返回。它不负责保存报告，已有工具执行器会把异常转为工具失败结果。

会话名使用标准库uuid4生成随机标识，例如：

```python
from uuid import uuid4
session_id = f"delegate_{uuid4().hex}"
```

uuid4().hex是32位十六进制字符串，适用于当前会话名规则；调用应放在函数内部，每次委派生成一次。这样即使两次委派同一个文件，也不会加载前一次的审阅历史。

DelegateReviewArgs和tools.resolve_workspace_path可在模块顶部导入。review_workflow的collect_review_findings、validate_review_evidence、render_review_report放在delegate_review函数体内导入：等工具实际执行才加载工作流，避开后续registry→delegation_tools→review_workflow→agent_runner→registry的导入环。此处函数内导入是为处理实际依赖关系，不要求其他导入照搬。

本步先静态审阅函数，随后完成事件来源、工具预算与注册，再进行一次实际委派。

2026-11-05 23:13首版回读：函数内工作流导入、每调用生成会话名、await收集、证据校验及返回报告的接线正确。第9行直接args.path.read_text会失败，因为参数类把path定义为str；需从tools导入resolve_workspace_path，先将相对字符串解析为workspace内的Path对象，再调用read_text。scope目前直接拼logic/exceptions标签，建议按两方向映射为具体检查范围再拼review_context；这不是Python类型错误，而是把审阅范围明确传给子模型。ReviewResult被用作局部变量名虽不惯用，当前没有遮蔽已导入类或改变行为，不设额外修改门槛。未运行或注册工具。

2026-11-05 23:21回读：已正确导入resolver并把args.path转换为Path读取源码。新写args.focus["logic"]/args.focus["exceptions"]赋值会失败：focus在运行时是一个字符串，Literal只限制可选字符串值，不创建字典。应另建focus_descriptions字典保存两段说明，用focus_descriptions[args.focus]选中说明再与review_context拼scope，保留传入的args.focus。另将collect_review_findings及render_review_report的路径参数保持为args.path，相对字符串用于任务说明和报告；局部Path仅用于父函数读文件。传Path在当前f-string实现中未必报错，但不符合这两个函数现有str接口约定，不误报为必然类型异常。当前仍修执行函数，尚未推进事件来源/预算或注册。

2026-11-05 23:27回读：已另建focus_descriptions字典、用args.focus选具体范围，collector/render均传args.path相对字符串，Path用于读取。输入、独立会话、用途/方向、收集、证据核对和报告返回静态通过；不为局部变量大写或scope换行后的空格加门槛。该函数尚未注册或实际运行。

## 4. 已完成的事件来源标记

现有主Agent和子任务共用agent_events.listeners，CLI的show_model_event和HTTP客户端会直接打印所有text_delta。委派接入后，子任务用于结构化解析的JSON也会进入相同显示通道。为每条事件增加source字段，显示函数后续便能识别主回答与子任务过程；用量监听器仍累计两者已报告的usage。

本项目自定义source约定：主任务为main，委派子任务为本次生成的delegate_会话名。source供事件消费者读取，不改变工具参数Schema。

先在agent_events.py导入标准库ContextVar，在模块顶部创建event_source = ContextVar("event_source", default="main")。event_source是一个上下文变量对象，event_source.get()取得当前执行上下文中的来源字符串；未设置时返回main。asyncio任务可在各自上下文保存不同的值，适合并发子任务，不能用一个共享普通字符串替换它。参见[Python 3.12 contextvars文档](https://docs.python.org/3.12/library/contextvars.html)。

在emit(event)的监听器循环之前复制本次event字典，给副本添加source，值取event_source.get()，之后将副本交给原有listener。可用event.copy()获得字典副本；各事件type及原字段继续保留。当前步骤只接标记，所有未切换来源的任务都会带source=main。

2026-11-08 14:42回读确认agent_events已创建默认值为main的event_source。emit先复制事件，再为副本填写source并分发，静态通过。

## 5. 已完成的委派来源切换

在delegation_tools.py顶部从agent_events导入event_source。在现有await collect_review_findings之前用source_token = event_source.set(session_id)把当前来源设置成本次委派会话名。collect_review_findings调用子Agent，子Agent发事件时emit读取该来源。

将收集结果的await语句放进try，在finally调用event_source.reset(source_token)。source_token是set返回的对象，reset用它恢复设置之前的值。正常完成、异常和取消都经过finally。证据校验和报告渲染放在try/finally之后。完成此步再让CLI和HTTP显示端根据来源筛选。

2026-11-08 14:51回读确认delegate_review以本次session_id设置来源，收集结果的await在try内，finally使用对应的source_token恢复来源。证据核对和报告渲染都在恢复后执行，静态通过。

## 6. 已完成的正文筛选

在cli.py的show_model_event和http_client.py解析SSE事件之后的text_delta分支中，正文打印需同时满足type为text_delta及event.get("source", "main")等于main。缺少source的事件按main处理，兼容旧服务端的事件格式。

source条件属于打印正文的分支。CLI的collect_usage负责累计主任务与子任务报告的model_response_end，工具状态和HTTP任务结束也有各自的分支。HTTP服务端会把事件字典序列化给客户端，客户端读取其中的source。

2026-11-08 15:05回读确认CLI和HTTP客户端的text_delta分支均按source筛选，缺省按main处理。CLI收集器累计模型响应上报的用量，静态通过。

## 7. 已完成的等待时间与注册

父循环的execute_validated_tool用wait_for等待整个工具协程。当前统一配置为10秒，一次委派内的模型请求、工具执行和报告处理都在这段等待中。首版把委派设为45秒，给HTTP客户端当前60秒的读取超时留出余量。读取超时是等待下一块数据的时长，见[HTTPX超时文档](https://www.python-httpx.org/advanced/timeouts/#fine-tuning-the-configuration)。

1. 在tool_registry.py的派生字典旁建立tool_timeouts。在现有遍历中，带timeout_seconds的条目用info["function"]作为键，将info["timeout_seconds"]作为值。函数对象正好对应执行器的tool_function参数。
2. 在agent_runner.py导入tool_timeouts。在execute_validated_tool里用tool_timeouts.get(tool_function, 10)为现有wait_for取得timeout参数，未单设的工具按10秒执行。
3. 在tool_registry.py导入DelegateReviewArgs和delegate_review，新增delegate_review条目。args_model和function指向对应对象，description说明委派独立只读子任务审阅Python文件并返回报告，requires_serial为False，timeout_seconds为45。注册后派生字典会保存delegate_review函数与45的对应关系。

子任务各自使用独立会话，已有read_only_guard只允许读取、列目录和搜索。由普通模式的主Agent发起委派。接好后用一次明确要求委派的实际任务核对父循环调用、独立子会话和结果回填。

2026-11-08 15:39回读确认委派参数类和函数已注册，requires_serial为False。tool_timeouts按函数保存45秒，执行器在wait_for处查表，默认10秒。现有配置静态通过。

## 8. 已完成的CLI委派

用项目.venv运行cli.py，在新会话`/session lesson15_demo`中让主Agent调用delegate_review一次，path为minimal_loop.py，focus为logic。review_context说明这是Python 3.12+教学脚本，main演示正常回答、达到工具轮数上限和模型请求失败，只检查固定演示中的实际逻辑问题。请求工具返回后用一两句话概括报告。

2026-11-08 15:44实际运行完成。父会话lesson15_demo记录一次delegate_review，path为minimal_loop.py，focus为logic。匹配调用编号的工具结果返回审阅报告，候选问题为0，父Agent随后概括结论。新delegate_子会话独立读取技能说明和minimal_loop.py，并返回空findings。子任务请求run_python和再次委派时，已有只读策略分别拒绝了两项操作。

终端结果与运行记录一致。任务耗时31.82秒，收到6条用量报告，累计输入13912、输出3787、合计17699。第15节的实际委派目标完成。

## 9. CLI输入行重绘的初版

学员观察到后台任务启动后立刻出现下一条输入提示，任务完成时光标却停在统计输出的下方。cli.py启动后台Task后，主循环继续用asyncio.to_thread等待input。input在开始时写一次提示，后台print随后把它滚到上方。任务完成时同一次input仍在等回车。

学员在requirement.txt加入prompt-toolkit>=3,<4并在项目虚拟环境安装3.0.53。main创建一个PromptSession，patch_stdout覆盖完整输入循环，prompt_async按会话名绘制提示。参见[prompt_toolkit异步提示文档](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html#prompt-in-an-asyncio-application)。

2026-11-08 16:09静态核对通过异步读入。初版若去掉flush=True，代理会按换行缓冲正文，流式事件的显示粒度变为整行。学员确认同时需要逐块显示与固定输入。2026-11-08 16:25回读时正文仍使用flush=True，当前改用分区界面。

## 10. 固定输入并逐块刷新输出

用prompt_toolkit的一个全屏Application绘制两个TextArea。上方输出区保存正文和日志，下方输入区固定一行并保留输入草稿。正文片段到达时更新上方缓冲并请求重绘。回车提交整行后，CLI命令循环照常识别普通任务、/stop和/steer。输入提交队列负责界面到命令循环的传递，steering_queue负责命令循环到运行中的Agent。全屏布局使用终端的备用屏幕，退出后回到原终端画面。参见[prompt_toolkit全屏布局文档](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/full_screen_apps.html)。

当前学员在code/agent_v1/terminal_ui.py写build_terminal_ui(submitted_inputs, get_prompt)。submitted_inputs由CLI创建，是保存已提交字符串的asyncio.Queue。get_prompt是CLI传入的零参数函数，返回带当前会话名的提示。

1. 建只读的output_area，使用TextArea(read_only=True, focusable=False)。它用于保存和显示程序追加的文字。
2. 建单行input_area，使用TextArea(height=1, multiline=False, wrap_lines=False)，prompt取get_prompt，accept_handler取本地回车处理函数。回车处理函数由组件传入Buffer，将buffer.text放入submitted_inputs，返回False让组件清空已提交的输入。
3. 用HSplit把output_area放在input_area上方，Layout设置focused_element为input_area。以该layout构造full_screen=True的Application，返回app和output_area，供CLI启动和写入。

2026-11-08 16:42首版回读确认两个TextArea和上下排列已写好。第9行创建的Layout实例需要赋给layout，第10行Application的layout参数使用该实例。函数已有submitted_inputs和get_prompt参数。修正布局后，在创建input_area前定义同步的accept_input(buffer)，用put_nowait提交buffer.text并返回False，再向输入框传入prompt=get_prompt和accept_handler=accept_input。

2026-11-08 16:51回读确认Application接收Layout实例。下方TextArea传入动态提示和回车回调，回调提交buffer.text后返回False，静态通过。

## 11. 把打印写入上方输出区

学员在terminal_ui.py新增TerminalWriter。CLI后续运行Application时把print写到该对象，正文片段和工具、用量等日志由同一个输出区显示。将output_area的占位文字换为空文本。

TerminalWriter初始化时保存output_area和asyncio.get_running_loop()，CLI会在async main中创建实例。同步的_append(text)将新片段追加到output_area.text，用Document记录拼接后的文字与末尾光标位置，调用output_area.buffer.set_document(document, bypass_readonly=True)。TextArea的缓冲变动会触发重绘，光标位置让输出区跟随最新正文。Document从prompt_toolkit.document导入。

write(text)接收print写来的字符串。有文字时调用loop.call_soon_threadsafe(self._append, text)，将更新交给界面的事件循环，随后返回len(text)。flush()提供空实现，write已经安排了本次写入。这样正文片段在换行前就会更新输出缓冲。

2026-11-08 20:08回读确认TerminalWriter的初始化与Document追加正确。第35行在write里调用print，重定向后会递归进入write。学员改为返回len(text)，仅对非空文字安排追加，并将flush(self)作为与write同级的方法，函数体写pass。

2026-11-08 20:11回读确认write对非空文本安排追加并返回长度，flush已单独定义。TerminalWriter静态通过。

## 12. 把分区界面接入CLI

在cli.py导入contextlib.redirect_stdout及terminal_ui的build_terminal_ui和TerminalWriter。main保留监听器登记及current_session_id，创建submitted_inputs = asyncio.Queue()和返回会话提示的get_prompt函数。调用build_terminal_ui(submitted_inputs, get_prompt)得到app与output_area，再创建writer = TerminalWriter(output_area)。Application先绑定实际终端输出，随后重定向普通print。

将原来的输入与命令循环移到main内的async command_loop。用nonlocal current_session_id共享会话名，把agent_task、read_only、steering_queue初始化放在command_loop内。循环从await submitted_inputs.get()取得一行并strip，非空时把提示和已提交文字打印到输出区，随后进入原命令判断。

在/session切换成功后调用app.invalidate更新提示。普通任务用app.create_background_task启动，使界面管理它的生命周期。/exit先await cancel_request(agent_task)，再app.exit()并return。

在command_loop之后定义普通函数start_command_loop，用app.create_background_task(command_loop())启动命令循环。在main末尾以with redirect_stdout(writer)包住await app.run_async(pre_run=start_command_loop)。pre_run接收函数对象，界面启动时调用它。输出框从空文本开始。接好后随一次正常任务观察正文逐块显示与底部输入，并用/exit回到终端。

2026-11-08 21:02回读确认CLI接线静态通过。回车经submitted_inputs进入命令循环，/session刷新提示，Application启动和管理后台任务，print重定向到TerminalWriter。/exit取消活跃任务后关闭界面。上方仍有一段布局占位字，运行前可将初始text置空以免和第一条命令连在同一行。待学员运行一条正文在同一自然段的任务，同时在底部输入草稿，观察正文增量和输入保留。

2026-11-08 21:15分区CLI实际任务已完成，学员确认显示正常。运行记录中default任务为completed，耗时2.78秒。上方初始文本已置空。逐块输出与固定输入的练习完成。

## 13. 输入历史和单行高度

输入框的Buffer默认创建InMemoryHistory。按回车时，组件调用accept_input提交整行，将非空文字追加到历史，再根据回调的False返回值清空输入。方向键回填的是本次CLI运行期间的输入记录，回车才把回填的内容再次提交。/session切换共用同一个输入控件，重开CLI时创建新的内存历史。模型会话消息另由session_store持久化。

全屏备用屏幕里的滚轮可被终端转成上下方向键，当前焦点在单行输入框，因此会翻看输入历史。已核对[Windows Terminal备用屏幕的滚轮处理](https://github.com/microsoft/terminal/blob/main/src/terminal/input/mouseInput.cpp#L476)。本机prompt_toolkit也会把无坐标的滚轮事件转成上下方向键。

本机prompt_toolkit 3.0.53的TextArea在multiline=False时将height设为D.exact(1)。单独给height传2或3，输入区仍占一行。multiline=True时可以指定显示高度，例如height=3分配三行，普通回车默认用于换行。
