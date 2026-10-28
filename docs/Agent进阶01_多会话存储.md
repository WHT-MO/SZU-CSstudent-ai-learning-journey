# 进阶第1节：多会话存储与入口选择

> 2026-10-27。本节实现已全部静态通过：存储层、Agent、CLI、HTTP服务端及Python客户端的会话选择和传递接通。源码由学员亲写；本次未新增多会话实际运行证据。结果见第12节。

## 1. 这一节结束后能做什么

同一个程序可以保存多段独立对话。例如，study会话用于学习，review会话用于审阅项目；每段对话分别保存messages和summary_cache，之后可以按会话名恢复。

架构位置：入口选择会话 → run_agent处理这一段对话 → session_store加载、保存该会话。本节先完成最后一段，之后再把会话名从入口一路传进去。

session_id是一个普通字符串，用来选择哪段历史。例如"study"。它由调用方提供，不是模型生成的内容，也不是某个库自动创建的变量。本节先用明确的会话名；后续CLI保存当前选择，HTTP请求携带这个字段。

## 2. 从固定路径变成按名字选路径

现在HISTORY_PATH固定指向code/agent_v1/session.json，所以三个函数总是处理同一个文件。

保留HISTORY_PATH作为默认会话路径，新增SESSION_DIR，表示同目录下的sessions文件夹。路径约定如下，表中路径均相对于code/agent_v1/：

| session_id | 会话文件 |
| --- | --- |
| "default" | session.json，继续沿用现有历史 |
| "study" | sessions/session_study.json |
| "review" | sessions/session_review.json |

文件名带session_前缀，也避免会话名刚好是Windows保留设备名时直接成为文件名。原历史无需迁移或复制。

新增get_session_path(session_id: str = "default") -> Path，负责检查名字并返回上表对应的Path。它只计算路径，不创建目录，也不读写文件。

名字仅允许英文字母、数字、下划线和连字符，且不能为空。这里的检查对应真实的文件边界：会话名直接参与拼接路径，不能允许../一类输入改变保存位置。

可用标准库re.fullmatch检查整段名字：

```python
re.fullmatch(r"[A-Za-z0-9_-]+", "study_1")
```

使用前import re。方括号表示允许的单个字符，+表示至少一个；fullmatch要求整个字符串都符合规则。符合时返回匹配对象，不符合时返回None。get_session_path遇到不合法名字时抛ValueError即可。

## 3. 三个接口怎样改

| 函数 | 本节接口约定 |
| --- | --- |
| save_session | save_session(messages, summary_cache, session_id: str = "default") |
| load_session | load_session(session_id: str = "default") |
| clear_session | clear_session(session_id: str = "default") |

save_session把新参数放在最后，原来的两个位置参数保持原意。三个函数都有默认值，所以目前runner和CLI已有的调用仍然使用原来的默认会话。

每次进入函数时，通过get_session_path(session_id)取得本次使用的局部变量history_path。函数体中的存在检查、读取、临时文件路径、replace目标和unlink目标，都改用这个局部路径。不要在函数中把全局HISTORY_PATH改成另一个会话的路径。

接口用法如下，messages和summary_cache就是现有代码已经使用的历史列表和摘要字典：

```python
save_session(messages, summary_cache, session_id="study")
messages, summary_cache = load_session(session_id="study")
clear_session(session_id="study")
```

三个调用传入相同的会话名，就会操作同一个会话文件。load_session仍返回原来的两项数据；保存的JSON仍包含原来的两个字段，无需把不同会话装进同一个大字典。

## 4. 保存时创建目录

新会话第一次保存时，sessions文件夹可能尚不存在。只有save_session需要在写入前创建父目录，放进已有的try里，沿用OSError处理。

例如，下面的独立示例为一个笔记路径准备目录：

```python
note_path = Path("notes") / "week1.txt"
note_path.parent.mkdir(parents=True, exist_ok=True)
```

- parent取得文件所在目录。
- parents=True表示缺少上层目录时一并创建。
- exist_ok=True表示目录已经存在时继续执行；它不会清空目录。

保存会话时对本次history_path的父目录做同样处理。临时文件仍由本次history_path.with_suffix(".tmp")生成，写完后replace到本次history_path。这样不同会话的正式文件和临时文件也分别对应。

load_session读取尚未保存的会话时，返回现有的空历史及默认摘要缓存；clear_session只删除选中会话的文件。读取和清除不需要先创建目录。其余JSON解析、旧列表兼容及错误处理沿用现有实现。

## 5. 存储层动手范围与后续

第一项为亲写session_store.py的路径选择和三个接口，现已静态通过。仓库已将sessions目录列入.gitignore，实际会话内容继续留在本机。

