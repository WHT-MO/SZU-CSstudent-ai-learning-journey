# 第 5 章第一小节：工具执行依赖

位置：模型提出 tool_calls 后，本地程序执行工具的阶段。

## 1. 当前项目的连接点

`code/agent_v1/agent_runner.py` 第 579 行建立工具协程列表，第 588 行用 `asyncio.gather()` 并行执行，第 590–592 行把结果按调用索引回填。

`gather` 返回值的排列对应传入顺序。工具实际读取和修改的数据取决于它们执行时的数据状态。接下来先观察一个受控例子，再决定项目中的调度规则。

## 2. 一个概念：执行依赖

当一个操作需要另一个操作产生的数据时，两个操作之间存在先后依赖。例如，解析刚下载的文件，需要先取得下载结果。

当前项目有 read_file、write_file、list_files、edit_file。某些调用互不依赖，某些调用读写同一份数据；后续用实际调用判断如何安排执行。

## 3. 学员亲写的小实验

新建 `code/agent_v1/tool_order_demo.py`，用字典模拟笔记：

```python
note = {"content": "旧内容"}
```

自己实现两个异步函数：

- `write_note()`：先 `await asyncio.sleep(0.1)`，再将内容改为“新内容”，返回“写入完成”。
- `read_note()`：返回字典中当前的内容。

在一个异步 main 中做两组操作，每组开始先把内容复位为“旧内容”：

1. 用 `asyncio.gather(write_note(), read_note())` 运行并打印返回结果。
2. 先 await 写入，再 await 读取，打印读取结果。

给出两组输出，并用自己的话解释读取内容为何有差别。沿用已学的单事件循环入口；教员不代写练习源文件，也不提前给出检查题结果。

## 4. 接回主项目

结合实验解释当前 runner 的并行执行与索引回填各影响什么，再确定简单的工具调度规则。固定延迟用于观察依赖关系，不能据此推断真实文件操作每次都会出现同一种先后顺序。

## 5. 前置复习：async def 与 async with

二者承担不同职责：

| 写法 | 职责 | 当前项目中的例子 |
| --- | --- | --- |
| `async def` | 定义异步函数，函数中可以使用 await | `write_note()`、`summarize_messages()` |
| `async with` | 管理支持异步进入和退出的资源使用范围 | `httpx.AsyncClient` 的使用与关闭 |

调用异步函数会取得协程对象，之后需要 await 或交给 gather 等调度。定义函数本身不会执行函数体。

在 `async with httpx.AsyncClient() as client` 中，`AsyncClient()` 先创建客户端对象，async with 管理其进入和退出；实际请求发生在 post、stream 等调用处。离开代码块时会执行异步清理，正常完成或块内抛异常都会经过退出处理。可以联系以前的 `with open(...)`：它管理文件使用与关闭；HTTP 客户端的退出处理支持异步等待。

两个语法可以一起使用：异步函数中用 async with 管理客户端，再 await 请求函数。并发仍由 gather、create_task 等安排。

本实验注意两点：第一组应 await gather 后再复位并执行第二组；read_note 应返回读取当时的 content 字符串。返回整个共享字典会让之后的修改反映到已经返回的对象上。

## 6. 接回主程序：按整批调用选择执行方式

2026-10-20：学员修正后运行截图与静态代码吻合，两组读写对照已通过。读取先发生时取得的内容已经确定，结果按索引回填只安排这份结果的位置；先后依赖需要在执行环节处理。

当前采用简单规则：

| 一批有效调用的组成 | 执行方式 |
| --- | --- |
| 全部是 read_file、list_files | 沿用 gather 并行 |
| 包含 write_file 或 edit_file | 整批按原调用顺序逐个 await |

学员修改 agent_runner.py 的有效工具执行部分，使用已有 for/if 判断整批组成。两种分支均通过 execute_validated_tool 执行，并按原调用 index 回填结果。混合批次中的读取也参与顺序执行。

输入数据仍是 valid_tools 的四元组 `(index, tool_call_id, tool_function, validated_args)`。第三项是函数对象；tool_functions 注册表存放同一组函数，可通过注册表取出 read_file/list_files 对应函数进行比较。

