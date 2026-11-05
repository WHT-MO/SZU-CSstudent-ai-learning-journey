# 进阶第14节：并行子任务与独立上下文

> 2026-11-05完成。独立会话、TaskGroup执行及父流程汇总已实际跑通，v2用途前提与结果已核对，报告前提拼接也已静态修正。本节没有剩余必做代码或额外模型请求。

## 1. 本节要解决什么

将一份代码的两个独立审阅侧重点分别交给两个工作单元：逻辑与控制流程、异常与资源处理。每个工作单元仍然调用现有run_agent，使用相同模型；通过不同session_id持有各自的messages和summary_cache，遵循各自的任务范围。两个工作单元都由已有read_only_guard限制工具，父流程收集其结构化结果。

模型数量、并发调度、上下文与任务分工是不同事情。asyncio负责调度；不同会话使两个工作单元拥有各自的历史；任务提示说明职责；父流程决定怎样使用结果。多次并发调用本身不自动完成职责设计。独立侧重点可并行，有输入输出依赖的步骤应先取得所需结果再执行。

这次复用review_workflow.collect_review_findings(path, scope, session_id)，它已负责只读run_agent调用和JSON解析，返回ReviewResult。新练习负责分组与独立会话，后面复用validate_review_evidence及报告排版。更多调用通常增加总用量，独立上下文也可能重复读取资料；本节学习适用机制，不把并行协作当作所有任务的必选方案。

## 2. 新方法：asyncio.TaskGroup

Python 3.12可使用TaskGroup管理一组子任务。在异步函数中，通过async with asyncio.TaskGroup() as group创建任务组，group.create_task(协程)启动各项工作并返回Task。离开async with时会等待组内任务结束，成功后用task.result()取得该Task返回的值。

本练习采用“两项都成功才返回整体结果”的规则。TaskGroup在一个子任务抛出普通异常时会取消组内其余任务，并以ExceptionGroup向外报告错误；当前收集函数不捕获它，后续入口统一显示失败。取消和异常不会被包装成正常的ReviewResult。与只写几个await相比，它明确了父任务对子任务生命周期的管理。

## 3. 已静态完成：收集两个有独立会话的审阅结果

新建code/agent_v1/parallel_review.py，导入asyncio以及review_workflow中的ReviewResult和collect_review_findings。编写async def collect_parallel_reviews(path: str) -> dict[str, ReviewResult]。

函数内为两个任务准备scope：共同前提为Python 3.12+、按现有脚本入口、只报告当前实际可触发的确定缺陷，不把风格或未来扩展混入；逻辑任务侧重控制流程、条件判断和返回值，异常任务侧重异常处理和资源清理。

使用同一个TaskGroup启动两次collect_review_findings，path取本函数参数，scope分别取各自范围，session_id分别为parallel_review_logic和parallel_review_exceptions。两个Task分别保存为logic_task和exceptions_task。演示会话名按角色分开，重复运行会延续各自历史；当前不要求UUID或额外会话名校验。

在async with结束之后返回字典：logic对应logic_task.result()，exceptions对应exceptions_task.result()。这两个值都是ReviewResult对象，不是原始助手消息、字符串或Task对象。先完成这个收集函数；当前不加运行入口或发请求，之后再接源码证据校验和报告保存。

收集函数首版回读（2026-11-05 15:50，Asia/Shanghai）：parallel_review.py已创建，TaskGroup内创建两个Task、分别传不同session_id、退出任务组后result()并返回logic/exceptions字典均正确。当前仅exceptions_scope复制成与logic_scope完全相同的控制流程/返回值范围，两项任务实际收到同样的审阅要求；改为Python 3.12+下异常处理与资源清理的实际缺陷即可。当前函数尚未运行，不为这一字符串修正安排额外验证。

并行收集静态通过（2026-11-05 16:00，Asia/Shanghai）：exceptions_scope已修为异常处理和资源清理；TaskGroup、两个独立会话、正常退出组后取两份ReviewResult及返回字典均正确，无待改收集逻辑。尚未运行请求，直接接父流程，不增加局部验证。

## 4. 已静态完成：父流程校验并保存汇总报告

父流程沿用review_workflow.main的读源码、收集、证据校验、排版和写盘顺序，把单份结果变为逐份处理结果字典。模型子任务只收集候选，Python父流程负责核对引用并决定是否保存报告。

任务调用和报告排版都需要同一份scope。将当前两条范围字符串移到parallel_review模块顶部的REVIEW_SCOPES字典，键为logic和exceptions；collect_parallel_reviews从对应键取范围。这样父流程不读取另一个函数的局部变量，也不用另外复制一套范围说明。