完成后静态审阅默认会话兼容、同一session_id的一致使用、命名边界及原子保存路径，不要求新增测试脚本或模型请求。

下一项再接run_agent：接收session_id，并在一次任务的加载与全部保存位置传入同一个值；随后接CLI会话选择和HTTP字段。会话历史分开与并发执行是两个问题，接HTTP时继续沿用现有共享锁，事件分发机制也在后续有并发需求时再调整。

## 6. 首版静态审阅

已正确：默认会话沿用HISTORY_PATH；三个函数均接收session_id并调用get_session_path；读写、删除、临时文件与replace目标已一致使用局部history_path。

首版剩余三处，记录如下：

1. session_store.py第5行的SESSION_DIR目前只有脚本所在目录，末尾还需拼接sessions子目录。否则具名会话会保存在源码目录，也不在现有sessions忽略规则覆盖范围内。
2. 第8行起的get_session_path尚无会话名检查。在选择路径前按第2节检查整个名字，不符合规则时抛ValueError；名字直接参与文件路径，路径分隔符可能改变实际读写位置。
3. 第28行的mkdir目前在try外。将它移进已有try，在write_text之前执行，这样首次创建目录失败也会进入已有OSError处理。

首版当时尚未静态通过；没有新增数据格式校验、测试脚本或模型请求。教员未代改源码。

## 7. 第二次静态审阅：校验结果与原字符串

第二次回读时，SESSION_DIR已补sessions，mkdir已移进已有try，二者正确。已导入re并加入整串名字检查；该次仅剩第10行把re.fullmatch结果赋回session_id的问题。

re.fullmatch返回匹配对象或None，不会返回原字符串。将其赋回session_id后，后续与"default"比较及文件名拼接用到的都是匹配对象，默认会话分支无法命中，文件名也会包含对象的表示文本。

需要保留session_id这个原字符串，用另一个变量（例如match）接收检查结果；只用match判断是否为None，路径分支和拼接继续使用session_id。此处修正后再接run_agent，不增加其他检查或测试。

最新回读：已使用match接收结果并判断None，session_id原字符串供默认判断及路径拼接使用，修正正确；连同此前目录、接口及原子写入路径，存储层静态通过。

## 8. 把会话名传给Agent（已静态通过）

这一项的目标是：调用方指定study后，run_agent加载study的历史，并将本轮每次保存都写回study。

```python
await run_agent("请概括工作区的约定", session_id="study")
```

这里的study由调用方传入，run_agent用形参session_id接收，再把同一个值传给存储函数。只在存储函数声明参数，还不会让上层调用自动传入它；省略传参仍会使用default。

由学员在agent_runner.py完成三处调整：

1. 在run_agent现有user_prompt和max_turns两个参数后，增加session_id: str = "default"。放在最后，使原有第二个位置参数仍表示轮数。
2. 开头的load_session调用显式传入session_id=session_id，沿用原来的两项返回值接收。
3. run_agent内现有七处save_session调用均增加session_id=session_id。当前源码位置为633、647、658、663、682、717、727行，修改后行号可能变化，可搜索save_session定位。

session_id=session_id左边是被调用函数的参数名，右边是当前run_agent收到的变量值。例如收到study，加载与所有保存都继续传study。不要在这些位置写死study或default。

特别要覆盖提前结束和完整回答等分支中的保存：如果只有加载传study，某次保存省略会话名，就会把当前历史写到默认会话。

这一项静态审阅通过后，继续接CLI中的当前会话选择、/reset和HTTP字段。当前存储层已通过，不另设运行确认或测试脚本。

最新回读：run_agent已在原两个参数后增加session_id默认值，load_session及全部七处save_session均传入session_id=session_id，静态通过。当前七处保存位于638、652、663、668、687、722、732行，不因函数签名的换行或末尾逗号另设修改要求。

## 9. CLI选择会话（已静态通过）

### 9.1 用户操作与变量来源

目标是在CLI输入/session study后，之后的普通任务都使用study会话；输入/session review后改用review。两个会话的历史分别由已有存储层加载和保存。

在cli.py的main内、while之前创建current_session_id = "default"。这个普通字符串由CLI持有，命令切换时更新它；放在while之前，才能在多次输入之间保留选择。

| 输入 | 行为 |
| --- | --- |
| /session study | 检查名字，成功后改为study，下次输入提示显示新选择 |
| /session review | 同理，改用review |
| /session | 显示当前会话名 |
| /reset | 清除当前选中会话的历史，当前会话名保持不变 |
| 普通任务 | 将原任务文字及当前会话名传给run_agent |

