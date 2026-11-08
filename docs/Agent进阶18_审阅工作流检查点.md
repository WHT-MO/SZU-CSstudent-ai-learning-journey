# 进阶第18节 审阅工作流检查点

现有审阅脚本先请求模型收集结果，再校对源码证据，最后生成并保存 Markdown。如果证据校对后报告保存失败，重新执行脚本会再次请求模型。把校对过的结果存到磁盘，就可以在下一次运行中从生成报告这一步接着做。

## 当前动手 保存检查点

沿用 `review_workflow.py` 的单文件流程。在 `main()` 中将检查点路径设为 `resolve_workspace_path("review_checkpoint.json")`。在 `validate_review_evidence(source, result)` 成功后、`render_review_report(...)` 前写入检查点。

记录 `path`、`scope`、`source_hash` 和 `result`。用 `from hashlib import sha256`，再用 `sha256(source.encode("utf-8")).hexdigest()` 计算当前源码的指纹。路径、范围和指纹共同标记这次审阅的输入。用 `result.model_dump(mode="json")` 把 `ReviewResult` 转成可存为 JSON 的字典。

用已有的 `json.dumps` 将检查点字典转成字符串。参考 `session_store.save_session`，先写到同目录的临时文件，再用 `Path.replace()` 替换正式文件。生成报告仍接在保存之后。下一步读回检查点，匹配这次的审阅输入后，再用保存的结果继续生成报告。