在parallel_review.py补充导入validate_review_evidence、render_review_report和tools.resolve_workspace_path。新增async main：path="minimal_loop.py"，通过工作区路径函数取得源码文件并按UTF-8读取source；results接await collect_parallel_reviews(path)，report_parts先为空列表。

遍历for role, review_result in results.items()。role为logic或exceptions，review_result为对应ReviewResult对象。每项先调用validate_review_evidence(source, review_result)，通过后调用render_review_report(path, REVIEW_SCOPES[role], review_result)生成字符串，追加到report_parts。该校验只核对行号和源码引用，不等于已证明每条候选问题的语义判断正确。

所有项处理成功后，用"\n\n---\n\n".join(report_parts)组合两份报告，通过resolve_workspace_path("parallel_review_report.md")取得输出路径并按UTF-8写入，最后打印保存路径。循环内只构造字符串，最终写盘在循环外；这样一份证据失败不会把半份结果报告成整体成功。已有renderer会将各自scope写入报告，报告之间的横线用于区分两个审阅范围，不改共享renderer。

main的try覆盖上述流程。TaskGroup的子任务错误会以Python内置ExceptionGroup向外传播；except ExceptionGroup取得group_error后遍历group_error.exceptions，显示每个内部异常的类型和原因，避免只打印汇总的“有几个子异常”。父流程自身的证据ValueError和文件OSError在另一个except中显示失败。当前固定任务组只包装直接子任务的普通异常，无须新增递归错误处理、重试或替代模型。底部用asyncio.run(main())启动。

REVIEW_SCOPES、main、报告保存和启动入口已写并整体静态通过，接下来由学员运行完整并行审阅一次。当前尚无成功报告，不增加局部测试脚本或由教员代请求模型。

父流程首版回读（2026-11-05 16:29，Asia/Shanghai）：REVIEW_SCOPES共用、父流程读源码/await结果、逐份validate/render、循环外写盘及ExceptionGroup内部异常显示均正确。当前启动条件误写if __name__ == "__file__"，直接执行脚本时__name__为"__main__"，因此不会调用main；修正入口即可。另在write_text之后补保存路径提示，方便观察成功完成。报告目前未生成，未运行模型。resolve_workspace_path经review_workflow转引当前可用，不误报为ImportError；join未使用横线也不作为必改格式项。

父流程整体静态通过（2026-11-05 16:37，Asia/Shanghai）：入口已改为__main__，write_text后已打印报告保存路径；并行收集、范围共用、两份证据校验、汇总及失败显示均接好，无待改源码。只读检查汇总报告尚未生成。下一动作由学员运行parallel_review.py，观察保存提示，随后核对两个角色的会话记录与报告，不新增验证程序。

## 5. 已讲清的概念区别

学员曾问第3步如何安排已有审阅函数，已拆解为collect_review_findings(path, scope, session_id)产生待执行协程，group.create_task负责启动并返回Task，任务组正常结束后task.result取到ReviewResult；第二项只更换范围和会话名，返回字典在async with外。函数声明、协程、Task及返回对象按这条数据流区分。

子任务分发、会话fork与工作树管理不同状态。当前父流程由Python固定分工，不由主模型临场决定派发；TaskGroup管理子任务生命周期，不复制聊天或代码。不同session_id加载各自的会话，两个只读子任务仍读取同一个workspace。