输入提示也显示当前会话名，例如[study] 请输入任务：。程序启动时选default；以后重新选择某个名字，就能继续使用它已保存的历史。切换本身只更新CLI变量，不调用模型，也不提前创建会话文件。

### 9.2 先认识partition

需要把命令名和后面的会话名分开。str.partition(" ")按第一个空格拆出三项：前面的文字、分隔符本身、后面的文字。例如这个独立示例：

```python
command, separator, argument = "open notes".partition(" ")
```

结果是command为open，separator为空格，argument为notes。没有空格时，例如"open"，结果为("open", "", "")。原字符串不会被修改；对argument再用strip清除两侧空格。

因此对当前user_prompt使用同样操作，就能判断command是否为/session，并从argument取得候选会话名。这里的三个变量来自返回值解包；separator在本次命令处理中无需使用。普通任务仍传原来的完整user_prompt，不要只传拆出的某一项。

### 9.3 本次动手

在cli.py完成这组相互配合的修改：

1. 从session_store同时导入已有的get_session_path和clear_session；在main的while之前初始化current_session_id。
2. 输入提示显示当前会话名；读取输入后拆出命令与参数，在现有命令分流中处理/session。
3. /session没有参数时显示当前选择。有参数时，先用get_session_path(候选名字)检查；它只检查并返回路径，不读写文件。捕获ValueError时显示名字规则并继续输入，当前选择保留；成功后才把候选名字赋给current_session_id，由下次输入提示显示新选择。
4. 普通任务调用run_agent时传session_id=current_session_id；/reset调用clear_session时也传session_id=current_session_id。

复用get_session_path的名字规则，不在CLI另写一份正则。先检查再更新选择，避免一次无效输入把当前会话名变成后续无法加载的名字。/session命令由CLI处理完成，随后回到输入，不把命令送给模型。

完成后静态审阅当前变量的初始化位置、命令拆分、检查与更新顺序、任务和/reset传参，随后接HTTP。不上新测试脚本，不要求为本小节请求模型。

### 9.4 CLI首版静态审阅

current_session_id在while前初始化正确，输入提示已显示当前名；命令拆分、名字检查成功后再更新、ValueError保留旧选择、任务和/reset传参均已正确。新名字会出现在下一次输入提示中，不必再增加单独的切换确认打印。

首版待补两处，记录如下：

1. cli.py第42行拆分后，对argument调用strip并接回变量。整条user_prompt的strip只处理整条输入两端，输入/session   study时，拆出的参数仍有前置空格。
2. 第53行/session分支先区分有无参数。没有参数时显示current_session_id并回到输入；有参数时才进入已有的检查与更新。当前直接检查空字符串，会把合法的/session查看命令当作非法名字。

修正后再接HTTP，不新增测试或模型请求。源码由学员亲改。

最新回读：已增加无参数显示分支，有参数时先strip再检查与更新，CLI整体静态通过。strip放在有参数的else里也正确：整条输入先strip，末尾只有空格的/session会成为无参数命令；多个分隔空格则在参数分支清除。无需为位置或额外continue再修改。

## 10. HTTP携带会话名（已静态通过）

### 10.1 请求中的字段由谁提供

CLI已经用current_session_id选择历史。HTTP入口通过每次请求的JSON正文取得选择，例如发送给本机POST /chat：

```json
{
  "prompt": "你好",
  "session_id": "study"
}
```

调用方提供study，FastAPI按ChatRequest构造本次data对象，因此chat内通过data.session_id取得这个字符串。该字段用于本机Agent选择历史文件。

在ChatRequest现有prompt字段下增加session_id: str = "default"。请求没提供时，Pydantic填入default，现有只发送prompt的客户端仍然使用原来的默认会话。

### 10.2 一次请求的传递链

请求正文 → ChatRequest → chat里的data.session_id → run_agent_to_queue的形参 → run_agent → load_session和save_session。

已有create_task启动run_agent_to_queue，后者才会调用run_agent；因此只增加ChatRequest字段还不能完成传递，需要把值穿过这两次调用。

### 10.3 本次动手

由学员修改http_api.py的四处：

1. ChatRequest增加默认会话名字段。
2. chat内创建Task时，给里面那次run_agent_to_queue调用增加session_id=data.session_id。会话名传给run_agent_to_queue，create_task负责启动返回的协程。
3. run_agent_to_queue在现有prompt、queue参数后增加session_id: str = "default"，接收这次请求给出的会话名。
4. 在现有持锁的run_agent调用处，传入session_id=session_id。

同一请求的会话名是函数参数中的局部值；无需在HTTP模块中保存一份全局当前会话名。每个请求明确携带选择，排队执行时也能继续使用各自传入的值。

