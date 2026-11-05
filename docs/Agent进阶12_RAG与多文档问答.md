# 进阶第12节：RAG与多文档问答

> 2026-11-04开始并完成。本地BGE真实编码、余弦比较、前k份资料选择及聊天模型根据原文生成带出处回答均已有实际运行证据；单文档问题和跨两份资料的复合问题已跑通。Python源码由学员亲写，本节是独立学习实验，不要求主Agent接入向量数据库。

## 1. 这节要解决什么

检索增强生成（RAG）是先找出问题相关资料，把问题和资料一起交给模型，再根据资料生成回答。关键词、语义或向量等都是可能的检索方式，向量数据库不是定义本身。概念参考[Microsoft Learn](https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation)。当前复用Python、本地资料和已有模型。

现有list_files/search_file/read_file已能支持工具驱动的查资料问答，不否认已有能力，也不把再造同名工具当成学习目标。本节新增内容是由代码统一管理多份资料、选择相关片段、保留出处后组织回答。第一步先读入资料，之后才做真正的相关性检索；加载全部文件不等于已经检索或应该全部塞入模型。

检索方法、工具接口与RAG流程是不同层次：本项目search_file把字符串匹配封装成Agent可调用的工具；RAG是把检索结果交给模型生成依据资料的回答，向量检索是可选方法之一。之前布置的retrieve_knowledge逐行关键词匹配与已有工具底层高度重复，对当前学员不作为必做项。仅增加一个返回字典列表的函数并不代表已经新增语义检索能力，教员已调整此段教学安排。

