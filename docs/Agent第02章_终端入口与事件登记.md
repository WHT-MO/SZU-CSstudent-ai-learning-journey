# 第2章应用练习：终端入口与事件登记

> 结果：2026-10-22。两个显示函数已移入cli，main在输入循环前登记一次，事件模块保留空名单与分发，runner移出终端入口，当前拆分通过源码静态审阅。
> 目标：终端入口决定怎样输入和显示，Agent执行流程可由其他Python脚本调用。

## 1. 为什么继续拆这一层

当前run_agent已返回最终消息，模型与工具也能发送事件。但agent_events在导入时就把终端显示函数放进listeners；任何脚本调用run_agent，都会自动获得这些终端监听器。runner还同时承担input循环。

将终端入口单独放进cli.py后，CLI（命令行界面）负责读取用户输入、处理/reset与/exit、登记终端显示监听器。runner执行任务；事件模块把通知交给已登记的接收者。其他Python入口可以选择自己的监听器。

这是本项目结合教材职责划分安排的整理，不要求增加类、插件扫描器或注册框架。

## 2. 文件分工

| 文件 | 本步职责 |
| --- | --- |
| agent_runner.py | run_agent、模型请求、工具调度、上下文与结果返回 |
| agent_events.py | 初始为空的listeners列表，以及emit分发函数 |
| cli.py | 两个终端显示监听器、main输入循环与启动入口 |

现有错误分支和emit异常处理仍含print，因此本步只把正常输入与模型/工具显示的接线放到CLI，不声称所有诊断输出都已经分离。

## 3. 当前动手

1. 在code/agent_v1下新建cli.py。将runner底部async main及if __name__启动段移入；把agent_events中的show_tool_event、show_model_event也移入。
2. agent_events保留asyncio导入、emit和listeners；listeners改为空列表。emit仍按原约定逐个等待监听器并隔离普通异常。
3. cli导入asyncio、run_agent、clear_session和同一个listeners列表。在main的输入while循环开始前，把两个显示函数加入该列表，启动时登记一次。
4. runner从session_store只导入仍需使用的save_session、load_session；clear_session由CLI导入使用。runner内部仍使用asyncio，其导入继续有用途。

“导入同一个列表后追加”会修改emit读取的那个对象；在cli中另写listeners = [...]会让局部名称指向新对象，不能登记到事件模块。应操作导入的原列表，例如使用extend追加函数对象。放在while外是为了每次输入任务时不重复添加监听器。

依赖关系为cli调用runner；runner和cli都使用agent_events。runner无需导入cli，避免把终端入口反向接进执行流程。

整理完成后的终端启动命令为：

```powershell
.\.venv\Scripts\python.exe code\agent_v1\cli.py
```

主README启动命令已随本次拆分通过同步为cli.py。教员不代写学生模块，不为本次函数迁移另设测试或付费请求门槛。

## 4. 首版回读：创建列表与登记成员

2026-10-22回读确认cli已包含main、启动段及循环前的extend，runner已移出入口并清理clear_session导入。尚有两处未完成：

- show_tool_event、show_model_event仍定义在agent_events；cli只导入listeners，因此main引用两个函数名时会NameError。应按本次分工将两个显示函数移到cli。
- agent_events仍是listeners = [show_tool_event, show_model_event]，已登记过两个函数。如果再让CLI追加同一对函数，就会重复显示。本次应改为listeners = []，由CLI登记终端需要的函数。

空列表定义负责创建共享的名单，extend负责加入成员。from agent_events import listeners取得同一列表对象；CLI没有再创建一份名单。当前代码保留旧的非空名单，所以学员质疑重复登记有实际依据。完成两处迁移即可继续，不新增注册接口或校验步骤。

第二次回读：listeners已改为[]，重复登记部分已修。show_tool_event与show_model_event仍定义在agent_events，cli第7行引用时没有定义或导入，NameError仍未解决。当前只需将两个函数的完整定义移到cli导入之后、main之前；导入listeners不会同时导入同模块的其他函数名称。其余入口拆分已符合当前要求，教员未代改或运行源码。

## 5. 拆分通过

第三次回读确认cli第6、23行已定义两个显示函数，第35至36行main在while前登记原列表；模块启动段调用asyncio.run(main)。agent_events仅保留asyncio、初始空listeners和emit；runner的终端入口与clear_session导入已移出，未出现反向导入cli。当前范围静态通过，未运行程序或模型请求。

下一项回到工具系统，新增[运行Python脚本工具](Agent第05章_运行Python脚本工具.md)。这次增加实际执行脚本的能力，已有工作区minimal_loop.py可供后续实际使用，无需另造测试脚本。
