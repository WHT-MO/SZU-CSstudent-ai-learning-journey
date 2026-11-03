# 进阶第11节：代码审阅工作流

> 2026-11-03开始，并于当日23:57实际跑通零问题分支，本节按当前范围完成。复用单Agent、模型、文件工具和Pydantic，学习业务结果结构、代码阶段控制与报告保存。源码由学员亲写；运行结论限于下文记录的路径。

## 1. 为什么选择这个主题

当前已覆盖模型请求、工具执行、上下文、会话、事件、HTTP及MCP接入。现有代码审阅场景曾出现将范围外问题或版本条件误报为缺陷，之后通过明确审阅范围与证据要求修订。下一步用该真实场景学习如何组织任务产物和检查条件。

这里的工作流指用程序控制阶段顺序、数据传递及继续条件。每个阶段内部仍可让Agent自主选择工具。Skill主要向模型说明如何工作；工作流把部分步骤和检查落实到Python代码中。此区别可参考[Anthropic对工作流和Agent的定义](https://www.anthropic.com/research/building-effective-agents)。本节顺序是针对当前项目的教学选择，不是Agent开发的唯一路线。

## 2. 本节目标与边界

先做单个Python文件的审阅流程：读取与模型审阅→取得结构化候选问题→程序核实可机械检查的证据→生成Markdown报告。工作流开始时已有目标路径，因此一条问题暂不重复携带路径。

程序可以检查行号是否在范围内、引用片段是否与源码一致、输出格式是否符合约定。问题是否构成缺陷、触发条件是否真实仍需判断，不能把有证据字段或格式校验通过当作结论正确。更复杂的复核只在出现具体需求时加入，不无条件增加一轮模型调用。

本节复用现有模型与工具，先用普通Python组织流程。RAG随后以多文档知识问答学习：现有read/search也能参与检索增强，向量库不是RAG的定义；是否增加索引要看资料规模和检索需求。多供应商和多Agent按实际需要安排。

本节定位是可选的业务工作流练习，不是每个Agent必须具备的代码审阅组件。原有Agent已经可以按技能指引直接生成Markdown报告。本节额外选择让模型输出结构化数据、由程序检查与排版，用现有场景学习如何消费模型产物；不能把这条路线说成唯一正确方案或Agent基础缺失。

当前项目的三个层次：run_agent提供模型/工具执行循环；workspace/skills/review_python/SKILL.md向模型说明审阅步骤与判断原则；review_workflow.py用Python组织收集、检查、排版及保存阶段。工作流可以调用Agent，阶段内部仍由模型选择读取工具。技能指引与代码流程可以配合，并非二选一。

当前技能、提示示例与报告标题围绕Python。ReviewResult字段、按行证据比对和字符串排版本身不依赖Python语法，可以复用于其他文本代码；实际支持其他语言时还需提供相应语言版本、审阅规则及需要的检查工具，不能把文本可读取等同于专业审阅能力已经验证。本节不因此扩展语言适配范围。

## 3. 已完成：定义审阅产物

学员新建code/agent_v1/review_workflow.py，使用已学的BaseModel和Field定义两个类，当前不写工作流函数。

ReviewFinding代表一条候选问题：

| 字段 | 类型与约束 | 含义 |
| --- | --- | --- |
| line | int，至少1 | 候选问题对应的源码行号 |
| description | str | 具体是什么问题 |
| trigger | str | 什么输入或状态会触发 |
| impact | str | 触发后造成的影响 |
| evidence | str | 支持该结论的源码片段 |

ReviewResult代表本次审阅结果，只有必填findings字段，类型为list[ReviewFinding]，即多条候选问题组成的列表。没有发现候选问题时用空列表，不据此宣称文件一定正确。嵌套类按先ReviewFinding、后ReviewResult定义；列表元素类型写类名。

为什么另设ReviewResult：ReviewFinding定义一条问题，ReviewResult定义整份输出的顶层结构。用同一个BaseModel既可生成供模型读取的JSON Schema，也可在返回后一次解析并校验整份数据及嵌套问题。json.loads单独只解析JSON，不会按这些字段约束检查数据。ReviewResult是项目自定义类名，模型收到格式说明、返回JSON文字，Python调用解析后才得到对象。外层类不是技术必需，直接校验并返回问题列表也能实现；本节选择轻量外层对象，复用已学的模型/Schema/解析接口，不以假想扩展为增加字段的理由。

这两个类描述审阅业务数据。现有run_agent返回的message/completed/reason继续描述运行结果；后续会把message.content中的结构化内容解析成ReviewResult，不在本步骤重写run_agent返回契约。

静态审阅：学员已补充Field导入并将line定义为`int = Field(ge=1)`。两个类的字段、行号下限及嵌套列表类型均正确，本步骤通过；未运行测试或模型请求。

## 4. 已完成：把JSON文字解析成审阅对象

模型回答保存在运行结果的`message["content"]`中，仍是一段字符串。本工作流后续会要求模型只输出JSON，例如`{"findings": []}`，当前先写接收这种文字的解析入口。

已学过的`model_validate(arguments)`接收Python字典等对象；本次使用`ReviewResult.model_validate_json(content)`，直接解析JSON文字、按ReviewResult及嵌套的ReviewFinding校验，并返回ReviewResult对象。此时通过对象的`.findings`属性取得列表，列表元素也是ReviewFinding对象。JSON格式错误、缺少必填字段或line小于1等会抛出ValidationError。解析通过只说明数据结构符合定义，问题是否成立仍需后续检查。已核对本机Pydantic 2.13.5实现及[官方说明](https://docs.pydantic.dev/latest/concepts/models/#validating-data)。

学员在同一个源码文件增加`parse_review_result(content: str) -> ReviewResult`，用普通def定义，调用上述方法并返回对象。函数执行内存中的数据处理，没有需要等待的网络或文件操作。解析失败先自然抛出，之后由工作流调用处统一处理；当前不增加异常吞掉后返回空列表的逻辑，空列表已经表示未发现候选问题。

本步只写解析函数，后续再接run_agent、JSON输出要求和错误处理。不新增测试或模型请求门槛；静态通过不等于已经完成实际工作流。

解析函数静态通过：名称已为`parse_review_result`，内部调用model_validate_json并返回对象，原try/except已移除，解析失败自然向外传递。源码仍导入ValidationError，当前未使用，不作为阻塞；后续调用入口处理格式错误时可以使用。

## 5. 已完成：连接只读Agent与审阅结果

本阶段固定顺序为构造任务→等待Agent→检查运行是否完整→解析最终回答。目标是返回ReviewResult对象，让后续代码继续做证据检查与报告。模型在阶段内仍自主选择读取工具。本步采用提示词约定JSON输出、收到后用Pydantic校验，没有增加供应商API的强制结构化输出配置。

在review_workflow.py增加异步函数`collect_review_findings(path: str, scope: str, session_id: str) -> ReviewResult`。三个参数都是调用方传入的字符串：path为workspace下的相对路径，例如minimal_loop.py；scope为审阅前提，例如“Python 3.12+，只报告当前脚本实际可触发的缺陷”；session_id为本次审阅的会话名，例如review_workflow_01，沿用已有存储规则。实际演示时选独立审阅会话；当前只写函数，暂不增加main或发起模型请求。

导入标准库json、agent_runner中的run_agent、tool_policies中的read_only_guard，复用同文件的ReviewResult和parse_review_result。

实现步骤：

1. 取得ReviewResult.model_json_schema()，用json.dumps(..., ensure_ascii=False)转成JSON文字，放入本次任务字符串。此前工具参数使用同一方法生成说明，这次让模型看到最终回答需要满足的数据结构。
2. 任务中填入path和scope，要求先读目标文件，按已声明的范围判断。只返回顶层JSON对象，findings中每条包含line/description/trigger/impact/evidence，没有候选缺陷时为[]；不加Markdown围栏、开场文字或报告。evidence须原样引用源码，不加行号前缀，line为该证据片段在文件中开始的1基行号，便于后续程序从同一位置核对。
3. await run_agent，首个参数传任务字符串，关键字参数传session_id=session_id及before_tool=read_only_guard。本阶段只审阅，现有权限函数允许read_file/list_files/search_file，拒绝写入、编辑和执行脚本；审阅结果返回后由后续代码生成报告。
4. 用agent_result等局部变量接住run_agent的字典。若completed为False，抛出RuntimeError，错误信息包含reason；这样长度限制、轮数耗尽等未完成结果不会直接进入JSON解析。
5. 正常完成后取agent_result["message"]["content"]交给parse_review_result，返回该ReviewResult对象。JSON或字段不合法时，沿用解析函数的ValidationError向外传递；下一步由工作流入口区分运行失败与格式错误，不自动重试或返回空findings。

run_agent的运行状态字典和最终ReviewResult分别描述执行情况与审阅业务数据，两者在这里衔接。本步依据源码静态审阅，不把已有Agent成功泛化为新工作流已运行。

收集函数静态通过：任务文字已填入path/scope/Schema，json.dumps已使用ensure_ascii=False，run_agent传参和completed/reason分支正确，末尾已调用parse_review_result并返回ReviewResult对象。函数签名中的返回类型注解只说明预期类型，实际转换由解析调用完成。未运行模型或新增测试。

## 6. 已完成：核对引用是否来自对应源码位置

Schema校验能确认line至少为1、evidence是字符串，但不能确认文件是否有该行，也不能确认模型引用的是该位置的真实代码。程序接下来完成这些可直接比较的检查；引用对上仍不保证缺陷结论成立。

在review_workflow.py增加普通函数`validate_review_evidence(source: str, result: ReviewResult) -> None`。source是待审阅文件的完整源码文字，由后续工作流入口读取后传入；result是collect_review_findings返回的审阅对象。此函数只检查传入数据，不读文件或调用模型，所以用def。函数不会生成新业务数据：检查全部通过时自然返回None，首个不符合项抛ValueError，说明行号及原因。空findings会正常通过这一层检查。

先用source.splitlines()取得源码行列表，然后遍历result.findings。列表元素是ReviewFinding对象，用finding.line及finding.evidence取值。每条检查：

1. line不能超过源码总行数，下限已由ReviewFinding约束，不重复写下限校验。
2. evidence不能只有空白。此处可以用strip判断有没有内容；真正比较时保留原文缩进与空格。
3. 用evidence.splitlines()取得证据行列表。起始下标为line - 1，结束下标为起始下标加证据行数；取源码这一段切片，与证据行列表比较。不相等即报错。按行比较会忽略换行符的形式，保留每行的其他内容；证据超过文件末尾时，切片长度不足也会导致不相等。

举例：源码三行为a = 10、b = 0、print(a / b)，报告line=3且evidence为print(a / b)，需要比较source_lines[2:3]与证据行列表。仅检查evidence是否出现在整个文件里无法核实行号，不能代替指定位置比较。

本节先选择证据全部通过后再进入报告阶段；不匹配就停止并说明原因，避免把证据失败静默变成未发现问题。当前只编写此函数，后续统一连接读取、收集、检查和报告，再实际运行。

证据检查静态通过：空白判断已为strip() == ""，行号上限、切片、列表比较及带行号的错误信息均正确，全部检查完自然返回None。is比较对象身份，==比较内容；此前空白判断问题已修正。不增加局部运行门槛。

## 7. 已完成：生成Markdown报告字符串

模型已提供description/trigger/impact/evidence，本节选择由Python完成固定排版。直接让模型返回Markdown也是合理方案，而且也可以只经历一次审阅过程；本节这种拆分不天然减少一次模型调用。选择理由是让程序先消费、检查字段，再按固定格式展示。后续入口会先验证证据，再调用本函数，并负责保存文件。

Markdown字符串就是包含Markdown标记的普通str，不需要专门的生成库。例如下面是与作业不同的最小示例：

```python
student = "小林"
note = f"""# 学习记录

姓名：{student}

- 今天完成：文件读取
"""
```

note仍是普通字符串，#表示标题，-表示列表项，空行分段；支持Markdown的查看器会据此显示样式，写进.md文件即可保存为Markdown文档。本次报告函数同理，只是把学生姓名与学习事项换成路径、范围和审阅问题。单独设函数，是把固定的排版工作集中在一个入口，后续改排版时无需修改模型调用或证据检查；简单使用场景直接让模型出报告更省代码，独立函数不是所有场景的硬性要求。

在review_workflow.py增加普通函数`render_review_report(path: str, scope: str, result: ReviewResult) -> str`。path和scope沿用收集阶段的目标相对路径与审阅前提，result是审阅对象。本函数只生成并返回Markdown文字，不读写文件，也不执行模型请求。

报告包含标题、文件路径、审阅前提、候选问题数len(result.findings)。没有问题时注明“当前审阅范围内未发现候选缺陷”。有问题时逐条编号，展示line和description，以及trigger、impact、evidence；证据用python代码围栏包裹。格式示意如下（示意数据，不是实际运行结论）：

````markdown
# Python 代码审阅报告

文件：`demo.py`

审阅前提：Python 3.12+

候选问题：1 条

## 1. 第 3 行：除数为零

触发条件：执行到除法表达式时 b 为 0。

影响：抛出 ZeroDivisionError，程序中断。

证据：

```python
print(a / b)
```
````

可以复用MCP适配器中先收集字符串片段、最后join的办法：先放报告开头，遍历result.findings为每条问题加入一个段落，最后用两个换行拼成完整字符串返回。enumerate(result.findings, start=1)可同时取得编号与问题对象。字段展示顺序按上述示意，排版细节无需完全一致；结果中应包含所有问题，避免在循环第一项后提前返回。当前只写此函数，尚未连接或运行完整工作流。

当前草稿接第3步的讲解：空列表分支已经将findings设为说明字符串，有问题的分支也将findings整理成正文字符串。原for part in result.findings可用enumerate增加编号；number是从1开始的编号，part是当前ReviewFinding对象，字段通过part.line、part.description、part.trigger、part.impact、part.evidence读取。循环中用f-string生成当前问题的Markdown段落，交给parts.append保存；parts存的是各段文字，不是问题对象。

循环结束后、仍在else分支内，用两个换行join(parts)得到findings正文。随后公共report字符串插入findings，并展示len(result.findings)；最后在函数层级return report。两个分支都产生正文，再共同组织报告，避免空列表时引用只在else创建的parts。当前标题写为#Python，应在#后加空格以显示Markdown标题。本次明确讲解生成段落、append、join、正文插值和返回的完整关系，源码由学员补写，不代改或运行。

报告函数静态通过：enumerate编号、五字段、append、循环后join、公共报告正文/数量及return均正确；代码围栏已为反引号、模板文字已顶格、总标题已为# Python。保持当前排版，不追加局部测试或模型请求。

## 8. 已完成：用main串联并保存报告

直接在同文件末尾增加async def main()，负责本次单次脚本演示，不额外增加仅转发一次的run_review_workflow封装。导入标准库asyncio，并从tools导入已存在的resolve_workspace_path。本函数调用此前已经写好的函数，不复制其内部实现。

在main内明确本次参数：path="minimal_loop.py"，scope="Python 3.12+，只检查当前代码实际可触发的缺陷"，report_path="workflow_review_report.md"，session_id="review_workflow_01"。只读检查已确认workspace/minimal_loop.py存在，本次报告和该会话文件尚不存在；使用独立审阅会话，不清除旧历史。

按以下顺序串联：

1. 用resolve_workspace_path分别将输入path与输出report_path转换成Path对象，例如source_file与report_file。沿用已有工作区边界，不另写路径检查。
2. source_file.read_text(encoding="utf-8")得到原始源码字符串source，用于后面的引用核对。
3. await collect_review_findings(path, scope, session_id)，接住返回的ReviewResult对象，例如result。调用时仍传原始工作区相对路径。
4. validate_review_evidence(source, result)，普通调用；失败会抛异常，使后续排版/写入不再执行。
5. render_review_report(path, scope, result)，普通调用，将返回的Markdown字符串存为report。
6. report_file.write_text(report, encoding="utf-8")保存文件，成功后打印报告的保存路径。本次报告直接放workspace下，父目录已存在。本入口在模型调用前后做本地读写，当前用同步Path方法即可，不增加文件IO包装函数。

main中将路径转换到保存这些步骤放进try。先except ValidationError，显示审阅结果格式错误；再except (RuntimeError, ValueError, OSError)，显示审阅失败及异常文字。ValidationError也属于ValueError，单独的格式分支放在前面，避免被通用分支先接走。成功提示放在保存之后，不在异常分支显示成功。

最后沿用demo_mcp_client.py已经学过的脚本入口：仅在__name__ == "__main__"时asyncio.run(main())。只有collect_review_findings需要await；证据检查、报告拼接及Path读写都是普通调用。当前先写入口，尚未运行模型；入口静态正确后由学员实际运行一次。

main最终静态审阅：参数、路径转换、读取、收集、验证、渲染、保存及脚本入口均正确。格式异常分支已改为except ValidationError as error并打印异常本身，避免在结果尚未赋值时引用result。学员已直接运行本文件，没有新增测试脚本。

在PowerShell使用完整解释器与脚本路径（不依赖当前终端目录）：

```powershell
& "D:\code\dsh\python-course\.venv\Scripts\python.exe" "D:\code\dsh\python-course\code\agent_v1\review_workflow.py"
```

成功时显示报告保存路径，实际文件为code/agent_v1/workspace/workflow_review_report.md，会话为sessions/session_review_workflow_01.json。运行后结合实际产物检查成功或具体失败原因；教员不代发模型请求。

## 9. 实际运行结果（本节完成）

2026-11-03 23:57，学员终端显示报告保存成功。教员随后只读核对workspace/workflow_review_report.md、sessions/session_review_workflow_01.json及最终main实现：

- 会话共8条消息，模型先读取review_python/SKILL.md和minimal_loop.py，两条工具调用及对应结果编号匹配。
- 模型另请求write_file创建check_run.py，被read_only_guard拒绝，工具消息为“只读模式，拒绝执行：write_file”；模型随后继续完成回答。
- 最终模型回答为{"findings": []}，报告显示候选问题0条，并注明当前范围未发现候选缺陷。结合main顺序确认完整响应、JSON解析、空结果证据检查、固定排版与本次保存成功。
- 报告由Python在验证之后保存，模型的写入工具请求没有获得执行许可，体现本节代码流程和模型行为的边界。

本次实际跑通的是零问题分支，逐条证据匹配、格式错误及其他失败分支仍以静态审阅为依据；不泛化为所有情况已经运行，也不追加局部验收。本节完成，下一项为RAG多文档问答，先学习资料加载和相关片段检索。教员未代改或运行源码、发模型请求或上传Git。
