from review_workflow import collect_review_findings, validate_review_evidence
from tools import resolve_workspace_path
from uuid import uuid4
import asyncio

async def main():
    cases = [("review_eval_a.py", 1), ("review_eval_b.py", 0)]
    scope = "只检查返回值是否符合函数文档，参数已保证 0 <= attempts_used <= max_attempts、`max_attempts >= 1`"
    for path, expected_count in cases:
        result = await collect_review_findings(path, scope, f"review_eval_{uuid4().hex}")

        source = resolve_workspace_path(path).read_text(encoding="utf-8")

        validate_review_evidence(source, result)

        actual_count = len(result.findings)
        status = "通过" if actual_count == expected_count else "未通过"
        print(f"{path} | 预期 {expected_count} | 实际 {actual_count} | {status}")

        for finding in result.findings:
            print(f"第 {finding.line} 行 {finding.description}")

if __name__ == "__main__":
    asyncio.run(main())