# 应用整理：依赖与运行说明

> 当前进展：2026-10-23。本节整理完成：requirement.txt、.env.example及固定规则/技能的Git忽略例外均已静态通过，README安装与首次配置步骤已统一。后续见[HTTP客户端连续输入](Agent实战篇_HTTP客户端.md#9-连续输入任务)。

## 1. 这次解决什么问题

本机已经安装过HTTPX、Pydantic等库，因此可以运行；依赖清单用于告诉pip需要安装哪些包，之后可以用一条命令安装。通常将文件命名为requirements.txt，本项目学员实际保存为requirement.txt；文件名可以自定，安装命令中的路径与它一致即可。

它是文本文件，每行写一个包名，也可以带版本要求。它不保存Python解释器、虚拟环境、API密钥或会话数据。Python 3.12+的要求仍写在README里。

## 2. 根据现有程序确定清单

已静态核对code/agent_v1的导入与README中的服务启动命令：

| 安装包名 | 当前用途 |
| --- | --- |
| httpx | 模型请求和本机HTTP客户端 |
| pydantic | 工具参数及HTTP请求参数模型 |
| python-dotenv | 通过dotenv.load_dotenv读取.env |
| fastapi | 声明HTTP接口 |
| uvicorn | 运行HTTP服务 |

安装名与导入名可以不同，例如代码写from dotenv import load_dotenv，安装包名是python-dotenv。uvicorn虽然由命令启动而非源码import，运行服务仍需要它。

asyncio、json、pathlib、os、sys、subprocess是Python标准库，不需通过pip安装；agent_runner、tools等是项目自身模块。第三方库自身所需的依赖由pip按包的声明一起处理，本次清单列项目直接使用的五项。

## 3. 依赖清单（已完成）

学员已在仓库根目录创建D:/code/dsh/python-course/requirement.txt，上表五个安装包名各占一行。Pydantic沿用README现有要求，写成pydantic>=2,<3，表示至少2版且低于3版；当前源码使用model_json_schema等2版接口。清单内容已静态通过，无需为了文件名补s而重做。

这份文件供下列命令读取：

```powershell
& "D:\code\dsh\python-course\.venv\Scripts\python.exe" -m pip install -r "D:\code\dsh\python-course\requirement.txt"
```

-r后面是清单文件路径。README已经改为读取实际的requirement.txt，HTTP服务部分不再要求单独安装已在清单中的FastAPI与Uvicorn。教员只静态核对及改文档，未重装或新建环境。本次没有锁定全部依赖的具体版本，不将这份清单称为完整环境快照。

## 4. 环境配置示例（已完成）

依赖清单说明要安装哪些库；环境配置说明程序运行时从哪里取得具体值。当前代码通过load_dotenv读取.env，再从DEEPSEEK_API_KEY取得模型密钥。

在根目录新建D:/code/dsh/python-course/.env.example，写入一行：

```dotenv
DEEPSEEK_API_KEY=your_api_key_here
```

.env.example是可以随仓库分享的模板；使用者复制为.env后填写自己的值。load_dotenv当前读取的是.env，模板本身不会替代它。现有.gitignore已排除.env和.env.*，并通过!.env.example单独允许模板，无需修改忽略规则。

最新回读已确认模板只有这一行占位配置，静态通过。README已改为新环境首次配置时执行Copy-Item .env.example .env，再编辑.env填写。教员仅检查模板并修改文档，未复制或覆盖本机.env，未运行程序或请求模型。

## 5. 随仓库保存固定规则和技能（已完成）

agent_runner的SKILLS_PROMPT引用skills/review_python/SKILL.md，build_system_prompt读取workspace/AGENTS.md。整理时发现两份文件在本机存在，原.gitignore的code/agent_v1/workspace/*却将它们排除；当时git ls-files也没有列出它们，克隆仓库会缺少这些文件。

本次将已有的工作区规则与review_python技能正文列为可提交的项目文件。两份正文已经回读：AGENTS.md是“修改已有文件前先读取相关内容”，技能是先确认版本和用途、说明可触发路径并区分问题类别的三项流程。

在D:/code/dsh/python-course/.gitignore的工作区规则段末尾，追加以下规则：

```gitignore
!code/agent_v1/workspace/AGENTS.md
!code/agent_v1/workspace/skills/
code/agent_v1/workspace/skills/*
!code/agent_v1/workspace/skills/review_python/
code/agent_v1/workspace/skills/review_python/*
!code/agent_v1/workspace/skills/review_python/SKILL.md
```

普通规则表示忽略，开头的!表示允许此前忽略的路径。先允许skills目录，接着忽略里面的条目，再允许review_python目录；最后在该目录中允许SKILL.md。父目录被忽略时，单独允许里面的文件不会生效，所以需要逐层允许目录。

最新回读：六行规则已正确加入，git status --untracked-files=all已显示AGENTS.md与review_python/SKILL.md两个文件；忽略规则查询也确认它们命中允许例外，报告及技能目录中其他文件仍命中忽略规则。本次Git保存范围调整完成，文件可在后续提交时收录，目前未提交或上传。

## 6. 本节结果与下一步

安装清单、配置模板、项目规则及技能保存范围已整理完成。已有文件夹会随规则和技能文件一并检出，无需另写工作区初始化功能。下一项回到客户端的实际使用：将原先一次输入改为持续接收任务，输入/exit结束，见HTTP客户端第9节。教员只审阅并更新文档，未运行程序、重装环境或发送模型请求。

## 7. 依据

- [pip官方：requirements文件格式](https://pip.pypa.io/en/stable/reference/requirements-file-format/)
- [Git官方：gitignore规则与父目录例外](https://git-scm.com/docs/gitignore#_pattern_format)
- 本项目agent_runner.py、tool_schemas.py、http_api.py、http_client.py的实际导入及README服务启动命令。
