# 第7章应用练习：模型输出也通过事件显示

> 结果：2026-10-22。正文与收尾事件字典、监听器事件名已修正，模型输出接入已有emit的实现通过源码静态审阅。下一项为终端入口与事件登记的职责拆分。
> 位置：模型响应解析 → 输出事件 → 显示监听器。复用已有工具事件机制。

## 1. 三种信息各自的用途

| 信息 | 谁使用 | 当前作用 |
| --- | --- | --- |
| text_delta事件 | 显示监听器 | 收到一点正文就显示一点 |
| stream_message返回的(message, completed) | run_agent | 判断回复是否完整，决定调工具或结束 |
| run_agent返回的最终消息或None | 外部调用者 | 取得本次任务的最终回答 |

流式片段用于边接收边显示；content_parts仍累积完整正文，用于最终消息和历史。发送事件不会自动生成完整回答，也不代替函数返回值。

当前stream_message第360行直接print正文，第390至394行直接换行并打印usage。接入事件后，解析函数提供数据，监听器决定终端怎样显示。已有工具通知也使用相同emit，不新增另一套分发系统。

## 2. 本次事件约定

收到非空正文片段时：

```python
{"type": "text_delta", "text": content}
```

本次读流循环结束、进入原先换行与显示用量的位置时：

```python
{"type": "model_response_end", "usage": usage}
```

usage沿用当前字典或None；有字典时含prompt_tokens、completion_tokens、total_tokens。model_response_end只表示到达这处接收收尾位置，不表示回复一定完整。原有stream_completed、finish_reason检查和completed返回值继续决定完整性；异常分支不保证发出此事件，因此不把它用作所有退出路径的清理通知。

## 3. 当前动手

1. 将code/agent_v1/tool_events.py重命名为agent_events.py，并更新runner中导入emit的模块名。模块现在同时处理工具与模型事件，新名称匹配其用途。
2. 在该模块增加异步show_model_event(event)，加入现有listeners列表。收到text_delta时按原方式print片段，使用end=""、flush=True；收到model_response_end时先换行，usage有值再打印输入、输出、合计三个字段。
3. 修改stream_message：正文分支保留content_parts.append(content)，通过await emit发送text_delta；读流结束后，通过await emit发送model_response_end，替换原来的换行及usage打印。

正文累积、工具调用拼接、历史保存和函数返回分别承担原有职责。本次迁移的范围是正文和usage显示；解析错误、网络错误等现有提示仍由原分支处理，不据此声称全部终端输出已分离。

本步由学员亲写，教员检查事件字段、监听器登记及触发位置。局部正确即可继续，不另建测试脚本或运行付费请求作为完成门槛。

## 4. 首版回读：调用参数由发送处提供

2026-10-22回读确认agent_events.py已存在，runner已从新模块导入emit，show_model_event也已加入listeners。正文及usage显示已移到监听器，但仍有以下三处需修正：

- runner第360行与第390行均为await emit(event)，当前stream_message中没有定义event，执行到此会触发NameError。emit定义中的event只是接收参数的局部名称，不会替调用者创建字典。发送处应按第2节分别构造正文事件（type、text）和收尾事件（type、usage），再传给emit；也可直接把字典作为参数。
- agent_events第25行写成model_reponse_end，缺少response中的s，应与约定model_response_end一致，否则不能匹配正确的收尾事件。

这属于当前接线问题，不引入新字段、校验器或运行脚本。教员未代改或执行学生源码，当前动作由学员修正上述位置后继续。

## 5. 修正通过，转入终端入口拆分

2026-10-22再次回读确认runner第360至362行构造text_delta/text字典并发送、保留正文累积；第391至392行构造model_response_end/usage字典并发送，位置在完整性判断之前。监听器匹配名称已统一，已登记两个显示函数，当前范围静态通过。未运行测试或真实请求。

目前agent_events仍默认登记终端显示函数，runner仍包含input循环。下一项为[终端入口与事件登记](Agent第02章_终端入口与事件登记.md)：将输入、显示及登记放进cli.py，事件模块保留分发，runner保留执行流程。
