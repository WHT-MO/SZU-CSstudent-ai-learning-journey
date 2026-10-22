# 第5章应用练习：运行Python脚本工具

> 结果：2026-10-22。实现已静态通过；学员已通过Agent实际运行已有脚本并追加报告，截图、会话工具返回与本地报告一致，本项实际使用完成。
> 架构位置：模型请求run_python → 既有参数校验 → 工具包装 → 子进程执行 → 结果回填 → 模型继续。
> 教材对照：[第5章工具系统](https://www.dgzhuya.com/modules/ch05-tools)。

## 1. 目标与新知识

当前Agent能读取和修改代码，还不能亲自运行脚本。新增run_python，让模型指定工作区内一个非交互Python脚本，取得退出码、标准输出stdout和错误输出stderr。

子进程是当前程序另外启动的程序。Python标准库subprocess负责启动和收集结果；subprocess.run会等待这个程序结束，返回CompletedProcess对象。无需安装新依赖。它是普通同步函数，本项目已有to_thread负责将同步工具放到线程运行。

下面是独立的API用法示例，不是本次工具实现：

```python
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-c", "print(6 * 7)"],
    capture_output=True,
    text=True,
)
```

列表首项是要启动的程序，后面各项是传给它的命令行参数。sys.executable是当前Python解释器的路径，-c让该解释器执行后一项中的Python文字。示例正常完成时result.stdout包含42及换行。

| 结果字段 | 含义 |
| --- | --- |
| result.returncode | 程序退出码；0通常表示正常退出，非0表示异常或程序主动报告失败 |
| result.stdout | 脚本写到标准输出的文字，例如print |
| result.stderr | 写到错误输出的文字，例如未捕获异常的traceback；非空本身不等于退出失败 |

这些是被执行程序的结果，不是另一次模型回答。check=False允许保留非0退出时的三项数据，由Agent据此判断。

## 2. 参数模型

在tool_schemas.py定义RunPythonArgs，当前只有path: str，描述为相对于workspace的非交互Python脚本路径。沿用现有BaseModel和Field模式，不新增任意命令字符串或解释器参数字段。

## 3. 实际函数

在tools.py导入subprocess、sys及RunPythonArgs，实现普通def run_python(...)->str：

1. 用resolve_workspace_path处理path，得到script_path。
2. 调用subprocess.run，按下表传参。
3. 正常返回时，整理为包含returncode、stdout、stderr三个清楚标签的字符串，交给既有工具结果封装。

| 参数 | 本次取值与原因 |
| --- | --- |
| args | [sys.executable, "-X", "utf8", str(script_path)]；固定使用当前解释器运行文件，UTF-8模式使子进程输出与读取编码一致 |
| cwd | workspace_root；脚本的相对文件路径以工作区为起点 |
| capture_output | True；收集stdout、stderr |
| text、encoding | True、"utf-8"；读取为文字 |
| stdin | subprocess.DEVNULL；本工具运行无需终端输入的脚本 |
| timeout | 5；由subprocess控制直接子进程的运行等待 |
| check | False；非0退出也返回结果对象 |

命令参数使用列表，shell使用默认False。cwd是工作目录，不是文件权限隔离；脚本仍具有当前账号权限，本阶段使用本人维护的工作区脚本。resolve_workspace_path只约束被选脚本的位置。

超时捕获subprocess.TimeoutExpired，转换为内建TimeoutError并携带简短原因，交给现有工具包装的超时分支。Python 3.12的asyncio.TimeoutError是该内建异常的别名，因此可沿用既有处理。subprocess.run自身超时会终止并等待直接子进程；这与外层wait_for只停止等待的机制不同。取消等待不会撤销脚本已经产生的文件修改，本步也不承诺管理脚本再创建的进程树。

## 4. 接入已有工具系统

沿用现有注册方法，添加run_python的AgentTool说明，说明使用当前Python解释器、运行非交互脚本、返回三项结果且可能修改文件；加入tool_arg_models、tool_specs和tool_functions。

在execute_tool_batch的判断中，把tool_functions["run_python"]也归入需要整批顺序执行的一组。脚本可以写文件，不能把它按普通只读工具安排并发。

本次动手范围是新参数、函数、注册与调度接入。教员不代写源码，不运行脚本、模型请求或测试。学员实现后先审阅源码；实际使用可沿用工作区现有minimal_loop.py，不另加验证脚本。

## 5. 已核对的官方资料

- [subprocess.run及返回对象](https://docs.python.org/3.12/library/subprocess.html#subprocess.run)：等待结束、结果收集、退出码及超时行为。
- [Python的-X utf8选项](https://docs.python.org/3.12/using/cmdline.html#cmdoption-X)：启用UTF-8模式。
- [asyncio异常](https://docs.python.org/3.12/library/asyncio-exceptions.html#asyncio.TimeoutError)：TimeoutError别名关系。

## 6. 首版回读与调用关系说明

学员曾对subprocess.run示例表示不理解，随后提交首版实现。此次回读只读源码，不运行脚本或模型请求。

示例的调用关系是：当前Agent程序调用subprocess.run；它再启动命令列表第一项指定的程序。sys.executable指向当前Python解释器，-c告诉该解释器执行后一项的Python代码文字。子进程里的print写入自己的stdout；capture_output=True将其收集到返回对象，而非直接作为当前函数的返回文字。

run返回一个CompletedProcess对象，它的returncode、stdout、stderr是三个属性。应先用一个变量接住对象，再按属性取值；它不是可以直接赋给三个变量的元组。text=True使收集的输出为字符串。工具函数最后仍要自行把三项整理为有标签的一个字符串，符合已有工具结果约定。

首版具体问题：

1. tools第110行使用returncode, stdout, stderr = subprocess.run(...)，会因结果对象不能这样解包而TypeError；第120行返回元组也不符合工具的str约定。先保存结果对象，再通过其属性组织返回文字。
2. tools第111行-X后写成utf-8，正确选项值是utf8。encoding="utf-8"是输出解码参数，这两个位置的拼写不同。
3. tool_schemas第59行name为run_python_file_tool，第70行参数表键为run_python_tool，而函数表和调度使用run_python。三个用于查找的名称应统一为run_python。保存工具说明的Python变量run_python_tool可以保留，不必把变量名也当成协议名称。
4. 函数尚未转换subprocess.TimeoutExpired，超时会落到现有通用错误分支；按第3节捕获并转为内建TimeoutError，才能复用现有timeout状态。

路径解析、工作目录、输出捕获、stdin、5秒子进程超时参数以及顺序调度已接入；当前只修上述实际问题，不加额外校验或测试脚本。

## 7. 第二次回读：最后的返回格式

已确认工具名称统一为run_python，-X后改为utf8，run结果由一个result变量接收，TimeoutExpired已转换为内建TimeoutError。当前裸raise TimeoutError能进入既有超时分支，不以补充异常消息或异常链作为完成门槛。

仅剩tools第123行return result：它交出的是CompletedProcess对象，仍不符合工具返回str的约定。返回类型注解不会自动转换实际值。学员用f-string等方法，将result.returncode、result.stdout、result.stderr三个属性的值整理为带标签的一段字符串后返回即可。教员未代写或运行源码，当前不增加新检查项。

## 8. 实现静态通过

第三次回读确认tools第124行已用f-string返回退出码、标准输出、错误输出三项文字。RunPythonArgs、工具说明中的name、参数表与函数表的run_python一致，tool_specs已加入说明，调度将脚本运行与写入/编辑一样归为整批顺序执行。UTF-8、工作目录、结果捕获和超时转换已接通，当前范围静态通过。

开头换行及标签后的空白不影响本步约定，不为显示格式追加修正门槛。教员未执行脚本、模型请求或测试；此时只记录实现已静态通过。

## 9. 实际使用任务：给审阅报告补充执行证据（已完成）

重新从cli.py启动Agent，使新增工具定义进入这次Python进程。使用工作区已有minimal_loop.py，输入：

```text
请先读取minimal_loop.py，再使用run_python运行它。
根据工具返回的退出码、标准输出和错误输出，说明实际发生了什么。
读取已有review_report.md，将本次运行结果和解释追加到“实际执行记录”一节，区分工具实际返回的内容与根据源码作出的推断。
```

这是使用新工具完成已有审阅任务，复用原脚本和报告，不新增验证脚本或故障场景。执行结果应通过tool消息交回模型，模型再据此解释并写报告。本次已通过会话中的实际调用与返回确认，见下一节。

工具执行通知的success表示包装取得了返回结果。脚本自身的退出码、输出及异常文字是另一层信息，解释时以工具返回的三项结果为依据。

## 10. 实际使用完成

学员提供运行截图后，教员回读本轮session.json与review_report.md，确认先读取脚本及原报告，再调用run_python(minimal_loop.py)，使用edit_file追加报告，最后read_file回读。工具实际返回退出码0、标准输出三行“笔记内容：今天学习Agent Loop”“达到最大轮数”“模型请求失败”，stderr为空。报告第七节已记录相同结果，本项通过。

“模型请求失败”是第三个假模型场景的程序输出，脚本按预设分支结束，退出码仍可为0。输出内容与进程退出状态分别解释，不能把这行文字当成此次真实DeepSeek请求失败。

直接观测是退出码与输出，具体执行了哪个源码分支需要结合源码解释。报告在7.2及7.3部分仍把分支推断标为实际观测，这一用词区别已在教学中指出；当前任务不增加报告再改或额外运行的门槛。内部调用轮数未插日志，仍属于源码推断。

教员只读现有记录并更新讲义，没有代跑脚本、请求模型或代改报告。另回读确认摘要及非流式响应已经通过extract_message检查finish_reason，旧停点中的待讲项不再自动变成新修改任务。下一项为[本机HTTP接口](Agent实战篇_本机HTTP接口.md)。
