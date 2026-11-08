from uuid import uuid4

from tools import resolve_workspace_path
from tool_schemas import DelegateReviewArgs
from agent_events import event_source

async def delegate_review(args: DelegateReviewArgs) -> str:
    from review_workflow import collect_review_findings, validate_review_evidence, render_review_report

    path = resolve_workspace_path(args.path)
    source = path.read_text(encoding="utf-8") #读取源码
    session_id = f"delegate_{uuid4().hex}"
    source_token = event_source.set(session_id) #设置任务来源

    focus_descriptions = {
        "logic": "控制流程、条件判断和返回值中的实际缺陷。",
        "exceptions": "异常处理和资源清理中的实际缺陷。",
    }
    scope = f"{focus_descriptions[args.focus]}\n {args.review_context}"
    try:
        ReviewResult = await collect_review_findings(args.path, scope, session_id) #收集审阅结果
    finally:
        event_source.reset(source_token)

    validate_review_evidence(source, ReviewResult) #检查证据

    report = render_review_report(args.path, scope, ReviewResult) #生成报告

    return report