最新回读：http_api.py第12行已声明默认会话名，第21行从data取局部值，第23行将它作为第三个位置参数传给run_agent_to_queue，第49行形参接收，第55行在锁内传给run_agent，链路静态通过。第三个位置参数与声明顺序一致，无需为此改成关键字形式。

客户端接线见第11节；HTTP新会话字段的运行证据尚未新增。

## 11. HTTP客户端选择会话（已静态通过）

### 11.1 请求函数接收并发送名字

request_agent负责向本机/chat发送请求。让它在prompt参数后增加session_id: str = "default"，再给现有request_body增加session_id键，值取本函数收到的session_id。

例如当前选择study、任务为你好，发出的JSON就是第10节的两字段对象。正文通过已有client.stream的json=request_body发送，HTTP服务端再沿已接通的链路处理。

### 11.2 交互入口选择名字

沿用CLI已经写过的交互方式，在http_client.py的main内、while前创建current_session_id = "default"；输入提示显示它。

本次命令为/session和/exit。/session无参数时显示当前选择，有参数时检查并更新选择；普通任务继续调用request_agent，并传session_id=current_session_id。空输入直接继续。使用partition和strip的方式与CLI相同，普通任务仍发送完整的prompt。

客户端负责选择并发送名字，服务端负责会话文件。客户端输入检查使用已学的re.fullmatch和相同的[A-Za-z0-9_-]+规则：导入re，不符合规则时显示说明并保留当前选择，成功后才更新。无需引入服务端的路径或存储函数。

HTTPError仍在普通任务请求的现有try中处理；/session是本地命令，处理后回到输入，不发送HTTP请求。/reset属于已实现的直接CLI入口，这里没有新增HTTP清除接口。

### 11.3 本次动手与收尾

由学员在http_client.py完成：

1. request_agent增加默认会话名参数。
2. request_body发送prompt和session_id两个字段。
3. main保存当前会话名，显示当前选择并处理/session的查看、检查和切换。
4. 普通任务调用request_agent时传入当前会话名，沿用现有HTTP异常处理。

这就是本节最后一段接线。静态审阅完整后，多会话这一轮实现收尾；运行证据与静态结论分别记录，不增加测试脚本、模型请求或其他必做功能。

### 11.4 客户端首版静态审阅

request_agent默认参数、request_body两字段、当前会话变量、提示、命令不发请求、检查成功后更新、普通任务显式传参及HTTPError处理均已正确。

客户端首版待补两处，记录如下：

1. http_client.py第53行input取值末尾加strip。否则/session后只有空格时会被当作带空白名字，/exit末尾带空格也无法命中，纯空格输入还会进入HTTP请求。
2. 第4行与第69行仍依赖session_store.get_session_path，按本节分工改为导入re并用fullmatch检查名字。当前函数不读写文件，因此同项目内这次调用可工作；这里调整的是客户端的模块依赖，不把它误报成已经操作了会话文件。客户端本身只需检查字符串，成功后保存原会话名，不符合时显示说明并保留旧选择。

其余接线无需重做。这两项补齐后本节静态审阅即可收尾，不增加测试或模型请求。

### 11.5 输入结果上的strip

第二次回读：已导入re，fullmatch结果用match接收并判断，合法时更新原argument，服务端路径模块依赖已移除，修正正确。

第二次回读时，第53行把strip放在input括号内部，处理的是提示文字；用户输入仍未清理。应先调用input取得返回字符串，再在input右括号外调用strip。

最新回读：第53行已将strip放在input右括号外，清理用户输入；客户端独立校验、查看与切换分支、当前变量、请求两字段及调用传参均正确，整体静态通过。

## 12. 本节完成结果

| 部分 | 已实现并静态核对的行为 |
| --- | --- |
| 存储 | 按session_id选择文件，分别保存messages与summary_cache；默认会话继续使用原session.json |
| Agent | 一次加载与七处保存传入同一个会话名 |
| 直接CLI | /session查看或切换，/reset清除当前会话，输入提示显示当前选择 |
| HTTP服务端 | 从请求正文取得session_id，经后台任务传给Agent；省略字段时使用default |
| HTTP客户端 | 本地/session选择、独立名字检查，并发送prompt和session_id两个字段 |

完整调用链为：入口选择会话 → Agent接收会话名 → 加载对应历史 → 执行当前任务 → 保存到同一会话。

会话历史与摘要分别存档；当前文件工具仍使用既有workspace，HTTP任务由现有共享锁顺序执行。这些是本节的实现范围，不把多会话等同于工作区隔离或并行执行。

本节完成依据为源码静态审阅。此前HTTP连接和文件工具截图仍属于此前版本的运行证据，本次没有新增运行、测试或模型请求。后续学习另定明确目标，本节没有待改源码或额外必做项。
