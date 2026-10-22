# Agent 第9章：摘要与当前任务

> 2026-10-21。第8章主路径的预算、用量与结束原因处理已静态检查通过。本章沿用当前Python项目，先保护最新任务，再整理摘要复用、生成完整性与输入输出预算。实现由学员亲写，教员只审阅和更新教学资料；讲解和已有代码不自动等同独立掌握。

教材：[上下文压缩](https://www.dgzhuya.com/modules/ch09-compaction)。本讲义是针对当前项目的教学安排，保留旧历史整体摘要，不直接引入复杂的近期保留额度或会话树实现。

## 1. 改动前实现的问题

改动前，prepare_request_messages在输入粗估超阈值时，将完整messages交给summarize_messages；成功后只返回原系统提示与一条历史摘要。run_agent在新用户输入后、以及工具批次完成后都会调用它。

因此最新用户要求也会被摘要重写。例如“只改A文件，不要动B文件”可能仅被概括为“用户想修改文件”，精确约束失去原文；本轮刚取得的工具结果也可能只剩概括。摘要有损，不能仅依靠摘要提示承诺永不遗漏。教材强调切割点与消息关联完整，本项目先选择最新user开头作为保留区起点，便于保持整个当前轮次。

目标请求结构为：原系统提示 + 旧历史摘要 + 当前轮次原始消息。完整会话仍照常留在原messages/session.json；这里改变的是送给模型的请求视图。

## 2. 当前轮次从哪里开始

当前轮次从最后一条role=user开始，一直包含到列表末尾。模型可能已经提出工具调用、程序也返回了工具结果，所以当前轮次不等于messages最后一个元素。

| 下标 | role | 内容 | 去向 |
| --- | --- | --- | --- |
| 0 | system | 原始规则 | 单独保留 |
| 1 | user | 旧问题 | 压缩区 |
| 2 | assistant | 旧回答 | 压缩区 |
| 3 | user | 最新任务 | 保留区起点 |
| 4 | assistant | 本轮工具调用意图 | 保留区 |
| 5 | tool | 本轮执行结果 | 保留区 |

这个例子old_messages=messages[1:3]，current_turn=messages[3:]。分界下标属于保留区。摘要以后只处理old_messages，保留current_turn完整结构；不能只挑出最后一条user文字而丢掉本轮assistant/tool链。

## 3. 消息切分（已静态通过）

在agent_runner.py中、prepare_request_messages前的split_messages_for_summary(messages)统一拆出system_message、old_messages、current_turn。这个分界接下来会同时决定摘要输入和请求中原样保留的部分。原先让调用方另取messages[0]也成立；学员提出一起拆出system，当前采用三项返回，使调用方能直接取得完整分区。

使用当前runner的合法输入约定：首条为原始system，至少存在一条user。任务步骤：

1. 从列表末尾向前查找，遇到第一条role=user时，把下标记为current_start并break。可用range(len(messages) - 1, 0, -1)依次取得末尾到1的下标；下标0是已知的原系统提示。正序enumerate逐次更新也正确，但会扫描全部消息；之前“不要提前break”只适用于正序写法，倒序查找应当找到就停止。
2. system_message取messages[0]，是单条消息字典；old_messages取messages[1:current_start]，排除首条系统提示；current_turn取messages[current_start:]，保留最新user和其后全部消息。
3. 返回system_message, old_messages, current_turn，后两项为列表。原messages保持原样。首轮用户任务时old_messages自然为空，current_turn是该轮全部内容。

学员提出从底部寻找最近user；该方法更直接，只检查当前轮次便可找到分界。正序和倒序的最坏时间复杂度都是O(n)，倒序通常检查更少消息；这是查找部分的差异，后续列表切片仍会创建新列表。原先建议正序是为了沿用已学enumerate，不是结构要求。

切分与第5节摘要请求接入均已静态通过。当前按第7节实现同一任务内摘要复用；摘要请求本身的输入预算与生成完整性随后推进，当前token计算仍是既有粗估。

2026-10-21：学员已实现倒序查找、两个切片及三项返回，并接入prepare_request_messages；预算与回退流程已静态通过。教员未代写完整函数、未修改或运行学生源码，不新增测试脚本、复述或故障注入门槛。

## 4. 规则文件与system消息

AGENTS.md是保存项目规则的文件；system是请求消息中的role。模型不会因磁盘上存在某个文件就自动获得内容，需要宿主程序发现、读取并组装到请求里。文件名本身不决定消息角色。

按OpenAI Docs，Codex会自动发现并加载约定位置的AGENTS.md；官方Codex CLI提示指南描述其以user角色消息注入，不等同于API的system角色。来源：[AGENTS.md指南](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[Codex Prompting Guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)。这里讲的是规则来源与消息角色的区别，不要求当前项目模仿完整Codex宿主实现。

当前Python Agent用SYSTEM_PROMPT初始化首条system消息，尚无自动加载AGENTS.md的实现。今后若把自定义规则文件内容读入system的content，它才成为该Agent系统提示的一部分。当前先完成摘要分区，不增加规则文件加载功能。

2026-10-22后续补正：上段记录的是当时停点。后续开始规则文件加载练习时，按教材Pi方案选择将学员自己的工作区约定组装到system；这是本项目的宿主设计，Codex CLI官方文档中的user注入说明仍成立。AGENTS.md来源与API角色必须分别说明，不将本练习方式推广成所有Agent的固定约定。当前实现审阅与来源对照见[项目规则与系统提示第7节](Agent第08章_项目规则与系统提示.md#7-来源与消息角色释疑以及第三次回读)。

## 5. 接入摘要请求（已静态通过）

架构位置：完整会话messages → prepare_request_messages准备本次请求 → stream_message请求模型。输入为完整messages、tools和max_tokens；准备函数返回消息列表，无法保留当前轮次时返回None。完整会话仍由run_agent保存，准备函数只构造请求视图。

学员追问前置检查是否过度防御，并确认若为正常边界则现在实现。该检查保留：这里的当前轮包含最新user及其后多批assistant/tool消息，现有50 KiB上限只管单条工具结果，不能限制整轮累计体积。因此保留部分确实可能超过预算。先检查它，既能保护当前任务原文，也能避免明知保留部分放不下仍请求摘要。当前按既有token粗估判断，不扩展额外的异常参数校验。

先保留原有的整份请求未超预算直接返回逻辑。超预算时调用split_messages_for_summary取得三部分，构造kept_messages=[system_message, *current_turn]。用estimate_request_tokens(kept_messages, tools)检查：若它已经超过max_tokens，打印当前轮次超过预算的说明并返回None，避免花一次摘要请求后仍然无法放下当前任务。

保留部分能放下时，把old_messages交给summarize_messages。摘要失败返回kept_messages，并明确打印本次仅保留当前轮、旧历史未送入模型。这是本节选择的简单降级方式，代价是模型本次看不到旧对话，原会话记录仍保留。

摘要成功时组装[system_message, 历史摘要消息, *current_turn]；沿用当前项目的摘要消息格式，但它表达的是历史概括，不能视为新增系统规则。对组装结果再次连同tools粗估：不超预算则返回；仍超预算则打印原因并返回已确认可放下的kept_messages。本节不再走旧trim_messages路径，其循环可能裁掉当前轮次。

| 条件 | 返回值 |
| --- | --- |
| 原完整请求未超预算 | 原messages |
| 系统提示、当前轮和tools合计已超预算 | None，并说明停止原因 |
| 摘要失败 | kept_messages，并说明旧历史未送入 |
| 摘要成功，合并结果未超预算 | 系统提示 + 旧历史摘要 + 当前轮 |
| 摘要成功，合并结果仍超预算 | kept_messages，并说明降级原因 |

在run_agent两处await prepare_request_messages之后，都拦截None并return；只有得到消息列表才继续调用stream_message。学员使用if not request_messages，在当前返回非空消息列表或None的约定下有效，可以保留。原历史已在准备请求前保存。

本任务由学员实现prepare_request_messages及两处调用方判断，教员只静态审阅，不代写完整函数、不新增或运行测试。摘要复用、摘要请求输入过长和摘要停止原因仍为后续任务，不据本次结构说明记为已完成。

## 6. 静态审阅修正：检查实际消息列表（已完成）

2026-10-21：学员已接入三项切分、保留部分前置预算检查、只摘要old_messages、摘要失败回退kept_messages、成功时保留当前轮，以及两处调用方停止判断。两处使用if not request_messages，在当前只返回非空消息列表或None的约定下有效，可保留；不将is None写法设成额外通过条件。

此前prepare_request_messages使用summary + kept_messages，把摘要正文字符串与消息列表相加，摘要成功时会抛TypeError；摘要失败时因or短路可能看不出错误。学员已修正：先处理摘要失败，再构造request_messages，里面包含system_message、包装好的历史摘要消息和展开后的current_turn。预算估计检查实际将发送的列表，最后返回同一列表。

2026-10-21静态检查：摘要失败、保留部分超预算、合并后超预算及正常成功分支均已接好，两处降级有提示，两个调用点均能拦截None。该请求准备流程静态通过；未新增或运行测试，未代改学生源码。

## 7. 同一任务内复用摘要（已静态通过）

架构位置仍为run_agent → prepare_request_messages → summarize_messages。接入缓存前，run_agent每批工具完成后传入原始完整messages；原历史超预算时，prepare_request_messages会为相同old_messages反复生成摘要。在一个run_agent(user_prompt)期间没有新user插入，旧历史不变，只有current_turn追加assistant/tool，所以同一份旧历史摘要可以复用。

本节将缓存限定在单次run_agent调用。新用户任务会再次调用run_agent并创建新缓存，不把上次旧历史的摘要误用于已经变化的旧历史。当前先解决任务内重复摘要；跨任务、重启后的摘要覆盖范围和保存策略另行设计。

动手范围：

1. 在run_agent中、两处请求准备调用之前初始化summary_cache={"summary": None}，可放在tools和turn_count初始化附近；该对象在同一任务内由两处调用共同使用。
2. 给prepare_request_messages增加summary_cache参数，两处调用都传入同一个对象，不在准备函数内重建缓存。
3. 保持现有完整请求预算判断和保留部分检查。需要摘要时先从summary_cache["summary"]取得已有摘要；没有缓存才await summarize_messages(client, old_messages)。成功取得非空摘要后写回同一字典；失败沿用已有提示及kept_messages回退。
4. 无论摘要来自缓存还是新生成，都继续走已有request_messages构造与合计预算检查。当前轮会增长，不能因为摘要已缓存就跳过预算检查。

用字典承载缓存，便于准备函数把结果写回，让下次调用访问同一对象。此次复用减少的是重复生成摘要的API请求；正常模型请求仍携带摘要，其输入token仍会计入。失败结果不作为可用摘要缓存。

2026-10-21：学员已在run_agent初始化一次summary_cache，两处调用传同一字典，准备函数仅缓存为None时调用摘要并写回，失败回退、命中复用及后续预算检查均已接好，静态检查通过。直接将summarize_messages返回值写入缓存有效：当前该函数只返回非空摘要或None，失败后缓存仍为None，下次可重试。未新增或运行测试，未代改学生源码。

## 8. 释疑：为什么会重复、为什么共用字典

学员追问：没到预算就直接返回，怎么会重复生成摘要；字典为何能把结果留给下次调用。这里补充变量关系，不增加新的动手或验证要求，也不将讲解等同于已掌握。

### 8.1 检查的是完整历史

完整messages未超预算时，确实直接返回，不会生成摘要，缓存也不会参与。重复问题发生在完整messages已经超预算之后：prepare_request_messages只构造并返回新的request_messages，并未把原messages替换成摘要；主循环仍向完整messages追加工具调用和工具结果，再将这份完整历史传入准备函数。

假设预算为100个token：完整请求最初估算120，摘要后实际发送的request_messages为30；一批工具结果加入后，完整请求变成125，下一次检查的仍是125。即使上次发送的压缩请求只有30，也会再次走到摘要分支。由于旧历史未变，没有缓存时就重复摘要同一部分。这里的数字只用于说明，不是运行结果。

如果下次传入的是维护好的压缩请求视图，则可用另一种方式避免该重复；本项目当前选择保留完整原始会话、独立准备请求视图，因此采用任务内缓存。

### 8.2 两次调用访问同一个字典对象

run_agent创建summary_cache，并把它传给prepare_request_messages；准备函数的参数指向同一字典，传参不会自动复制字典。函数修改cache["summary"]时，修改的是这个共享对象的内容；run_agent仍持有它，函数返回后内容继续存在，下一次传入同一对象即可读取。字典不会自动写入文件，本节只覆盖单次run_agent调用。

阅读示例：

```python
def store_summary(cache):
    cache["summary"] = "旧历史摘要"

summary_cache = {"summary": None}
store_summary(summary_cache)
print(summary_cache["summary"])  # 旧历史摘要
```

cache["summary"]=summary是在修改原字典；cache={"summary":summary}则只让函数里的局部名字指向新字典，不能更新外层原字典。若只是给准备函数的局部summary赋值，下一次调用不会自动继承这个局部值。

字典并非唯一方案，也可以把摘要作为额外返回值，让run_agent接住再传回。当前采用共享字典，是为了在准备函数返回请求列表的同时保存可复用摘要，维持现有请求返回约定。

## 9. 拒绝未完整生成的摘要（已静态通过）

任务内缓存已静态通过。此前summarize_messages只验证正文非空，extract_message只验证choices与message结构；达到生成上限的非空摘要仍可能被当作成功返回并缓存。本节承接第8章finish_reason，处理非流式及摘要生成是否正常结束。

2026-10-21核对[DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)：非流式响应的finish_reason位于choices[0]，与message同级。stop表示自然停止或命中停止串，tool_calls表示生成工具调用后交回控制，length表示达到请求生成上限；其他中断原因及缺失原因不视为本项目正常完成。这里检查协议结束状态，不能据此证明摘要语义没有遗漏。

当前只修改既有解析入口，返回值仍为message字典：

1. extract_message新增allowed_finish_reasons参数，默认("stop", "tool_calls")，满足普通非流式对话正常回答或提出工具调用的两种情况。
2. 在验证choices[0]为字典后，读取finish_reason=choices[0].get("finish_reason")；若不在allowed_finish_reasons中，抛ValueError，错误文字带上实际原因。之后继续已有message结构检查和返回。
3. summarize_messages调用extract_message时显式传allowed_finish_reasons=("stop",)，摘要只接受正常文本结束。单元素元组需要末尾逗号。非流式普通对话使用默认允许集合。

两处请求函数已有except ValueError并返回None，因此拒绝摘要会自然走现有降级分支，缓存保持None，不新增异常类型、重试场景或返回元组。

现有test_summary_mock.py中fake_response_then_success的200成功响应已补finish_reason=stop，位于choices[0]内、与message同级。该字段调整使原有成功假数据符合新解析规则，不新增测试函数、场景或运行门槛；教员未执行测试。

2026-10-21静态回读：extract_message已接入allowed_finish_reasons，默认stop/tool_calls；摘要调用显式只接受stop；不允许的原因抛ValueError并由原异常分支转为None，缓存保持None。学员把finish_reason检查放在message结构检查之后，两者均在返回前完成，该顺序有效，不为顺序或格式另加修改要求。本节静态通过，未代改或运行学生源码。当前进入第10节，任务内缓存尚不提供跨任务或重启复用。

## 10. 释疑与修订：压缩阈值不等于摘要容量

学员指出：summary_messages的主体本来就是待压缩的旧历史，超过预算不是正常的吗？前一项教学任务把主动压缩阈值和摘要请求容量混为同一值，安排不合理。撤回“传入聊天的INPUT_TOKEN_BUDGET，摘要输入超过它就直接放弃”的当前源码任务；静态回读确认学员尚未添加该参数和判断，不要求回退源码。

| 概念 | 用途 |
| --- | --- |
| 压缩触发阈值 | 在上下文仍可处理时主动整理旧历史，超过它是正常压缩场景 |
| 摘要请求的容量 | 摘要模型实际上下文窗口扣除该次输出与必要余量，超过它无法一次读完待摘要内容 |

summary_messages包含摘要指令和序列化旧历史，不含当前轮与工具定义。完整聊天请求超过触发阈值，不代表摘要输入一定超过同一个数值；但旧历史持续增长时，摘要输入也可能超过该值。前一项只加拒绝分支，没有处理正常增长路径，不是完整解决方案。

2026-10-21核对[DeepSeek模型规格](https://api-docs.deepseek.com/quick_start/pricing/)：deepseek-flash官方窗口标为1M。本项目CONTEXT_BUDGET=200000、INPUT_TOKEN_BUDGET=190000是自行选择的工作预算，不是该模型的官方上限；不能拿它们证明模型已无法读取摘要输入。现有字符数//4仍为粗估，不保证严格符合实际窗口。

[教材第9章](https://www.dgzhuya.com/modules/ch09-compaction)介绍提前触发压缩，以及用previousSummary与新增历史更新摘要。下一步整理摘要覆盖范围：保存摘要已覆盖到的消息位置，从摘要和其后原始消息重建活动请求；再次压缩时处理上次摘要与新增旧消息。完整档案继续保存，但不无限把全部档案重新当作一次摘要输入。

整体摘要可保留为对当前活动上下文旧部分的整体整理。确实超过摘要模型容量的历史需要分段等恢复策略，不能把只返回当前轮称作已经解决。容量检查仍有意义，后续按实际模型容量和活动上下文流程落地。

当前先讲清上述设计并修订计划，下一项为摘要覆盖范围与请求视图，持久化恢复与第10章衔接。未代改或运行学生源码，不新增验证门槛，不把本轮解释记为独立掌握。

## 11. 当前动手：记录覆盖位置并构造请求视图

本步完成摘要元数据与请求构造器，下一步再把预算判断与增量摘要接到该视图。当前原历史仅追加消息，已有位置不变，因此先用原messages的下标标记范围；不是压缩后列表的下标。

summary_cache增加next_message_index，表示原始messages中第一条尚未被摘要覆盖的消息下标。初始状态为{"summary": None, "next_message_index": 1}：下标0是原系统提示，1开始是普通会话。若摘要覆盖messages[1:3]，next_message_index应为3，范围右端不包含在摘要里。

示例：原messages的0为system，1为旧user，2为旧assistant，3为最新user，4为本轮assistant工具调用，5为tool结果。摘要成功后记录next_message_index=3，重建请求为原system、摘要消息、messages[3:]；最新任务与本轮工具链原样保留。不能从3之后开始，否则丢掉最新用户任务。

动手范围：

1. run_agent中的summary_cache初始化增加next_message_index=1，现有两处调用继续共享该字典。
2. prepare_request_messages首次生成非空有效摘要后，记录summary_cache["next_message_index"]=len(messages)-len(current_turn)。原messages长度减去当前轮长度，得到当前轮在原历史中的起点；失败返回前不推进边界。
3. 在prepare_request_messages之前新增build_request_messages(messages, summary_cache)。没有摘要时返回原messages；有摘要时返回[原system, 沿用当前格式的摘要消息, *messages[next_message_index:]]。摘要正文及起点均从同一缓存字典取，原messages不修改。

此次构造器尚不接入准备函数，不把记录覆盖位置称作已经完成跨任务增量摘要。下一步将先构造视图再判断是否需要压缩，并更新摘要与其覆盖范围；会话持久化之后衔接第10章。当前只存进程内状态，run_agent结束后会重新初始化，不能宣称已提供跨启动恢复。

代码由学员亲写，教员静态审阅。没有额外运行、故障注入或复述要求，正确后直接接下一段实际实现。

## 12. 释疑：构造器与原request_messages的区别

学员追问：这和压缩协程已经输出request_messages有什么区别？当前一次摘要成功时，两种写法的结果确实相同。抽出build_request_messages是代码组织与复用选择；功能增加在于保存覆盖范围，并按覆盖范围保留全部未覆盖原文，不应把“多一个函数”本身解释成新能力。

原prepare_request_messages拼接的是原system、缓存摘要、最新current_turn。当前缓存只在一次run_agent内使用，摘要覆盖了此前全部旧历史，因此该拼接是正确的。若以后保存并跨任务恢复摘要，不能继续假定所有旧历史都在摘要里。

假设摘要覆盖完整轮次A和B，C后来完成，接着用户提出D。复用同一摘要时，原拼接会得到system+摘要(A,B)+D，缺少未被摘要的C；按next_message_index重建则得到system+摘要(A,B)+C+D。此处是未来跨任务复用的示例，当前run_agent仍每次重建缓存，不能误报当前源码已经发生该丢失。

学员进一步追问：C已经进入历史，为什么摘要请求会漏掉？按当前代码，D开始时缓存重新置None，old_messages包含A、B、C；需要摘要时会生成摘要(A,B,C)，正常聊天再使用摘要(A,B,C)+D。C不会因该拼接被排除在新的摘要输入外；摘要本身有损这一点另当别论。

未来假设中的缺失发生在“直接沿用旧摘要”的路径：若恢复了非空摘要(A,B)，缓存命中后根本不会发起新的摘要请求；错误地只拼current_turn(D)，才使C未进入最终聊天请求。C仍在完整messages中，只是没被选入实际发送的request_messages。先前应明确这是未来缓存更新遗漏的假设，不能称作当前摘要请求漏C。

接入后，build_request_messages只用已知摘要和覆盖位置拼接列表，不调用模型；prepare_request_messages调用它，检查预算、必要时更新摘要与覆盖位置，再返回最终列表。构造器会替换现有手写列表拼接，避免长期维护两套逻辑。本步仍先完成构造器，下一步接流程。

2026-10-21最新静态回读：覆盖位置已移到摘要成功判断之后；build_request_messages已补切片冒号，使用*messages[summary_cache["next_message_index"]:]保留全部未覆盖消息，注释也已区分聊天请求与摘要生成请求。本步静态通过，尚未接入准备函数；未代改或运行源码。

## 13. 当前动手：接入请求视图与摘要更新

本节接入已正确的build_request_messages，替换prepare_request_messages中的重复拼接。当前缓存仍由run_agent每次初始化，尚不提供跨任务或跨启动恢复；本步使准备函数具备按覆盖范围更新的能力，为第10章保存、恢复做准备。

目标流程：先构造当前应发送的请求视图，预算满足即返回；超预算时，从该视图分离旧部分与当前轮，只在没有摘要或有新增完整旧轮次时生成摘要，成功后更新正文与覆盖位置，再重建请求。

例：若以后恢复摘要(A,B)及C起点，完整档案含A/B/C/D，初始视图为system+摘要(A,B)+C+D。对视图切分得到old_messages=摘要(A,B)+C，current_turn=D；更新结果为摘要(A,B,C)，边界推进到原档案D起点，最终视图为system+摘要(A,B,C)+D。不能改为切分全部原档案后再次从零摘要A/B/C。

动手范围：

1. prepare_request_messages开头先request_messages=build_request_messages(messages, summary_cache)，用estimate_request_tokens(request_messages, tools)判断；未超预算返回request_messages，不再直接检查完整档案并返回messages。
2. 超预算后，调用split_messages_for_summary(request_messages)，而不是原始messages。保留原system+current_turn的预算检查与None停止逻辑。
3. 用current_start=len(messages)-len(current_turn)取得当前轮在原档案中的起点。覆盖位置始终是原档案下标，不能用压缩视图的长度计算。
4. 原缓存为空时才生成的条件，扩展为summary_cache["summary"] is None或current_start > summary_cache["next_message_index"]。后者表示出现了尚未覆盖的完整旧轮次。同一任务工具结果增长时current_start不变，不会因此反复摘要；若没有新旧轮可压且最终仍超预算，沿用保留当前轮的降级。
5. 用局部new_summary接收await summarize_messages(client, old_messages)。失败打印并回退kept_messages，不覆盖原有效缓存；成功后才把new_summary写入summary_cache["summary"]，并把current_start写入next_message_index。缓存与覆盖范围要对应。
6. 删除末尾手写的system+摘要+current_turn列表，改为再次调用build_request_messages(messages, summary_cache)，继续已有合计预算检查、降级与返回。
7. summary_prompt补一句合并要求：若输入已有历史摘要，请在其基础上合并后续记录，保留仍有效的目标、约束与决策。无须增加新的API参数，old_messages已经携带上一份摘要及新增旧消息。

此处没有摘要且有旧轮时是首次摘要；已有摘要且视图未超预算时直接返回；已有摘要、有新增旧轮且视图超预算时才更新。这样“复用”不再只依赖缓存非空，而是由视图预算与覆盖范围共同决定。

2026-10-22源码静态审阅通过：学员已从构造后的请求视图切分，按原历史计算current_start；无摘要或有新增旧轮时生成new_summary，成功后同步更新摘要与覆盖位置，失败保留原缓存。摘要提示已补合并要求，首尾重建均传原始messages。教员未新增或运行测试、未代改学生源码。摘要真实容量边界与持久化恢复仍按前述修订衔接，不重新加入已撤回的同阈值拒绝摘要练习。

## 14. 收尾记录：原始下标用于原始列表

2026-10-22上传前发现末尾调用误写build_request_messages(request_messages, summary_cache)。缓存中的next_message_index属于完整messages，压缩后的request_messages已重新编号，不能再用该下标截取。

例：当前用户任务在原messages下标3，压缩后可能变为request_messages下标2。用原下标3截取压缩列表会跳过该任务。没有缓存时构造器直接返回原列表，两个变量可能恰好指向同一对象，因此首次摘要时错误不易暴露；已有摘要时必须区分列表来源。

学员听取解释后亲自将末尾参数改为messages，教员回读确认，未代改源码。当前源码已满足本节视图构造与摘要更新约定，验证依据为静态审阅；未执行mock或真实模型请求。下一步与第10章衔接，保存、恢复摘要正文和覆盖位置；当前仍由run_agent每次创建缓存，尚未持久化摘要状态。
