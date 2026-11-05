# 进阶第13节：任务用量与运行记录

> 2026-11-04开始，2026-11-05完成。学员已实际跑通CLI正常任务的计时、跨轮已报告用量累计及JSONL追加保存，终端与文件一致。摘要事件及取消/异常分支已静态通过；不为结课追加故障矩阵。

## 1. 目标与当前缺口

CLI计时、摘要usage事件、任务本地累计、JSONL保存及各结束状态接线均已静态通过。正常任务的终端截图和两条本地日志已核实，本节实现与运行目标完成。

任务可能包含多次模型请求、工具调用、摘要与重试等待。整项任务的耗时是执行入口开始到退出的时间差；模型的单次usage只描述对应请求，不能直接当作整项任务总量。后续汇总以实际收到的usage为准，缺失统计不能冒充零消耗。

## 2. 已静态完成：为CLI任务显示总耗时

在cli.py顶部导入标准库time，使用time.perf_counter()。它返回适合计算时间间隔的秒数；起点不需要解释为日期，用结束值减开始值即可。await期间等待网络、工具或重试的时间也包含在差值中，因此适合观察用户等待任务的总时长。

在run_cli_task开始处记录started_at = time.perf_counter()，在现有try/except结构之后增加同级finally。finally中计算elapsed_seconds = time.perf_counter() - started_at并输出任务耗时；可用f-string的:.2f显示两位小数。

finally在成功返回、普通错误或取消向外传播时都会执行，适合收尾记录。当前已有的except asyncio.CancelledError: raise仍负责传播取消；计时收尾不把取消改成成功，也不需要新增异常包装或改run_agent返回值。计时覆盖本次run_cli_task执行，等待用户输入下一项任务的时间不包含在内。

本次只接CLI计时，不新增脚本、HTTP接口或独立模型请求。静态正确后继续后面的统计接线，首次运行证据可随实际任务一起取得。

计时静态通过（2026-11-05 13:05，Asia/Shanghai）：cli已导入time，run_cli_task开头设置started_at，现有两个except之后的同级finally计算秒数差并显示两位小数。取消分支仍raise，成功、普通错误及取消均能经过计时收尾。无待改计时代码，未运行学员程序，不为此单独请求模型。

## 3. 已静态完成：摘要请求也报告usage

当前model_client的流式路径在响应读取结束后发送model_response_end，包含本轮usage；summarize_messages则只返回摘要字符串，没有报告统计。一次任务可能同时调用这两条路径，因此先补摘要事件，再做任务累计。

在summarize_messages的请求循环内，response.raise_for_status()之后、extract_message调用之前，从response.json()取得完整响应字典，再用get("usage")取统计。usage位于完整API响应的顶层，与choices同级；extract_message返回的只是助手消息，不能从那个message里取usage。

用已有await emit(...)发送与流式路径一致的事件：type为model_response_end，usage为刚取得的统计。API未提供usage时允许为None，后面的收集器按缺失处理。事件在内容校验之前发送：即使结束原因或摘要文本不符合要求，只要API已经报告用量，该部分仍应被统计。此事件表示响应收尾及统计报告，不代表内容已校验成功。

本步不增加新的模型调用、事件种类或任务全局计数器。emit将已经收到的数据交给本地监听器，后续再由每项任务自己的统计字典累加。

摘要事件静态通过（2026-11-05 13:18，Asia/Shanghai）：response.raise_for_status后已读取response_data及顶层usage，通过await emit发送model_response_end，并置于extract_message和摘要文本校验之前。统计事件与既有流式结构一致，摘要返回约定仍是str|None；未运行请求或新增测试。

## 4. 已静态完成：每项CLI任务累计已报告用量

在run_cli_task内、try之前创建本次任务的usage_totals字典。prompt_tokens、completion_tokens、total_tokens初值为0，另加reports初值0，表示收到有效usage的条数。reports由程序自己维护，不是API字段，也不等于网络请求次数。每次调用run_cli_task都会新建字典，避免把下一项任务和上一项任务混在一起。

在同一个run_cli_task内部、try之前定义async def collect_usage(event)。这是嵌套函数：它能直接访问并修改外层本次任务的usage_totals字典。其event由已有emit在通知监听器时传入，函数不是定义后自动运行。

collect_usage只处理type为model_response_end的事件，取其中的usage；usage为空时直接return。存在统计时，只对prompt_tokens、completion_tokens、total_tokens三个字段分别做+=，并将reports单独加1。可用已学过的循环遍历明确的三个字段，不把reports也当成API统计字段读取。

