# 进阶第12节：RAG与多文档问答

> 2026-11-04开始。第11节代码审阅工作流已于11月3日23:57实际跑通零问题分支。本节以现有项目的短资料为例，学习多文档检索与带出处回答；当前只布置资料加载函数，尚未实现或运行RAG应用。Python源码仍由学员亲写。

## 1. 这节要解决什么

检索增强生成（RAG）是先找出问题相关资料，把问题和资料一起交给模型，再根据资料生成回答。关键词、语义或向量等都是可能的检索方式，向量数据库不是定义本身。概念参考[Microsoft Learn](https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation)。当前复用Python、本地资料和已有模型。

现有list_files/search_file/read_file已能支持工具驱动的查资料问答，不否认已有能力，也不把再造同名工具当成学习目标。本节新增内容是由代码统一管理多份资料、选择相关片段、保留出处后组织回答。第一步先读入资料，之后才做真正的相关性检索；加载全部文件不等于已经检索或应该全部塞入模型。

## 2. 当前资料与目标问题

教员已按当前session_store.py、tool_policies.py与文件工具实现准备两份短资料：workspace/knowledge/sessions.md与tools.md；可提交的原始样本保存在docs/rag_demo/。这些是本节的固定学习资料快照，运行实现仍以源代码为准。

后续用问题“会话study保存在哪里？只读模式能否修改文件和运行脚本？”检索两个文件，要求回答有来源文件和行号，资料没写明时说明未找到依据。当前不发模型请求、不安装新库；不把索引/向量库设为先决条件。

## 3. 当前动手：读入多份资料

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

## 4. 后续顺序

保留来源与行号的片段整理→基础关键词检索与选取→把选中资料交给模型→带来源回答并实际运行。再依据漏检、片段过长等具体问题讨论检索策略和分块取舍；不无条件增加语义检索、模型复核或复杂框架。第11节保持完成，不重开局部验收。