先静态检查学员实现。学员随后明确小改正确即推进，不额外布置独立调度测试；具体证据见第 10 节。线程等待超时后的底层操作行为见第 11 节。

## 7. 卡点复习：先判断整批组成

先完成“列表中是否存在某类项”的判断，再接执行方式。与项目不同的最小例子：

```python
goods = [("苹果", 2), ("牛奶", 1)]
needs_cold = False

for item in goods:
    if item[0] == "牛奶" or item[0] == "酸奶":
        needs_cold = True
```

这里 goods 是列表，每项是一个元组；item[0] 取得商品名。标志先为 False，发现目标后改为 True，后续非目标项保持它已有的状态。or 两边各写完整条件；单独的非空字符串作为条件会成立。

对应项目，valid_tools 是四元组列表，每项为 `(index, tool_call_id, tool_function, validated_args)`，item[2] 才是函数对象。注册表的 `tool_functions["write_file"]` 也返回函数对象，可用于比较；字符串 `"write_file"` 是名称。

本轮学员先亲写 has_write 判断并保存供静态检查，判断正确后接执行分支。当前截图中的 if 缩进、列表内嵌套 await gather 也需要在执行部分修正；整批并发的 gather 应接收未逐个等待的工具协程。

## 8. 协程与执行结果放在不同阶段

当前 execute_validated_tool 是异步函数，正常完成时返回工具结果字典：

| 表达式 | 取得的对象 |
| --- | --- |
| 调用 execute_validated_tool，尚未 await | 协程对象 |
| await 单次 execute_validated_tool | 一条工具结果字典 |
| await gather，输入整组工具协程 | 按输入顺序排列的结果列表 |

在列表中逐项 await 会等待当前项完成后才进入下一项。即使单项套一层 gather，只有一个调用时也不会让不同列表项并发。await 后的结果字典或结果列表不能再当成工具协程传给外层 gather。

两条分支的出口统一为 executed_results：有写分支逐项等待并收集结果；无写分支先收集协程，再用一次 gather 收集结果。之后共同按原 index 回填。函数对象的判断使用注册表函数值，保留名称字符串只用于查表。

## 9. 同文件修改的冲突与下一小步

原实现先收集协程，再用 gather 并发执行同一批全部工具。同文件的两次编辑都可能先读到相同旧内容，各自替换后再回写，后写入的内容覆盖前一次修改。需要结合依赖决定执行方式，两个调用就可能冲突；结果按索引回填不会重做文件操作。

2026-10-20：学员已保存新调度，分类、含写顺序执行、只读并发和共同回填已静态核对正确，尚未运行验证。gather 的结果排列对应输入顺序，注释应描述“并发执行，按输入顺序返回结果”。

后续封装已完成：学员将整批判断与执行块提取为异步 execute_tool_batch(valid_tools)，返回 executed_results；主循环 await 此函数，再沿用索引回填。原拟安排的独立调度测试已取消，以第 10 节的最新约定为准。

## 10. 调度入口：静态检查通过

异步函数的完整定义语法是 `async def execute_tool_batch(valid_tools):`。2026-10-20 学员已完成封装，定义、返回结果列表和主循环 await 调用均静态核对正确；教员此前文字漏写 def 已更正。

学员随后要求小改无问题直接推进，省去逐步独立验证。本次 test_tool_scheduling.py 及配套数据的练习取消，当前按静态检查通过继续课程；没有该运行结果，不将已取消的测试记成待完成门槛。

## 11. 工具超时：等待与实际执行

当前工具通过 `asyncio.wait_for(asyncio.to_thread(...), timeout=10)` 执行。wait_for 限制等待时间；当同步工具已在工作线程中运行时，超时通常无法强行终止这个线程里的函数。

假设某工具需要 12 秒：第 0 秒开始运行，第 10 秒等待方得到超时并生成工具错误结果，第 12 秒底层操作仍可能完成。超时消息说明没有按时取得结果，不能据此判断文件没有被修改。

因此正常完成时的逐个 await 与超时后的底层工作状态要分别理解。先明确现有实现的边界，按实际需要处理后续调度；本节不另布置运行实验。

