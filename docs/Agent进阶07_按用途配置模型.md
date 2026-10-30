# 进阶第7节：按用途配置模型

> 2026-10-30。本节整体静态通过：两个用途配置、三个请求体及主任务输入预算已接齐，模型名与旧常量引用已修正。教员未运行源码或模型请求，不追加测试门槛。

## 1. 目标与当前问题

本节结束后，主任务和历史摘要各自从一份配置读取模型名、输出上限及推理强度；输入预算采用主任务的输出上限。

当前model_client.py中，non_stream_message、stream_message、summarize_messages三个请求都直接写着deepseek-flash，max_tokens共同引用MAX_OUTPUT_TOKENS=20000。agent_runner.py又导入这个常量计算输入预算。未来若想只调整摘要的输出额度，需要能明确区分两个用途。

配置就是程序使用的一组设置。按用途分开配置，解决“这类请求选哪个模型、给多少输出额度、采用什么推理强度”；异步并发解决“多个请求如何调度”。两个用途可以使用同一个模型。

## 2. 前置与数据去向

本次使用已经学过的BaseModel、创建实例、导入变量和读取对象属性，不引入新的配置框架。

ModelConfig供Python代码读取。它不是工具参数说明，不需要调用model_json_schema()；发给模型接口的是请求体中的model、max_tokens、reasoning_effort字段，值来自配置对象的属性。

例如“主任务配置”和“摘要配置”是两种用途名称；deepseek-flash是模型名称。两种用途可以选中相同模型，输出上限也能各自调整。

## 3. 当前动手：配置与三处接线

### 3.1 新建model_config.py

在code/agent_v1下新建model_config.py，用pydantic的BaseModel定义ModelConfig，包含三个字段：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| model | str | 发给模型接口的模型名称 |
| max_output_tokens | int | 本次请求允许生成的输出上限 |
| reasoning_effort | str，默认high | 当前接口的推理强度，取值按下节说明 |

建立两个配置实例，模型名及输出上限沿用当前代码；主任务采用high，摘要采用low作为本项目的初始用途策略：

| 实例名称 | model | max_output_tokens | reasoning_effort |
| --- | --- | --- | --- |
| AGENT_MODEL_CONFIG | deepseek-flash | 20000 | high |
| SUMMARY_MODEL_CONFIG | deepseek-flash | 20000 | low |

这些数值来自当前项目配置，不用它们声明供应商的官方容量。后面可以分别调整用途设置。本节不引入运行中修改配置或按请求选择模型，配置实例在模块加载时建立。

### 推理强度是否必须配置

2026-10-30核对DeepSeek的Chat Completions接口：不提供thinking及reasoning_effort时，默认开启推理，强度为high。reasoning_effort不是必填字段，省略表示采用服务端默认，不表示关闭推理。当前接口接受none、low、high、max；none关闭推理，其余三个值启用相应强度。当显式thinking对象存在时，其type优先决定是否开启。当前项目没有传thinking，本节统一使用reasoning_effort控制，避免重复开关来源。

主任务high、摘要low是本项目根据代码审阅与摘要用途选择的初始策略，不是官方规定，也不保证特定质量或耗时。max_output_tokens控制生成上限，reasoning_effort控制推理投入，两者不能互相代替。配置应纳入当前确实要控制的参数；其他模型的字段、取值及默认值需按其接口核实。

参考：[DeepSeek Chat Completions参数](https://api-docs.deepseek.com/api/create-chat-completion/)、[推理模式说明](https://api-docs.deepseek.com/guides/thinking_mode/)。

### 3.2 model_client.py按用途取值

从model_config导入两个配置实例。non_stream_message和stream_message的请求体使用AGENT_MODEL_CONFIG的model、max_output_tokens与reasoning_effort属性；summarize_messages使用SUMMARY_MODEL_CONFIG的对应属性。

请求体中的model、max_tokens分别取配置的model、max_output_tokens；新增顶层reasoning_effort，值取配置的同名属性。当前用HTTPX发送原始JSON，直接把该键加入request_body。完成替换后删除model_client.py中的旧MAX_OUTPUT_TOKENS定义。

API地址和密钥读取沿现有DeepSeek路径，本节集中模型名、输出上限与推理强度。调用函数的参数及返回结构沿用既有接口。

### 3.3 agent_runner.py的预算来源

runner从model_config直接导入AGENT_MODEL_CONFIG，从model_client导入stream_message、summarize_messages，移除旧MAX_OUTPUT_TOKENS导入。

INPUT_TOKEN_BUDGET按现有公式计算，但输出预留读取AGENT_MODEL_CONFIG.max_output_tokens。当前CONTEXT_BUDGET=200000、TOKEN_MARGIN=10000沿用现有配置。

原因是主任务请求使用哪份输出上限，主任务的输入预算就应扣除同一份值。摘要输出上限属于摘要请求，不能替代主任务的输出预留。

## 4. 依赖与完成条件

model_client和agent_runner都读取model_config；配置模块只定义配置，不依赖两个调用模块。URL、鉴权、流式解析与重试仍归现有模型模块。

静态审阅确认两个实例、三个请求体及runner预算引用一致，且没有旧常量的悬空导入，即完成本段。无需为配置迁移增加测试脚本、启动服务或请求模型。动态选择不同模型、上下文容量跟随选择、不同供应商协议及流式重试是后续议题，不把本段配置称为已完成全部适配。

## 5. 首版回读：两处问题已修正

2026-10-30首版回读：ModelConfig三个字段、两个实例的输出额度与推理强度，以及model_client三个请求体按用途读取属性均正确；旧MAX_OUTPUT_TOKENS定义已经移除。首版曾有两处问题：

1. model_config.py两个实例的model均写成deeoseej-flash，需修正为deepseek-flash。字符串类型正确不等于模型名称有效；供应商会按约定名称查找模型。
2. agent_runner.py仍从model_client导入已删除的MAX_OUTPUT_TOKENS，会在导入时失败。按3.3移除该导入，直接从model_config导入AGENT_MODEL_CONFIG，并让INPUT_TOKEN_BUDGET减去AGENT_MODEL_CONFIG.max_output_tokens。

最新回读确认：两个模型名均已改为deepseek-flash；runner只从model_client导入stream_message、summarize_messages，并从model_config导入AGENT_MODEL_CONFIG，INPUT_TOKEN_BUDGET已减去其max_output_tokens。定向搜索未发现遗留MAX_OUTPUT_TOKENS引用。本节整体静态通过，无剩余必做代码项。

## 6. 下一项

进入[模型请求的重试边界](Agent进阶08_模型请求的重试边界.md)：复用摘要的三次尝试循环，先统一可重试错误分类，再处理流式输出可见后的重试约束。本节未实现动态模型切换、多供应商全适配，不将配置迁移写成这些能力已完成。
