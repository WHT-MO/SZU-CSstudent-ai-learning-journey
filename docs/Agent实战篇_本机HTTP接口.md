# 应用阶段：给现有Agent增加本机HTTP入口

> 当前进展：2026-10-22。请求链路及共享锁已静态通过；学员提供/docs的Response body截图，实际收到role为assistant、content含自我介绍的JSON，首次HTTP调用成功。下一项见[HTTP事件流](Agent实战篇_HTTP事件流.md)。
> 对照教材：[实战篇第7章：把Agent封装成服务](https://www.dgzhuya.com/modules/pr07-deploy)。本项目用FastAPI连接已有Python运行时，教材SDK示例用于职责对照。

## 1. 本节目标

通过POST /chat接收JSON中的prompt，交给现有run_agent，等本次任务完成后，将最终消息作为JSON响应返回。当前沿用一份会话文件及既有返回约定：完整最终回答为消息字典，没有取得最终回答时为None，对应JSON的null。

```text
HTTP请求中的prompt → HTTP入口函数 → run_agent → 原有模型/工具循环
                                                   ↓
HTTP响应中的最终消息 ← HTTP入口函数 ← run_agent返回值
```

CLI输入和显示已独立，run_agent已返回结果，所以新入口可以直接复用执行流程。当前HTTP响应在完整任务结束后返回；后续可接入事件流展示正文和工具进度。

## 2. 新工具与函数登记

FastAPI负责把HTTP路径关联到Python函数、读取请求数据、返回JSON。Uvicorn负责运行这个Web应用并接收网络连接。它们是本节新增依赖，在项目根目录使用已有虚拟环境安装：

```powershell
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn
```

下面是与作业分开的基本示例：

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
async def hello():
    return {"message": "hello"}
```

app表示这个Web应用。@app.get("/hello")是装饰器写法：把下面的hello函数登记为GET /hello的处理函数。请求到达时，由框架调用它；返回字典后，框架组织JSON响应。这里的登记可以类比已学的监听器登记，但匹配条件变成HTTP方法和路径。

本次使用@app.post("/chat")，因为调用者要在请求正文中发送prompt。用已学的Pydantic BaseModel定义ChatRequest，字段为prompt: str；将入口函数参数标注为该模型，FastAPI会读取JSON并提供对应对象。函数通过该参数的.prompt取得文字。

装饰器并不替你执行Agent，入口函数仍需await run_agent(...)并返回取得的结果。终端里的print输出不会自动变成HTTP响应。

## 3. 为什么需要一把共享锁

当前load_session/save_session使用固定session.json。Web入口可以同时收到两个请求，如果它们各自加载旧历史、请求模型并保存，就可能互相覆盖。这里的共享文件是已有实现，所以在新增入口将整个run_agent调用排队。

使用asyncio.Lock，在HTTP模块创建一把共享的agent_lock；处理请求时，用async with agent_lock包住run_agent调用。进入时等待锁，退出时释放，第二个请求等前一个完成后再使用这份会话。锁在整个调用期间持有，覆盖加载到保存的过程。

这把锁供同一服务进程中的请求共用，启动命令固定一个worker。当前使用一个入口处理这份会话，不把进程内锁当作多进程文件锁。

## 4. 当前动手

在code/agent_v1新建http_api.py，由学员完成：

1. 导入FastAPI、BaseModel、asyncio和现有run_agent。
2. 创建app对象及共享agent_lock，定义只含prompt字段的ChatRequest。
3. 用POST /chat登记一个异步入口函数，参数标注为ChatRequest。
4. 在共享锁内等待run_agent处理参数中的prompt，向调用者返回其最终结果。

本节直接复用原有消息结构和会话文件。CLI中的监听器由CLI登记；HTTP入口以函数返回值提供最终消息。当前产出为这个可调用入口，不额外要求前端、流式队列、鉴权或会话树。

## 5. 整理完成后怎样使用

在原CLI输入/exit退出，再在项目根目录启动本机服务：

```powershell
.\.venv\Scripts\python.exe -m uvicorn http_api:app --app-dir code\agent_v1 --host 127.0.0.1 --port 8000 --workers 1
```

http_api:app表示导入http_api模块、取得其中的app对象；--app-dir指定模块所在目录。127.0.0.1是本机地址，8000是端口，workers 1对应上面的共享锁范围。

运行后可打开http://127.0.0.1:8000/docs，在POST /chat中提交：

```json
{"prompt": "你好，用一句话介绍你自己"}
```

这是实际使用入口的方法；请求链路与共享锁均已写出并静态通过。教员未安装依赖、启动服务、发送模型请求或新建测试，当前由学员实际使用。

## 6. 本次核对的官方资料

- [FastAPI基础与路径登记](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [Pydantic请求正文](https://fastapi.tiangolo.com/tutorial/body/)
- [Uvicorn启动参数](https://uvicorn.dev/settings/)
- [asyncio.Lock](https://docs.python.org/3.12/library/asyncio-sync.html#asyncio.Lock)

## 7. 请求数据到函数参数：回读通过

学员曾对ChatRequest的作用表示不理解。已补讲：类声明定义字段格式；FastAPI读取请求JSON后，按类型声明创建包含本次内容的数据对象，并把它作为入口函数的参数传入。通过data.prompt读取实际文字，而不是从ChatRequest类上读取当前输入。

回读http_api第10至14行确认：入口签名为chat(data: ChatRequest)，先取得data.prompt，再await run_agent(prompt)，最后return answer。数据输入、调用及返回这条链已静态通过，不据有提示实现直接记录独立掌握。

## 8. 共享锁任务（已静态通过）

在http_api.py导入asyncio，在模块中创建一次共享的agent_lock = asyncio.Lock()。将完整的await run_agent调用放入async with agent_lock的缩进块，再返回取得的结果。

async with进入时等待并取得锁，退出时释放；期间其他需要同一把锁的请求等待。锁供这些请求共同使用，因此在模块中创建，不能每次进入chat都创建一把新锁。

这里保护的是现有session.json完整的加载、处理和保存过程：若A、B同时加载同一份旧历史，分别添加自己的任务，最后保存的人可能覆盖另一人的记录。整个run_agent持锁，能让后来的请求在前一个保存结束后再加载历史。当前不改现有会话结构，也不新增验证脚本；下一次先回读锁的创建位置与调用范围。

## 9. 启动并实际调用（已完成）

回读确认agent_lock在模块创建一次，chat内的async with覆盖await run_agent，结果在锁内返回。return也会正常退出上下文并释放锁。函数末尾另外一条锁外return answer不可达，学员顺手删去即可，不作为继续启动的阻塞。

实际使用按第5节命令，在项目根目录启动单worker本机服务。看到Uvicorn running提示后，保持该终端运行，用浏览器打开http://127.0.0.1:8000/docs。展开POST /chat，点击Try it out，填写第5节JSON，点击Execute，再阅读Response body中的role、content等字段。

该接口会等待整个run_agent结束，随后一次返回最终JSON；当前Swagger页面不实时显示模型正文片段。若没有取得最终消息，原有None约定对应JSON null，须结合服务日志排查，不能把服务器已启动记成Agent已完成任务。

学员截图已展示实际Response body：role为assistant，content为“你好！我是这个工作区里的代码审阅助手，可以读取代码、运行 Python 脚本，并按技能流程出具审阅报告。”据此记录HTTP输入、Agent调用、最终消息返回这条链的运行成功。截图不单独证明并发锁、工具执行或HTTP逐段输出；这些无需为本次完成额外补测。教员未代启服务或发请求。

## 10. 下一步：HTTP事件流

沿教材实战篇第7章继续，把已有text_delta、tool_start、tool_end等事件经HTTP逐段发送。先学习异步队列、yield和StreamingResponse之间的关系，由学员在http_api.py实现stream_events(queue)：读取事件、转为SSE字符串并逐条交出，遇到None结束。下一次再将监听器和Agent任务接入同一请求的队列。讲义与当前任务见[HTTP事件流](Agent实战篇_HTTP事件流.md)，当前不修改已有/chat行为，不新增测试脚本。
