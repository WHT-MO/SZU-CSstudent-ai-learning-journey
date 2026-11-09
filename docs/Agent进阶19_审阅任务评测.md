# 进阶第19节 审阅任务评测

检查点练习验证了已有审阅结果能用来生成报告。要检验审阅能否发现真实缺陷，需要一份答案已知的源码。再准备一份只修复该缺陷的对照源码，就能分别观察漏报和误报。

## 当前动手 准备一对已知答案的样例

在工作区创建 `review_eval_bug.py`，让函数根据已用次数和上限决定能否重试。

```python
def can_retry(attempts_used: int, max_attempts: int) -> bool:
    """低于上限时返回 True，达到上限时返回 False。"""
    return attempts_used <= max_attempts
```

复制为 `review_eval_fixed.py`，将返回表达式中的 `<=` 改为 `<`。两份样例共用同一审阅范围。参数满足 `max_attempts >= 1` 和 `0 <= attempts_used <= max_attempts`，只检查返回值是否符合函数文档。

| 样例 | 输入 `can_retry(3, 3)` 时的返回值 | 审阅预期 |
| --- | --- | --- |
| 缺陷版 | `True` | 指出达到上限时仍允许重试，并引用返回语句 |
| 修复版 | `False` | 在限定范围内返回空 `findings` |

下一步用现有 `collect_review_findings()` 分别审阅两份样例，根据预期检查结果。

2026-11-09 回读确认两份样例代码正确，目前放在 `agent_v1` 目录。将它们移到该目录下的 `workspace`，让只读工具可以按文件名找到。缺陷版改名 `review_eval_a.py`，修复版改名 `review_eval_b.py`。审阅提示会带上文件名，使用中性名称可以把预期结果留在评测脚本中。

## 当前动手 跑两份样例并对照结果

在 `agent_v1` 创建 `eval_review.py`。在异步 `main()` 中遍历两项数据，`("review_eval_a.py", 1)` 和 `("review_eval_b.py", 0)`。每项的两个字段分别是文件名和预期发现数。两份文件使用上面的同一审阅范围。

每项用 `await collect_review_findings(path, scope, f"review_eval_{uuid4().hex}")` 获得 `ReviewResult`。用 `from uuid import uuid4` 给每次审阅生成新会话，避免上次评测记录进入这次输入。用 `resolve_workspace_path(path).read_text(encoding="utf-8")` 读源码，再调用 `validate_review_evidence(source, result)` 核对引用。

比较 `len(result.findings)` 与预期发现数，打印文件名、预期、实际和是否通过。缺陷版还打印发现的 `description`，供核对它是否说清了达到上限时仍允许重试。入口用 `asyncio.run(main())`。

## 实跑结果

2026-11-09 学员运行 `eval_review.py`。`review_eval_a.py` 预期和实际均为 1 条，第 3 行的说明指出 `<=` 会在达到上限时允许重试。`review_eval_b.py` 预期和实际均为 0 条。两项都完成了源码引用校验和发现数比较。终端输出同时提供了人工核对缺陷描述的依据。

这对样例固定了预期答案，保留 Agent 自己读取源码的流程。缺陷版检查漏报，修复版检查误报。已确认缺陷的历史代码和对应修复版也可以作为同类样例，用来比较修改审阅规则或模型后的结果。
