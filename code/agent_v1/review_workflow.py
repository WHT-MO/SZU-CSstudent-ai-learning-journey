from pydantic import BaseModel, Field, ValidationError
import json
import asyncio
from hashlib import sha256

from agent_runner import run_agent
from tool_policies import read_only_guard, READ_ONLY_TOOL_NAMES
from tools import resolve_workspace_path

#代码审阅工作流练习
class ReviewFinding(BaseModel): #代表一条候选问题
    line: int = Field(ge=1)
    description: str
    trigger: str
    impact: str
    evidence: str

class ReviewResult(BaseModel): #代表整份结果
    findings: list[ReviewFinding]

def parse_review_result(content: str) -> ReviewResult: #解析审阅结果
    result = ReviewResult.model_validate_json(content) #解析失败会传递ValidationError
    return result

async def collect_review_findings(path: str, scope: str, session_id: str) -> ReviewResult: #s收集模型审阅结果
    schema = ReviewResult.model_json_schema()
    prompt = f"""
请先读取并审阅 {path}。
审阅前提：{scope}。
最终只返回 JSON，不加开场说明或 Markdown 代码围栏。
没有发现候选缺陷时，findings 使用空列表。
evidence 原样引用源码，line 表示引用片段的起始行号，从1开始。
返回的 JSON 必须符合下面的格式说明：
{json.dumps(schema, ensure_ascii=False)}
"""
    agent_result = await run_agent(
        prompt,
        session_id=session_id,
        before_tool=read_only_guard,
        visible_tool_names=READ_ONLY_TOOL_NAMES,
    )

    if agent_result["completed"] == False:
        raise RuntimeError(f"任务没有完整结束：{agent_result["reason"]}")
    
    findings = parse_review_result(agent_result["message"]["content"])
    return findings

def validate_review_evidence(source: str, result: ReviewResult) -> None: #比较审阅证据
    source_lines = source.splitlines() #源码行列表
    
    for finding in result.findings:
        if finding.line > len(source_lines):
            raise ValueError(f"{finding.line}行号超过文件总行数")
        if finding.evidence.strip() == "":
            raise ValueError(f"{finding.line}无证据")

        evidence_lines = finding.evidence.splitlines()
        actual_lines = source_lines[finding.line - 1:finding.line - 1 + len(evidence_lines)]

        if actual_lines != evidence_lines:
            raise ValueError(f"{finding.line}证据与源码不一致")

def render_review_report(path: str, scope: str, result: ReviewResult) -> str: #审阅报告排版
    if not result.findings:
        findings = "当前审阅范围内未发现候选缺陷"
    else:
        parts = []

        for number, part in enumerate(result.findings, start=1):
            section = f"""
## {number}. 第 {part.line} 行：{part.description}
触发条件：{part.trigger}
影响：{part.impact}
证据：
```python
{part.evidence}
```
"""
            parts.append(section)

        findings = "\n\n".join(parts)

    report = f"""
# Python 代码审阅报告
文件：{path}
审阅前提：{scope}
候选问题：{len(result.findings)}条
{findings}
"""
    return report

def load_review_checkpoint(checkpoint_file, path, scope, source_hash): #读档
    try:
        text = checkpoint_file.read_text(encoding="utf-8")
        checkpoint = json.loads(text)
        if isinstance(checkpoint, dict):
            if checkpoint.get("path") == path and checkpoint.get("scope") == scope and checkpoint.get("source_hash") == source_hash:
                result = ReviewResult.model_validate(checkpoint.get("result"))
                return result
        return None

    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as error:
        return None

async def main():
    try:
        path = "minimal_loop.py"
        scope = "Python 3.12+，只检查当前代码实际可触发的缺陷"
        report_path = "workflow_review_report.md"
        session_id = "review_workflow_01"

        source_file = resolve_workspace_path(path) #转换路径
        report_file = resolve_workspace_path(report_path)

        source = source_file.read_text(encoding="utf-8") #读取源码
        checkpoint_file = resolve_workspace_path("review_checkpoint.json") #检查点路径
        source_hash = sha256(source.encode("utf-8")).hexdigest() #哈希校验

        result = load_review_checkpoint(checkpoint_file, path, scope, source_hash)
        if result is None:
            result = await collect_review_findings(path, scope, session_id) #收集审阅结果

            validate_review_evidence(source, result) #检查证据

            checkpoint = { #存档
                "path": path,
                "scope": scope,
                "source_hash": source_hash,
                "result": result.model_dump(mode="json"),
            }
            checkpoint_text = json.dumps(checkpoint, ensure_ascii=False, indent=2)

            temp_path = checkpoint_file.with_suffix(".tmp") #原子写入
            temp_path.write_text(checkpoint_text,encoding="utf-8") #写入文件
            temp_path.replace(checkpoint_file)

        report = render_review_report(path, scope, result) #生成报告

        report_file.write_text(report, encoding="utf-8") #保存报告
        print(f"审阅报告保存在{report_file}")

        checkpoint_file.unlink(missing_ok=True) #清除检查点

    except ValidationError as error:
        print(f"审阅结果格式错误：{error}")
    except (RuntimeError, ValueError, OSError) as error:
        print(f"审阅失败：{error}")

if __name__ == "__main__":
    asyncio.run(main())