在进入原有try之前用listeners.append(collect_usage)登记本次收集器。模型发出事件时，emit会将同一event交给显示函数和收集函数；前者打印单轮统计，后者累加到本次任务字典。不能把收集器登记到main的常驻名单，因为它的寿命属于当前任务。

在现有finally中先listeners.remove(collect_usage)，再显示计时和累计结果。取消、错误或正常结束都会移除它，下一项任务不会再调用旧的收集函数。reports为0时显示“本次任务未收到用量统计”；否则显示“任务已报告用量合计”，列出累计输入、输出、合计。该标签表示已报告统计之和，缺失usage不当作零实际消耗。

当前CLI一次只允许一个活跃Agent任务，沿用已有listeners即可，不在本步新增并发隔离、ContextVar、测试脚本或独立模型请求。完成静态审阅后继续接运行记录，实际验证随下一次正常任务进行。

累计首版回读（2026-11-05 13:42，Asia/Shanghai）：usage_totals的位置、内层async collect_usage缩进、三个字段累加、reports计数、登记及finally移除均正确。当前漏了事件类型筛选：收集器第一行直接event["usage"]，但listeners也会收到没有usage的text_delta及工具事件，因而会触发KeyError；须在读取usage之前对非model_response_end事件直接return。另在累计输出前增加“任务已报告用量合计”标题，区分已有单轮输入/输出/合计显示。finally中先同步显示耗时再移除收集器不作为额外修改项。当前只修筛选与标题，不新增异常包装、测试或运行请求。

累计静态通过（2026-11-05 13:45，Asia/Shanghai）：collect_usage已先过滤非model_response_end事件，再取usage、跳过None并累加三字段及reports。任务本地字典、嵌套作用域、登记/移除和无统计提示均正确；标题“任务已报告用量统计”已能区分单轮与任务级输出，接受该措辞，不要求逐字改为“合计”。当前无待改累计代码，未单独运行模型或增加测试。

## 5. 已静态完成：将一份运行记录追加到JSONL

新建code/agent_v1/run_records.py，导入json与pathlib.Path，定义RUN_LOG_PATH = Path(__file__).resolve().parent / "runs.jsonl"。它固定指向模块同目录的本地运行记录文件，父目录已经存在。根.gitignore增加code/agent_v1/runs.jsonl，与本地会话一样不纳入Git；当前该规则尚未添加。

JSONL是一行一条独立JSON对象。任务结束时追加一行即可，例如两次任务可以形成两行：{"session_id":"study","elapsed_seconds":2.5}与{"session_id":"study","elapsed_seconds":4.1}。这里是格式示意，不是实测记录；后续读取时逐行解析。

学员编写普通函数append_run_record(record: dict) -> None。record由之后的CLI调用方构造，保存函数只负责序列化并追加到文件。使用json.dumps(record, ensure_ascii=False)生成字符串，不传indent，保证一条记录只占一行；字符串字段中的换行由JSON编码处理。

通过with RUN_LOG_PATH.open("a", encoding="utf-8") as file打开文件，向其写入序列化结果并拼接"\n"。模式a表示在末尾追加，文件不存在时会创建；with负责关闭文件。文件操作的OSError由本函数捕获并打印保存失败提示，使日志写盘失败不会替换调用方原有的任务结果或取消信号；不捕获编程错误或增加参数结构校验。

本步只写保存函数及忽略规则，不新增main、不独立生成假日志，也不代运行模型。静态通过后接CLI结束状态和finally调用，届时再随正常任务核实计时、统计和写盘。

保存函数初稿回读（2026-11-05 14:01，Asia/Shanghai）：run_records.py已创建，路径、无缩进UTF-8 JSON序列化及根.gitignore日志规则正确。当前两处待改：file.write(run_record, "\n")传入两个参数，会TypeError，须先把JSON字符串与换行拼成一个字符串再write；except OSError内部又打开同一日志并写fail，应移除这次写盘，只在终端提示错误。失败分支重写同一文件可能继续失败，裸fail也不是有效JSONL记录。异常提示可包含捕获的error，便于定位。当前尚未接CLI，未运行函数或生成日志，不增加测试。

保存函数静态通过（2026-11-05 14:04，Asia/Shanghai）：write已使用run_record + "\n"的单个字符串，except OSError只打印包含error的提示；追加模式、编码、无缩进JSON及固定路径均正确，日志忽略规则此前已通过。未运行函数或生成假记录，直接进入CLI接线。