关键词适合文件名、编号等明确词项；embedding将文字转为数字向量，用相似度处理部分不同措辞但语义相关的情况。两者可互补，实际方案也可混合使用，参见[Anthropic关于检索方式的说明](https://www.anthropic.com/research/contextual-retrieval)。当前两份短资料用现有搜索就够；下一步学习向量检索是为了掌握新方法，不把向量库视为当前应用的硬性需求。

学员进一步问“模型已能理解模糊意图并找相近文件，为什么还要embedding/RAG”：这种能力来自模型的语义理解、已在上下文中的候选，以及工具取得的目录/正文等事实。模型可以改写关键词、比较候选并向用户澄清，这是真正有效的工具驱动检索。按需通过glob/grep等工具取得上下文也是已有工程方案，参考[Anthropic上下文工程文章](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)。不能因为它没有向量库就说Agent缺少检索增强。

需要区分候选召回和看到候选后的理解：聊天模型能理解已有候选，不表示全部资料已经进入其上下文或被建立索引。embedding检索提前把资料编码为可比较表示，在大范围资料中筛选语义候选，再由聊天模型精读判断。Agent也能用查询改写和多轮工具实现检索，是否增加向量后端取决于命中覆盖、查询耗时/输入量，以及预处理和索引更新成本，并不是“没有embedding就做不到”或“大资料必用向量”。

对当前两份短资料和模糊文件名查找，推荐继续使用现有工具，不为演示强装向量库。以后若有收益，可把semantic_search作为与search_file并列的检索工具供Agent选择，无需替换run_agent或另搭一层必需框架。本节embedding及手写余弦的定位是独立学习实验，帮助理解另一种后端，不能当成当前主Agent待修缺陷或所有Agent的必备能力。

## 2. 当前资料与目标问题

教员已按当前session_store.py、tool_policies.py与文件工具实现准备两份短资料：workspace/knowledge/sessions.md与tools.md；可提交的原始样本保存在docs/rag_demo/。这些是本节的固定学习资料快照，运行实现仍以源代码为准。

基础问题“聊天记录保存在哪个文件里？”已完成。接下来用“会话study保存在哪里？只读模式能否修改文件和运行脚本？”检索两个文件，回答需标注各自的来源路径，资料没写明时说明未找到依据。当前以整篇短资料为单位编码和引用；原关键词片段方案中的行号引用需配合分段和行号元数据，不作为当前整篇实验的额外门槛。不把索引/向量库设为先决条件。

## 3. 资料加载初稿

新建code/agent_v1/rag_demo.py，导入tools中的resolve_workspace_path，编写普通函数load_knowledge_documents() -> list[dict]。本步返回供后续检索使用的内部数据，先用普通字典即可，不增加业务结果类。

实现目标：通过resolve_workspace_path("knowledge")取得资料目录；遍历该目录直接包含的.md文件，按UTF-8读取每份内容；为每份资料记录path与content，加入列表，最后返回整个列表。

新API：Path.glob("*.md")枚举当前目录匹配.md扩展名的文件路径对象，当前不递归子目录。循环变量例如file_path是Path对象；file_path.name得到文件名，例如sessions.md；file_path.read_text(encoding="utf-8")返回原文字符串。path字段使用knowledge/加文件名，供后续回答引用；content保存完整文字。

返回数据形状示意：

```python
[
    {"path": "knowledge/sessions.md", "content": "第一份资料的全文……"},
    {"path": "knowledge/tools.md", "content": "第二份资料的全文……"},
]
```

本步只写加载函数，不增加main、工具注册或模型调用。静态检查正确后直接进入片段选择，不新建测试脚本。错误处理与调用入口按实际使用场景接入，不重复添加已有工作区边界检查。

资料加载静态通过：目录转换、glob、UTF-8读取、字典收集与循环后返回均正确，path已修为knowledge/加文件名，工作区相对路径元信息完整。不增加独立测试门槛。

## 4. 可选对照：关键词检索（不再必做）

以下保留原练习说明供对照，已从当前必做任务撤下。学员已新增retrieve_knowledge的空声明，先用pass作为空操作占位，避免空函数体导致语法错误；不要求继续实现其重复的关键词匹配，也不代删学员源码。

本节两份短资料中的规则主要各占一行，因此先以一行作为可检索片段，命中时保留文件路径、原始行号与原文。这个基线复用已有search_file的字面匹配思路，增加跨资料遍历和供程序使用的结构化结果，不注册同名新工具。以后处理长段落时再根据上下文需求调整片段范围。

在rag_demo.py增加普通函数`retrieve_knowledge(documents: list[dict], keywords: list[str]) -> list[dict]`。documents是加载函数返回的资料列表；keywords是调用方提供的关键词列表，例如["会话", "只读"]。当前先用显式关键词理解检索规则，不要求本步解析整句中文问题或调用模型生成关键词。

规则为任一关键词出现在当前行就保留该行，按原样、区分大小写匹配。每条命中结果含path、line、content；同一行即使命中多个关键词也只加入一次。行号从每份文件的第1行开始，标题与空行也计入原始行号。

实现过程：先准备命中结果列表；遍历documents中的每份字典，使用document["content"].splitlines()并以enumerate(..., start=1)取得行号和原文；对每行遍历keywords，命中后将document["path"]、当前行号和原文加入结果列表，并结束当前行的关键词循环，继续下一行；所有资料处理完再返回列表。空命中时自然返回空列表，不生成未被资料支持的内容。

例如关键词["session_study.json"]，应能从sessions.md第5行取得如下数据：

```python
[
    {
        "path": "knowledge/sessions.md",
        "line": 5,
        "content": "例如会话study的存档是code/agent_v1/sessions/session_study.json。",
    }
]
```

此对照练习没有新增main或模型请求，不设独立测试或验收要求。

## 5. 当前主题：embedding与向量相似度

embedding是模型把文字编码成一串数字，在Python中可表示为list[float]；数字个数叫维度。比较资料和问题时使用相容的模型编码方式，让它们位于同一向量空间。真实向量各维通常不能直接命名为某个主题；当前二维示意的数值是人工构造，只用于理解几何关系，不宣称是真实模型输出。

向量库负责存储与检索服务，小规模样本可直接计算相似度。当前选余弦相似度学习打分，它比较方向，对任一向量作正数倍缩放不会改变分数。理论上同向为1、垂直为0、反向为-1；这些是几何关系，不直接等于文字是否相关、是否反义或答案正确的概率。模型可能使用其他距离/相似度，之后按所选模型说明接入。参见[Sentence Transformers的相似度说明](https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html)。

计算分成三步：

1. 对应位置相乘并相加，得到点积，例如[1, 0]和[2, 0]的点积是1*2+0*0=2。
2. 每个向量的数字先平方、相加，再开平方，得到各自长度。上面两个向量长度分别是1和2。
3. 点积除以两个长度的乘积，得到2/(1*2)=1，说明方向相同。

```text
相似度 = 对应位置乘积的总和 / (a的长度 * b的长度)
向量长度 = sqrt(各位置数字的平方和)
```

平方在Python中可写x ** 2；from math import sqrt后，sqrt(9)得到3.0。使用下标循环range(len(a))即可逐位读取a[i]和b[i]，当前不要求先学习zip或使用数值库。

## 6. 当前动手：计算余弦相似度

在独立的rag_demo.py中新增普通函数`cosine_similarity(a: list[float], b: list[float]) -> float`，作为理解向量打分的学习实验。它不承担主Agent的文件查找功能，也不要求为此改造现有工具或接数据库。后续真实embedding产生的向量可交给它打分；批量计算或大型检索再按具体需求选库/索引，不把手写循环当成高性能实现。

两向量必须有同样的数字个数，否则抛ValueError。准备点积、a平方和、b平方和三个累加值，逐位计算。若任一平方和为0，抛ValueError，因为零向量的长度为0，公式分母为0；这也覆盖空列表，不额外重复空列表检查。用sqrt算两个长度，最后按公式返回相似度。

本步只编写同步数学函数，不发模型请求，不新增main或测试脚本。加载函数及关键词pass占位已静态正确，不重开验收。当前仍未选择embedding模型或配置其接口，不假定现有聊天模型能直接返回embedding。

余弦函数初稿静态审阅：维度检查、zip配对及最后的除法形式正确。待修四处：sum(ax * bx)及sum(x ** 2)把单个数字传给sum，会TypeError；已有循环中的+=负责累加，直接累加本次的乘积/平方即可。向量长度须先累加全部平方，再在循环之后开一次平方，不能逐项开平方再相加，例如[3,4]长度为sqrt(9+16)=5，逐项求和会得到7。b循环当前误加到norm_a，应累加b对应的变量，否则norm_b一直为0。除法前补零向量检查，抛ValueError。本轮只指出并解释这些实际问题，源码由学员修正，不运行测试或模型请求。

最新回读：sqrt已移到各自循环之后，b循环已更新norm_b，零向量检查也已补齐；当前仅剩三个sum仍包住单个数字。明确分别替换原循环的对应行：点积直接+= ax * bx，a平方和直接+= x ** 2，b平方和同理。解释循环中+=已经把每轮数字累加，例如0→3→11；sum([3,8])接收一组数字，sum(3)不能成立。给出局部替换行帮助澄清，不代写完整函数或新增运行门槛。

最终静态通过：学员改用sum(a * b for a, b in zip(vec_a, vec_b))及两个平方和生成器，sum接收可迭代对象，开平方及边界检查均正确。该写法与循环累加同样有效，不要求照搬此前局部写法。不新增测试或据此宣称已运行真实语义检索。

## 7. 已完成：准备本地embedding运行库

学员当前没有现成embedding模型或接口，询问路线及“向量数据库能算是否还要模型”。本次推荐本地CPU小模型：不需要新增embedding API密钥，便于看清文字编码和向量检索的分工。编码器采用BAAI/bge-small-zh-v1.5，运行库采用FastEmbed，当前几份短资料的向量先保存在Python内存中。

三项职责分开理解：embedding模型将文字编码为语义向量；余弦函数或向量数据库对已有向量比较/筛选；现有DeepSeek聊天模型根据选中原文生成回答。某些数据库能自动编码，是关联的embedding函数/服务代为调用模型，并非相似度公式直接理解中文；例如[Chroma文档](https://docs.trychroma.com/docs/embeddings/embedding-functions)说明可在增改查时自动调用绑定的embedding函数。一体化产品可以封装这些步骤，本节分别演示有助于理解，并不要求生产代码照此拆分。

已于2026-11-04核对[FastEmbed官方资料](https://pypi.org/project/fastembed/)，当前已发布0.9.1，可使用CPU和ONNX Runtime；所选中文模型输出512维，官方支持表标注模型大小约0.090 GB，见[支持模型表](https://qdrant.github.io/fastembed/examples/Supported_Models/)。这是模型权重规模，安装依赖另计，不声称此模型为最新或所有任务最优。FastEmbed是Python运行库，BGE是实际编码模型，不要把两者当作同一个东西。

教员只读核对项目解释器为Python 3.12.10，尚未代装依赖或下载模型。学员在PowerShell执行：

```powershell
& "D:\code\dsh\python-course\.venv\Scripts\python.exe" -m pip install "fastembed==0.9.1"
```

这一步安装库及依赖；BGE权重会在下一步首次初始化TextEmbedding时下载，不在当前步骤生成向量。当前不改主Agent或安装数据库；真实接口仅在依赖准备好后接入。本节是独立学习实验，主Agent继续用现有工具。

安装已核实：项目.venv/Lib/site-packages/fastembed-0.9.1.dist-info/METADATA的Name与Version符合要求。教员只读文件核对，没有导入模型或代执行安装。

## 8. 已完成：初始化模型并生成真实向量

在rag_demo.py顶部导入fastembed的TextEmbedding，末尾增加普通def main()及标准脚本入口。当前调用的是本地同步编码接口，先用同步入口，不另建模型服务或聊天请求。

模型实例放在main内创建：TextEmbedding(model_name="BAAI/bge-small-zh-v1.5", cache_dir=str(resolve_workspace_path(".models/fastembed")))。cache_dir是权重缓存目录，使用workspace下的.models/fastembed；已有Git忽略规则覆盖此目录，避免权重混入学习代码提交。缺少缓存时首次初始化会下载并加载权重，后续可复用缓存。构造参数已核对本机0.9.1实现，默认英文模型不适用于本节选择，因此明确指定中文模型名。

main的完整数据流：

1. documents接住load_knowledge_documents()返回的资料字典列表，从每份字典的content取出原文，整理成字符串列表texts。
2. 使用同一个embedding_model实例的passage_embed(texts)编码资料。它返回逐个产出NumPy数组的生成器；遍历时对每个vector调用tolist()转为普通Python数字列表，收集成documents_vectors。输入资料顺序与输出向量对应。
3. 准备question="聊天记录保存在哪个文件里？"，调用embedding_model.query_embed(question)编码问题。这也返回生成器，即使只有一条问题也要取出其中的一个向量。可先list(...)收集，再取[0]并tolist()，得到question_vector。
4. 当前两份资料应对应2个向量，该模型输出512维。需要观察形状时可打印数量与维度；现有实现直接输出两篇资料的相似度即可，不追加必做的打印或测试。
5. 用zip(documents, documents_vectors)逐一配对资料与向量，调用cosine_similarity(question_vector, vector)，显示文件路径与分数。比较两个分数即可，当前不添加排序函数或设定通用相关性阈值。

API转换写法示意：

```python
documents_vectors = [vector.tolist() for vector in embedding_model.passage_embed(texts)]
question_vector = list(embedding_model.query_embed(question))[0].tolist()
```

生成器是按需产出结果的可迭代对象；list(...)将其收集成列表；其中的NumPy数组是带数值运算功能的数组，tolist()再将单个向量变成普通list[float]，与学员的余弦函数输入一致。不要把问题向量的一层列表与多份资料的二维向量列表混淆。已核对安装版本中query_embed/passage_embed签名及NumpyArray返回类型，不按SDK错误的个别文档字符串推断为稀疏向量。

这一入口完成后首次运行将下载模型并实际编码，输出数量、维度及两个得分；它验证新接入的本地编码行为，不是重复给已有数学函数新增测试。源码由学员亲写，教员不代执行模型下载/编码；主Agent保持原有工具，下一步再连接选中原文与聊天回答。

入口草稿释疑（2026-11-04 17:21）：用户说看不懂，回读见import TextEmbedding及texts = list[*documents["content"]]。当前需补前置：fastembed是包，TextEmbedding是包里的类，应from fastembed import TextEmbedding；documents是字典列表，需要逐份取出document后再读取document["content"]，用普通for和texts.append展示，不再只给压缩的列表表达式。list[dict]描述类型，与[]建立结果列表用途不同。模型初始化参数、passage_embed生成器转tolist及query_embed取第一个向量的已有写法正确，解释其数据形状，暂不堆叠新接口。沿用用户变量documents_vectors，避免文档单复数差异造成额外NameError。评分循环与函数外main入口尚未写，不把当前草稿记为可直接运行或已经下载模型。

评分循环回读（2026-11-04）：导入已修正为from fastembed import TextEmbedding，texts的列表推导逐份取content正确，模型与向量转换也正确。当前独立写zip(documents, documents_vectors)只创建配对迭代器，后面的循环没有使用它；print(documents["path"], sim)仍把资料列表当字典。需在同一循环用for document, vector in zip(documents, documents_vectors)取到一份资料和对应向量，再比较并打印document["path"]。文件最外层尚缺标准main启动入口。只修这两个连接点，不重写已正确代码；首次下载与编码仍待学员运行，教员未执行模型。

编码入口静态通过（2026-11-04 17:45）：已使用for document, vector in zip(documents, documents_vectors)配对并输出document["path"]与余弦分数，文件最外层标准main入口正确。导入、正文提取、同一模型编码资料及问题、转换为普通列表和评分流程均静态通过，不再新增局部测试。当前进入首次真实运行：由学员使用根目录.venv的解释器执行rag_demo.py；首次无缓存时需下载模型，预期看到knowledge/sessions.md和knowledge/tools.md各自的得分，行顺序不作要求。sessions更相关是待实测的预期，不能提前记为检索成功；收到实际输出后再进入选择原文与生成答案。

真实编码运行成功（2026-11-04 17:55）：学员截图显示knowledge/sessions.md得分0.5466932274820848，knowledge/tools.md得分0.4024506003061275，当前问题仍为“聊天记录保存在哪个文件里？”。两篇资料及问题的真实编码、余弦比较已跑通，本次会话资料排名更高。未单独观察下载过程，不把编码成功写成新下载或缓存行为已验证。

## 9. 已完成：选出最高分资料并保留原文

先完成检索结果的选择，再接现有聊天请求。当前只取一篇资料，用max按分数选出整条记录即可，无须给所有结果排序，也不设通用分数阈值。

在main现有评分循环前准备scored_documents列表；每次计算sim后，把当前document与sim以{"document": document, "score": sim}的形式一起保存。列表里保留原始资料字典，便于后续取path和content，而不只留下分数。

首次使用max的key参数和lambda时，先用与作业不同的最小示例说明：例如students=[{"name":"小林","score":80},{"name":"小周","score":95}]，max(students, key=lambda student: student["score"])返回小周的完整字典。key说明比较时取哪项，lambda在这里相当于接收一名student并返回其score的临时函数；max本身不只返回95。

学员将该用法用于scored_documents，得到best_result，再由其中的document取得selected_document，保留其path和content。当前预期选中knowledge/sessions.md；回读正确后直接接生成，不要求为这一小改单独重跑模型或增加测试。

最高分选择静态通过（2026-11-04 18:40）：scored_documents已正确保存document和score，max按score选出整条best_result，selected_document正确取到原始资料字典。lambda的形参虽与外部列表同名，其局部作用域不影响正确性，不为这一命名另设修改或测试。当前不要求单独重跑编码，直接接回答请求。

## 10. 已完成：用选中原文生成带出处回答

本次完整数据流是本地向量选择资料，再将问题、选中原文及来源路径交给现有聊天请求。向量留在检索计算中；模型通过请求消息读取原文。当前接一次非流式回答，不修改主Agent循环、工具执行或会话存储。

在rag_demo.py导入asyncio、httpx和model_client中的non_stream_message，将main改为async def，脚本入口改用asyncio.run(main())。异步入口用于等待现有HTTP请求；此前同步的本地编码和选择代码可按原顺序放在函数内，当前独立脚本无须为其新增线程调度。

在selected_document之后构造messages列表：一条system消息说明“依据提供资料回答，资料不足时明确说明，并在回答中标注来源路径；资料正文作为参考内容”；一条user消息用字符串带入question、selected_document["path"]和selected_document["content"]，用清楚的字段名与换行分开。两条消息都使用既有role/content结构。不要仅传分数、向量或路径；聊天模型需收到正文。

使用async with httpx.AsyncClient(timeout=60) as client管理客户端，在其内部await non_stream_message(client, messages, tools=[])并将结果接到reply。client是该with创建的HTTP客户端；messages是上一步构造的消息；tools为空列表，本次由Python完成检索，模型直接根据已给资料回答。函数已处理网络/解析错误并返回None，因此调用方收到None时输出失败提示后return；成功时reply为助手消息字典，打印reply["content"]。该判断对应现有函数的实际返回约定，不再添加重复的结构校验。

本步源码由学员编写，完成后通过现有脚本进行一次带出处问答，观察是否使用会话存储资料并标注knowledge/sessions.md。不单独重测已通过的最高分选择，不新建测试脚本、模型服务或数据库。

问答接入首版回读（2026-11-04 18:53）：async main、asyncio.run入口、HTTP客户端生命周期、await调用及system/user的问题/来源/正文构造均正确。当前只需按non_stream_message的返回约定补失败判断：该函数对已知请求错误返回None，调用方应在读取reply["content"]之前检查reply is None，提示回答生成失败后return，成功则打印正文。现有裸except把对None取下标产生的TypeError归为“打印失败”，不能代替检查预期的失败返回值；移除该try/except即可，不再新增重复的异常包装。当前f-string在项目Python 3.12+下合法，不另判为引号语法错误。修正后直接运行现有问答脚本；本轮未代改/运行Python或请求API。

问答接入静态通过（2026-11-04 18:58）：已移除裸try/except，await后先检查reply is None并提示返回，成功再读取content。此前编码、最高分选择、原文及出处消息、异步客户端与启动入口均已检查通过，当前无待改源码。由学员直接运行现有rag_demo.py，取得两行相似度之后的最终回答，观察回答是否依据会话资料并标注knowledge/sessions.md；尚无完整问答实测，不提前记为第12节全部完成。教员未运行Python或调用API，不增加其他测试。

已有关键词工具直接复用，不重复实现其底层。根据数据与问题决定是否引入索引/向量库、重排及片段策略，不把这些都设成先决条件。第11节保持完成，不重开局部验收。

基础RAG实际成功（2026-11-04 18:59）：学员截图显示两篇资料得分仍为sessions 0.5466932274820848、tools 0.4024506003061275。最终回答给出default的session.json、具名session_<session_id>.json及study示例，并说明存档包含messages和summary_cache，末尾来源为knowledge/sessions.md。教员回读两份knowledge原文，回答与本节会话资料一致。加载/编码/比较/最高分选择/原文入请求/模型回答与出处的完整基础流程已实际跑通；该单文档问题阶段完成，不要求重跑或补局部测试。

## 11. 已完成：让一个问题使用多份资料

原来的max适合只取一份资料。综合问题分别需要会话存储资料与工具策略资料，因此本步将检索结果改为前k项，再把多份原文带入同一次回答请求；这是新增多来源能力，不重复验证已完成的基础流程。

问题改为“会话study保存在哪里？只读模式能否修改文件和运行脚本？”。在main里将scored_documents按score从高到低排序，得到ranked_results；设置top_k=2，用切片取前top_k项为selected_results。新API sorted返回新的排序列表，reverse=True表示从大到小，例如sorted([3,1,2], reverse=True)[:2]得到[3,2]；字典记录继续使用已学过的key=lambda item: item["score"]指定比较字段。

selected_results每一项仍是含document和score的记录。遍历这些记录，先取出其中的document，再把该资料的path和content整理成“来源：...\n资料正文：...”的字符串，收集为context_parts；通过"\n\n".join(context_parts)组合成context。user消息带入question与整个context，替换此前仅引用selected_document一份资料的构造。沿用现有system规则和non_stream_message调用。

当前两份短资料都与复合问题有关，top_k=2会将两份都选入，本步用于学习多来源结果与请求组织，不声称这两篇样本可证明筛选效率。完成后运行现有脚本，目标是同时回答两个主题并分别标注knowledge/sessions.md与knowledge/tools.md。更多资料、分段、召回质量及索引按后续需求处理，不在本步新增第三份资料、数据库或测试脚本。

多来源代码静态通过（2026-11-04 19:17）：sorted按score降序后[:2]正确，context_parts列表推导逐项取得document的path/content，join及user消息带入context均正确。不强求另建top_k变量或改回显式for。当前仅question仍是旧的“聊天记录保存在哪个文件里？”，需换成本节复合问题“会话study保存在哪里？只读模式能否修改文件和运行脚本？”，随后直接运行现有脚本观察两个主题及两个来源。未代改/运行Python，不增加测试。

## 12. 本节完成结果

2026-11-04 19:19学员截图确认复合问题实际成功：sessions得分0.6511935725947252、tools得分0.6599381060703613；回答给出study存档code/agent_v1/sessions/session_study.json并标注knowledge/sessions.md，随后说明只读模式不能修改文件或运行脚本，列出允许read/list/search及拒绝write/edit/run_python，标注knowledge/tools.md。当前源码也已换为对应复合问题，取前两份并将各自原文与路径带入同一请求，回答与本节资料一致。

本节实现与运行目标完成，没有剩余必做代码、额外检索测试或索引改造。小样本成功不等于已完成通用检索质量评测；分段、重排、持久化索引和向量库按实际需求另开。独立复写和解释掌握继续按证据记录。下一主题为[任务用量与运行记录](Agent进阶13_任务用量与运行记录.md)，从CLI整项任务计时开始。