会话fork将某一时刻的会话历史作为新会话的起点，后续各自追加；在本项目数据层可由messages与summary_cache快照保存到新session_id实现，但当前练习未做这一步。Git worktree则提供独立的代码检出目录，适合并行尝试修改方案。可以为两个分发的任务同时准备会话fork和工作树，也可以只做其中一层。官方概念参考：[子Agent](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[会话fork](https://learn.chatgpt.com/docs/developer-commands#fork-the-current-chat-with-fork)、[工作树](https://learn.chatgpt.com/docs/environments/git-worktrees)；已于2026-11-05查阅，未实际创建聊天分支、工作树或宿主子Agent。

## 6. 已跑通：完整并行审阅的执行与汇总

由学员用项目.venv解释器运行parallel_review.py，对现有minimal_loop.py样本执行完整并行审阅。正常结束时显示报告保存路径，随后核对session_parallel_review_logic.json、session_parallel_review_exceptions.json各自的任务与结果，以及parallel_review_report.md中的两个范围。只对新增编排行为取得一次实际证据，不重开第11节的单文件审阅验收；共享写工具、投票和自动互相对话按需要另开。

运行核对（2026-11-05 16:40，Asia/Shanghai）：终端显示报告已保存；两份会话的末次用户任务分别含逻辑和异常范围，各自有read_file调用及匹配的tool结果，末条均为合法结构化审阅结果，各2条findings。报告包含两个范围的四条候选，父流程正常完成源码引用校验及汇总写盘。执行和上下文分离的目标已实际跑通。

报告语义复核：第66行的轮数停止分支会结束并丢弃局部messages，当前没有继续调用、保存或重放这段未配对历史；第59行的None返回与main继续演示后续场景符合教学用途，空字典由假想模型产生；第58行提出真实SDK异常与清理要求，当前脚本没有这类调用或资源；第79行的缺content路径也不由当前三个固定桩产生。因此四条均不能按现有练习直接列为确定缺陷，不修改minimal_loop.py。

validate_review_evidence只核对行号和引用一致，不证明触发条件或缺陷判断成立。已有scope虽写“实际缺陷”，却未把该教学文件的用途和支持路径作为明确前提交给子任务；这处任务前提遗漏由教员补清，不将模型误报归咎于学生的TaskGroup实现。

## 7. 已实际验证：把实际用途作为显式上下文

在main定义review_context，说明：这是最小Agent Loop教学脚本，只按main中的fake_model、fake_model_always_tool、fake_model_failed演示正常回答、工具上限和模型失败；messages仅为局部临时状态，不保存/重放，不接真实SDK，main不使用run_loop返回值。仍只报告上述当前路径中能证明的缺陷，不向模型指定必须输出零问题。

collect_parallel_reviews增加review_context: str参数，main传入该值。函数内分别将review_context与REVIEW_SCOPES的logic/exceptions方向拼成两个完整scope，再交给现有collect_review_findings；父流程render_review_report的scope也拼入同一review_context，保证提示和报告声明一致。使用者前提由main提供，审阅方向继续由REVIEW_SCOPES维护，避免把教学脚本用途写死进通用收集函数。

本次独立修正对照将两个演示会话名改为parallel_review_logic_v2和parallel_review_exceptions_v2，旧会话保留。固定会话会继续带入旧候选结论，本次用新的历史起点观察补充前提的效果；不添加UUID、额外校验或删除旧会话。源码修改后仅做一次针对已观察误报的对照运行，不重测并行机制或以必须零候选为无限重跑门槛。原报告保留到下次脚本覆盖，旧会话及本页保存本轮证据。

v2复核（2026-11-05 17:22，Asia/Shanghai）：review_context已在main定义并传入收集函数，两类完整scope均带入用途前提，两个v2会话各仅1条用户任务。两者都有读取minimal_loop.py第1-90行全文的read_file调用及匹配tool结果，最终均返回{"findings":[]}；新报告两个范围均为0条。当前任务输入与结果符合本例实际约定，不据此宣称所有审阅都可靠，也不以更多模型代替语义复核。

## 8. 已静态完成：报告中的用途声明

此前render_review_report只接收REVIEW_SCOPES[role]，报告未显示实际采用的review_context；2026-11-05 17:35回读已改为f"{review_context}\n{REVIEW_SCOPES[role]}"，声明与真实请求一致，静态通过。review_context参数暂未标注str不影响当前行为，不作为额外必改项。

本次输入、双会话与结果已有运行证据，报告说明是可直接静态确认的字符串拼接小改；修改后只需回读源码，不再发模型请求或要求重跑完整编排。既有v2报告作为本次运行产物保留，其实际前提已在会话及本页注明。

## 9. 答疑：会话中出现“模型请求失败”

2026-11-05 17:35学员明确指会话JSON里的这段文字。定向检查两份v2会话，消息正文共出现13次，全部位于read_file工具返回的文件正文：两会话各读取minimal_loop.py一次，共2次；逻辑会话读取review_report.md中的旧说明，7次；读取当时旧版parallel_review_report.md中的引用，4次。它们不是13次API失败或重试事件。

minimal_loop.py第60行本来就写print("模型请求失败")，由固定返回None的fake_model_failed演示失败分支；本轮read_file只是读取这行代码，不是在执行它。旧报告又反复引用该分支和历史演示输出，因此同一句话重复进入了消息历史。工具消息保存的是读取当时的内容快照，后来文件被新报告覆盖，旧消息不会跟着更新。

轨迹另有每个角色各一次run_python被只读策略拒绝，那是工具权限结果，与学员本次询问的字符串不同。两会话最终都正常返回空findings。逻辑角色还读取了旧报告，因此新会话代表独立消息历史，不代表对工作区文件进行盲审；不能把此次变化单独量化归因于新增上下文。

本轮借助diagnosing-bugs的信号区分思路，用户澄清后已确定是保存文本的来源问题，采用只读轨迹归因和源码对照即可；没有待复现的运行时故障，因此不新增重现/回归测试、模型调用或源码修复。对未记录的HTTP重试不作判断。报告前提修正同时已静态通过，第14节收尾。