## 6. 已静态完成：在CLI收尾保存任务结果与统计

在cli.py导入run_records的append_run_record。在run_cli_task的try之前创建status="running"与reason=None，确保任务返回或抛异常时finally都有自己的状态变量可用。run_agent已核对为返回含message/completed/reason的字典；如果await抛异常则可能拿不到agent_result，因此finally使用单独维护的status和reason，而不是在那里读取未必存在的返回值。

status是本项目写入运行记录的字符串约定：run_agent正常返回且completed为True时设为completed，为False时设为incomplete，两种情况的reason均取agent_result["reason"]；except Exception里设为error，reason取str(error)，保留当前错误显示；except asyncio.CancelledError里设为cancelled，reason写“任务已取消”，继续raise传播取消。初始running用于表示执行阶段，正常返回、普通异常及取消三个出口会更新它。

在现有finally末尾构造record字典，保存session_id、status、reason、elapsed_seconds、usage_totals五个字段，值分别来自本次任务参数、前述状态变量、已有计时结果及累计字典。当前先实现这五项，不引入额外时间戳、请求ID或存储模型。append_run_record(record)是普通函数调用。

保存调用位于usage显示的if/else之后、与该if/else同级，仍在finally内部。这样收到或没收到usage都保存一次，成功、未完整完成、错误和取消都能走同一处收尾；不在收集器中每轮写入。收集器移除、计时及单轮显示沿用当前实现。日志保存函数自己处理OSError，保留任务结果和取消传播。

接线静态正确后，由学员运行一次正常CLI任务，同时观察最终耗时、累计已报告用量及runs.jsonl新添的一行；不额外创建验证脚本、故障注入或模型请求矩阵。当前状态接线尚未写、运行记录尚无实测。

CLI接线静态通过（2026-11-05 14:31，Asia/Shanghai）：保存函数导入、try前status/reason初始化、返回completed/incomplete及原因、普通异常error/str(error)、取消cancelled并raise均正确。finally在用量if/else之外构造五字段record并调用普通保存函数一次，收集器仍移除。只读检查runs.jsonl尚未生成，当前没有运行记录实测；未代运行Python或请求模型。

## 7. 已完成：一次正常任务同时查看统计与记录

由学员使用项目.venv解释器运行cli.py，进入/session metrics_demo后发送“请调用read_file读取AGENTS.md，然后用一句话概括内容。”。本次使用现有工具与回答流程，观察任务结束时的耗时和已报告用量合计，再核对runs.jsonl新增的一条记录。

正常完成时预期session_id为metrics_demo、status为completed，elapsed_seconds与终端的两位小数显示对应，usage_totals与终端任务合计一致。reports表示收到usage的条数；工具调用及后续回答通常形成多轮统计，不固定具体token数或把reports称作网络调用次数。一项任务对应一条日志记录。

只需这项正常任务的实际证据；取消、异常和未完整完成分支当前仅静态通过，不额外安排故障注入或测试矩阵。收到输出和日志后再判断本节运行目标是否完成。

运行核对完成（2026-11-05 14:43，Asia/Shanghai）：截图两轮输入1044与1242，合计2286；输出84与32，合计116；total_tokens为1128+1274=2402。runs.jsonl对应首条为session_id=metrics_demo、status=completed、reason=null、elapsed_seconds=3.3129303999594413、reports=2，三项累计与终端完全一致，耗时显示3.31秒。

同次读取还看到第二条completed记录：耗时2.559637400030624秒、输入1280、输出210、合计1490、reports=1。第一条仍保留，第二条从本次任务重新累计，实际展示了追加与任务间统计分离。第二项任务的具体内容未由截图提供，不推定其内容。取消、错误、未完整完成及摘要统计事件仍按静态证据记录，不宣称本次都已触发。

第13节完成，无剩余必做代码或额外验证。下一主题为[并行子任务与独立上下文](Agent进阶14_并行子任务与独立上下文.md)，复用已完成的结构化审阅函数，学习任务分组和结果归属。

## 8. 统计边界

一行保存一项任务的运行结果与已报告统计，不把日志写入会话消息或发给模型。会话历史继续保存对话，日志保存本次任务的指标，两者由各自调用方维护。

已只读核对当前model_client：流式与摘要路径均已接model_response_end事件。汇总称为已报告用量，不能将缺失usage视为零实际消耗；请求次数、重试次数与收到的统计条数按实际来源区分，不凭显示次数推定。当前不增加价格表、计费推算或多供应商适配。