## 12. 本节收束：工具执行的完整分工

工具描述给模型说明名称、用途与参数；运行时参数校验检查模型实际传来的数据；工具内部路径检查限制实际访问位置；执行包装处理等待、超时、操作异常和结果格式。说明书本身不会执行函数，也不能代替后续检查。

当前实现把普通执行错误变成可关联 ID 的工具结果，让模型有机会解释或调整；收到 CancelledError 则向外抛出，让取消沿调用链传播。超时和取消等待均不能保证已运行的工作线程停止。

批次调度决定不同调用如何开始与等待，结果回填决定返回消息如何对应原调用。只读批次 gather 并发；含 write/edit 的批次逐个 await。正常完成的顺序有保证，超时后可能仍运行的线程须另看其实际状态。gather 按输入顺序返回结果，不代表工具按该顺序完成。

2026-10-20 按学员要求将纯说明合并给出，接到 [消息的三种用途](Agent第06章_消息的三种用途.md)，再开始 [工具执行通知](Agent第07章_工具执行通知.md) 的实际任务；不加新的运行验收。

## 13. 函数如何交给线程执行，以及替代方式的边界

学员提出三个问题：为什么没有 tool_function(...) 仍会执行、to_thread 的两个参数怎样对应、为什么不直接使用异步函数或 gather。以下一次讲清，不增加练习。

### 函数与参数分别交付

`try` 只负责圈定异常处理范围。`asyncio.to_thread(tool_function, validated_args)` 把函数对象与调用参数一起交给线程执行；线程里的实际调用是 `tool_function(validated_args)`。

例如 tool_function 指向 read_file，validated_args 是 ReadFileArgs(path="a.txt")，则实际执行 read_file(validated_args)，对应 read_file 定义中的 file_args。validated_args 是一个完整的已校验对象，其 path 等字段由工具函数读取。

这里不提前加括号，是为了把调用交给 to_thread。写成 to_thread(tool_function(validated_args)) 会先在当前线程执行同步函数，再把它的返回值交给 to_thread；当前工具返回字符串，字符串无法充当待执行函数。

### 内容与结果字典的来源

read_file 通过 read_text 返回文件内容；write_file 完成 write_text 后返回状态文字。to_thread 负责传递这些返回值，不生成文件内容。wait_for 正常完成时继续返回该值，于是赋给 tool_content；最后 make_tool_result(tool_call_id, tool_content) 才生成含 role、tool_call_id、content 的工具结果字典。timeout=10 是 wait_for 的参数，不会传入工具函数。

### 三个工具的职责与实际取舍

| 方法 | 职责 |
| --- | --- |
| to_thread | 将同步函数放进工作线程，避免它占住事件循环线程 |
| wait_for | 等待可等待对象，超时后请求取消并处理超时 |
| gather | 并发等待多项可等待工作，收集结果 |

现有文件工具是同步 def，直接调用会占住事件循环线程。to_thread 用来适配这些工具；外层 wait_for 提供等待超时。超时取消的是异步等待，已开始执行的线程函数不能由此强制停止。更准确的结论是“超时后文件状态不能仅凭超时结果判断”，不应讲成这个组合必然导致文件损失。

仅将函数声明改成 async def，内部仍直接执行 read_text/write_text，运行时依然阻塞；超时回调也可能无法及时运行。真正使用可异步等待操作的函数可直接交给 wait_for，取消在可响应的等待点生效，已经发生的文件改动仍不会自动撤回。

gather 可以包围多个执行包装或 to_thread 协程，它不提供强制终止运行线程、撤回写入或处理同文件依赖的能力。当前正常完成的含写批次逐个 await；若写入超时后底层线程仍在执行，就不能推断其后的同文件操作仍有完整的顺序保证。若要保证“超时后文件一定没改”，须另设计写入提交与取消规则，不能只换一个 asyncio 方法。

参考：[Python 3.12 的 to_thread、wait_for 与 gather](https://docs.python.org/3.12/library/asyncio-task.html)、[运行中的线程任务与取消](https://docs.python.org/3.12/library/concurrent.futures.html#concurrent.futures.Future.cancel)。
