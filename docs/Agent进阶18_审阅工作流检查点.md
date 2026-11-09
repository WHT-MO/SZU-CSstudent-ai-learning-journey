# 进阶第18节 审阅工作流检查点

现有审阅脚本先请求模型收集结果，再校对源码证据，最后生成并保存 Markdown。如果证据校对后报告保存失败，重新执行脚本会再次请求模型。把校对过的结果存到磁盘，就可以在下一次运行中从生成报告这一步接着做。

## 当前动手 保存检查点

沿用 `review_workflow.py` 的单文件流程。在 `main()` 中将检查点路径设为 `resolve_workspace_path("review_checkpoint.json")`。在 `validate_review_evidence(source, result)` 成功后、`render_review_report(...)` 前写入检查点。

记录 `path`、`scope`、`source_hash` 和 `result`。用 `from hashlib import sha256`，再用 `sha256(source.encode("utf-8")).hexdigest()` 计算当前源码的指纹。路径、范围和指纹共同标记这次审阅的输入。用 `result.model_dump(mode="json")` 把 `ReviewResult` 转成可存为 JSON 的字典。

用已有的 `json.dumps` 将检查点字典转成字符串。参考 `session_store.save_session`，先写到同目录的临时文件，再用 `Path.replace()` 替换正式文件。生成报告仍接在保存之后。下一步读回检查点，匹配这次的审阅输入后，再用保存的结果继续生成报告。

2026-11-09 保存段静态通过。检查点字典经 `json.dumps()` 编码后写入临时文件，再替换正式文件。检查点的父目录是已读取源码的工作区根目录，可以直接写文件。

## 当前动手 从检查点续写报告

在 `main()` 前定义普通函数 `load_review_checkpoint(checkpoint_file, path, scope, source_hash)`。用 `read_text(encoding="utf-8")` 和 `json.loads()` 读出保存的数据。先确认读出的是字典，再比较保存的路径、审阅范围和源码指纹。三项一致时，用 `ReviewResult.model_validate(checkpoint.get("result"))` 得到可以交给报告生成函数的结果对象。遇到字段不匹配、文件不存在或格式错误时返回 `None`。

在 `main()` 读完源码后计算一次 `source_hash`，在调用模型前尝试读回检查点。返回 `None` 时才执行原来的收集结果、校对证据和保存检查点。两个分支最后都用 `result` 生成并写入报告。报告写入成功后调用 `checkpoint_file.unlink(missing_ok=True)`，让已完成的任务结束。写报告失败时会在这行之前抛出异常，下一次运行可以继续使用检查点。

2026-11-09 恢复段静态通过。首次运行从缺文件异常得到 `None`。匹配的检查点还原为 `ReviewResult`，可直接生成报告。报告写成功后清理检查点。

用 VS Code 做一次中断恢复演示。在 `report = render_review_report(...)` 打断点并调试运行。停在这一行时，检查点已落盘，报告还未写入。停止调试，把断点移到 `if result is None:`，再启动同一脚本。此时 `result` 应为 `ReviewResult`。继续运行，看到报告保存消息并确认检查点消失。

2026-11-09 第二次调试在 `if result is None:` 暂停时，截图中的 `result` 为 `ReviewResult(findings=[])`，确认重启后读到了已有审阅结果。核对时检查点仍在，报告是此前生成的版本。继续调试后核对报告写入与检查点清理。

2026-11-09 14:50（Asia/Shanghai）恢复演示通过。继续调试后终端显示报告保存成功，磁盘上的报告已更新为零条候选缺陷，检查点已清理。此前断点观察到的 `ReviewResult` 使程序跳过模型调用，直接生成报告。接下来进入[审阅任务评测](Agent进阶19_审阅任务评测.md)。
