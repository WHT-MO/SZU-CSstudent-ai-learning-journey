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

## 4. 当前动手：给事件标记来源

现有主Agent和子任务共用agent_events.listeners，CLI的show_model_event和HTTP客户端会直接打印所有text_delta。委派接入后，子任务用于结构化解析的JSON也会进入相同显示通道。为每条事件增加source字段，显示函数后续便能识别主回答与子任务过程；用量监听器仍累计两者已报告的usage。

本项目自定义source约定：主任务为main，委派子任务为本次生成的delegate_会话名。source供事件消费者读取，不改变工具参数Schema。

先在agent_events.py导入标准库ContextVar，在模块顶部创建event_source = ContextVar("event_source", default="main")。event_source是一个上下文变量对象，event_source.get()取得当前执行上下文中的来源字符串；未设置时返回main。asyncio任务可在各自上下文保存不同的值，适合并发子任务，不能用一个共享普通字符串替换它。参见[Python 3.12 contextvars文档](https://docs.python.org/3.12/library/contextvars.html)。

在emit(event)的监听器循环之前复制本次event字典，给副本添加source，值取event_source.get()，之后将副本交给原有listener。可用event.copy()获得字典副本；各事件type及原字段继续保留。当前步骤只接标记，所有未切换来源的任务都会带source=main。

随后再在delegate_review执行子Agent前设置来源、finally恢复，接CLI和HTTP的正文显示筛选。set返回用于恢复的Token，reset在finally执行，使正常完成、异常和取消均恢复原来源；此接线尚未布置或实现，不新增运行门槛。

## 5. 后续接线与已核对的现状

函数通过后接回主Agent的模型工具调用及结果回填，不新建一套Agent循环。

已核对当前实际约束，接到对应步骤时再实现：

- execute_validated_tool当前对所有工具固定wait_for(timeout=10)。一次子Agent可能包含多轮模型请求，注册委派工具时需给它独立预算，不能只在工具内部延长等待而仍被外层10秒取消。
- agent_events当前使用共享listeners，CLI会直接显示所有text_delta。子任务结构化JSON与主Agent回答需要标识来源并在显示层区分，任务总用量则应包含已报告的子任务消耗。事件来源接线在执行前完成，不靠临时移除全局显示函数规避并发问题。
- tool_registry会导入工具实现，而review_workflow又导入agent_runner。工具模块不能在导入时形成registry→实现→workflow→runner→registry的循环；执行函数阶段再安排调用依赖。
- 现有read_only_guard只允许read_file/list_files/search_file，子任务继承它时会拒绝写入、脚本和再次委派。首版由普通模式的主Agent调用委派工具，不扩展该白名单或增加无关权限检查。

这些是当前代码中的接口条件，不是当前步骤的额外任务。每步静态正确即可继续，最终用一次明确要求委派的实际任务核实新行为，不为参数类或小改新增测试脚本。
