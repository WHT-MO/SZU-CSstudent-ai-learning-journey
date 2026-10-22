# 第 8 章补充：项目规则与系统提示

> 结果：2026-10-22。规则文件路径命名、每任务读取、system刷新及技能目录组合均已静态通过，未运行验证。接入方式仍为教材Pi的system组装方案，见第7节；后续命名和读取时机修正见第9节。
> 架构位置：工作区约定文件 → 组装system提示 → 构造请求视图 → 模型请求。
> 教材：[第8章“系统提示词动态组装”](https://www.dgzhuya.com/modules/ch08-context-engineering)。

## 1. 这一节的目标

让Agent在每个用户任务开始时读取工作区约定，组装到本次system消息。用户编辑约定文件后，下一条任务即可使用新内容。

AGENTS.md这个文件名本身不会让模型获得内容。作用来自程序读取文件，并把文本放入实际发送给模型的消息。教材展示了多层项目上下文的组装；本项目先实现一个工作区文件，具体函数和任务拆分属于Python教学安排。

本练习明确选择教材Pi的系统提示组装方式，把学员自己维护的工作区规则当作受信任配置。文件名不规定API的role；其他宿主可以选用user消息。Codex CLI的做法见第7节，不应将本练习的选择描述成通用要求。

## 2. 输入和输出

新增build_system_prompt()，返回字符串。内容由现有SYSTEM_PROMPT与工作区AGENTS.md文本组成：文件不存在时返回固定提示，存在时按UTF-8读取，用换行及“工作区约定”标题分隔后拼接。

现有tools.py已经定义workspace_root，可以与tool_functions一起导入，使用workspace_root / "AGENTS.md"定位文件。使用现有路径和文本读取方法。

## 3. 学员亲写的动作

1. 在code/agent_v1/workspace/AGENTS.md写一两条自己的工作区约定。例如“修改已有文件前先读取相关内容”“任务完成后列出修改文件及原因”。
2. 在agent_runner.py添加build_system_prompt，按前述约定返回组合后的字符串。
3. 每次run_agent开始时构造本次提示。若messages已有开头的system，原位更新messages[0]["content"]；若缺少，沿用原有插入system和重置缓存的逻辑，插入内容使用本次组装结果。

原位更新只改变下标0的内容，摘要覆盖位置仍对应原列表。若只在空历史时创建system，重启或下一条任务加载的会话仍携带旧提示，文件修改就无法及时生效。

## 4. 完成标准

固定规则与工作区约定组成实际请求里的system内容；已有会话也能在新任务开始时更新该内容。文件不存在时使用固定规则。当前任务由学员亲写，教员静态审阅；不新增运行、故障注入或复述门槛。

当前workspace目录按现有.gitignore作为本地工作区；本任务的AGENTS.md供学员自己的Agent读取，进度记录仍写入docs与memory。尚未创建学生文件、修改源码或执行请求。

## 5. 首版静态审阅：路径、内容和消息的区别

2026-10-22学员已创建workspace/AGENTS.md，内容为“修改已有文件前先读取相关内容。”。教员只读回文件与源码，尚未代改或运行。

- AGENTS_PROMPT目前使用Path(workspace_root).resolve().parent / "AGENTS.md"，parent回到agent_v1，实际创建的文件在workspace内。定位应直接基于workspace_root / "AGENTS.md"。
- if not AGENTS_PROMPT只检查路径对象真假，不能判断目标文件存在，应检查路径的exists()结果。
- f字符串中的路径对象会被格式化成路径文字，不会读取文件。用read_text(encoding="utf-8")取得正文，再与固定SYSTEM_PROMPT组合。
- build_system_prompt约定返回字符串；首版返回了字典，且存在文件的分支使用role=user并遗漏固定规则。消息的role由run_agent中的system消息承载，组装函数只返回组合后的正文。
- run_agent尚未调用组装函数，插入时仍使用固定SYSTEM_PROMPT，已有system也未刷新。需在每个任务开始时取得新提示，插入或原位更新首条system。

本函数使用同步的路径和文本读取方法，普通def即可。若学员保留async def，调用处须await取得字符串；两种形式均可正确实现，不把同步/异步形式本身设为额外门槛。当前等待学员修正上述实际问题。

## 6. 第二次回读：先理清返回值的层级

2026-10-22再次静态回读：路径已经定位到workspace，exists及UTF-8读取均已修正。当前未通过的原因集中在返回约定与接入层级：build_system_prompt无文件时返回字典、有文件时返回消息列表，而目标输出是提示正文字符串；run_agent又把未await的协程直接insert进messages，且只在缺少system时调用，已有system仍未刷新。

层级约定：提示正文是str；一条system消息是包含role、content的dict；整个messages是多条消息的list。组装函数处理第一层，run_agent将结果放入第二层的content，第二层才是messages中的一个元素。

本次推荐按同步函数实现build_system_prompt，用普通def与现有同步read_text匹配，使调用方直接取得字符串。若学员选择保留async，则正确await同样有效；真实错误是当前把协程直接存入历史。

当前动手修正：两个返回分支统一为字符串，无文件返回SYSTEM_PROMPT，有文件返回固定提示与规则正文的组合；每次run_agent开始时取得该字符串，缺system时创建标准system消息，已有时更新其content。首版列表中的systemt拼写随错误消息结构一起移除，无需额外制作另一条规则消息。

教员仅静态审阅并说明概念，未代改或运行源码；待学员修正这组返回约定和接入问题。

## 7. 来源与消息角色释疑，以及第三次回读

2026-10-22学员追问：之前不是说AGENTS.md是user信息吗？已回查第9章旧讲义并重新核对官方资料，学员记忆准确。此前说明的是Codex CLI将约定文件以user角色注入；本次选择的是教材Pi将项目约定组装进系统提示。教员没有预先交代宿主实现与角色设计的切换，且把返回user消息也混在代码错误中指正，容易造成概念矛盾，现明确补正。

- [OpenAI官方Codex Prompting Guide的Using agents.md小节](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)明确说明约定文件内容作为user角色消息注入。
- [教材第8章的系统提示动态组装](https://www.dgzhuya.com/modules/ch08-context-engineering)把项目上下文组装到system prompt。
- AGENTS.md是规则的来源，role是宿主赋予内容的消息层级；两者不是同一概念。采用user方式本身成立，需有匹配的消息组装与请求流程。本文继续采用已选的Pi方案，不将其说成Codex的实现。

最新源码已使用普通def，路径、exists、UTF-8读取及字符串返回形式均已修正。仍需修两处：有文件时返回值遗漏固定SYSTEM_PROMPT，应组合固定提示与约定；run_agent第624行误写message[0]且使用+=，此处message尚未赋值，应对messages[0]["content"]使用赋值更新完整提示。追加会在每条新任务重复累积规则，赋值才能刷新为当次组装结果。当前仍未通过，教员未修改或运行学生源码。

2026-10-22最新回读：固定SYSTEM_PROMPT已加入返回值，更新运算已改为=；仅剩第624行变量名仍写message，缺少末尾s。会话列表是messages，局部模型回复变量message此处尚未赋值。待学员将该处改为messages[0]["content"] = build_system_prompt()；教员未代改或运行源码。

## 8. 当前结果与下一项

2026-10-22回读确认第624行已改为messages[0]["content"] = build_system_prompt()。路径、存在性检查、固定规则与文件正文组合、字符串返回，以及每个用户任务刷新system均已接通，按当前受控工作区规则来源静态通过。新会话分支调用组装器后又统一刷新一次，虽有重复读取但不构成功能错误，不为此另设修改要求。

下一项接教材同一小节的[技能目录与按需加载](Agent第08章_技能目录与按需加载.md)：先用一个技能文件和一段目录字符串实现，模型匹配任务后用已有read_file读取正文。教员未代改源码或运行测试。

## 9. 命名提醒与读取时机修正

2026-10-22学员指出原AGENTS_PROMPT存放路径而非提示正文，教员此前未提醒命名不准确，这个反馈成立。应区分AGENTS_PATH这样的路径变量、函数内读取到的agents_text正文，以及最终组装的提示字符串。

实际回读发现，学员保留了AGENTS_PROMPT名字，并在全局定义时调用read_text，使其值变为正文。命名与值虽已一致，行为也随之改变：模块加载时立即读取一次，后续连续任务使用同一旧字符串；文件不存在时会在进入组装函数之前报错，原有可选文件行为失效。

当前修正方向：全局使用AGENTS_PATH保存Path对象，build_system_prompt每次执行时检查文件存在并读取当前正文，再返回本次组合结果。这是语义命名与读取生命周期同时保持清晰；学生仍负责源码修改，教员未代写或运行。

2026-10-22后续回读：路径命名与函数内读取已经恢复正确，技能目录也已加入。无AGENTS分支的固定提示仍有一处f字符串漏花括号，见技能目录讲义第6节；当前仅待学员修正这一处，未运行验证。

2026-10-22最终回读：缺失花括号已补齐，固定规则、可选工作区约定与技能目录在当前实现中均已接通，静态通过；下一步由学员用自己的Agent产出代码审阅报告。
