import asyncio

from review_workflow import (
    ReviewResult,
    collect_review_findings,
    render_review_report,
    validate_review_evidence,
    resolve_workspace_path,
)

#并行子任务与独立上下文

REVIEW_SCOPES = {
    "logic": "Python 3.12+，只检查控制流程、条件判断和返回值中的实际缺陷",
    "exceptions": "Python 3.12+，只检查异常处理和资源清理中的实际缺陷",
}

async def collect_parallel_reviews(path: str, review_context) -> dict[str, ReviewResult]:
    logic_scope = f"{review_context}\n{REVIEW_SCOPES["logic"]}"
    exceptions_scope = f"{review_context}\n{REVIEW_SCOPES["exceptions"]}"

    async with asyncio.TaskGroup() as group:
        logic_task = group.create_task( #逻辑任务
            collect_review_findings(path, logic_scope, "parallel_review_logic_v2")
        )
        exceptions_task = group.create_task( #异常任务
            collect_review_findings(path, exceptions_scope, "parallel_review_exceptions_v2")
        )

    result = {
        "logic": logic_task.result(),
        "exceptions": exceptions_task.result(),
    }
    return result

async def main():
    try:
        path = "minimal_loop.py"
        review_context = "这是最小 Agent Loop 教学脚本，仅按 main 中三个固定模型演示正常回答、工具上限和模型失败。不接真实 SDK，不保存或重放 messages，main 不使用 run_loop 的返回值。只检查这些现有路径中的确定缺陷。"

        source = resolve_workspace_path(path).read_text(encoding="utf-8")
        results = await collect_parallel_reviews(path, review_context)
        report_parts = []

        for role, review_result in results.items():
            validate_review_evidence(source, review_result)
            report_parts.append(
                render_review_report(
                    path,
                    f"{review_context}\n{REVIEW_SCOPES[role]}",
                    review_result,
                )
            )

        report = "\n\n".join(report_parts)
        report_path = resolve_workspace_path("parallel_review_report.md")
        report_path.write_text(report, encoding="utf-8")
        print(f"报告已保存：{report_path}")

    except ExceptionGroup as group_error:
        for error in group_error.exceptions:
            print(f"子任务失败：{type(error).__name__}：{error}")

    except (ValueError, OSError) as error:
        print(f"父任务失败：{error}")

if __name__ == "__main__":
    asyncio.run(main())