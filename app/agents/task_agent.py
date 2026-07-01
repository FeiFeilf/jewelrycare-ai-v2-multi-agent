from typing import Any, Dict, List
from app.tools.task_tool import create_task


def run_task_agent(result: Dict[str, Any]) -> Dict[str, Any]:
    tasks: List[Dict[str, Any]] = []
    ticket = result.get("ticket") or {}
    handoff_record = result.get("handoff_record") or {}
    recovery_log = result.get("recovery_log") or {}

    if ticket.get("created"):
        risk_level = ticket.get("risk_level")
        tasks.append(create_task(
            task_type="after_sales_evidence_followup",
            related_type="ticket",
            related_id=str(ticket.get("ticket_id")),
            title="等待用户补充售后证据",
            description=ticket.get("evidence_required", "请用户补充售后证据。"),
            owner="after_sales_team",
            status="open",
        ))
        if risk_level == "high":
            tasks.append(create_task(
                task_type="high_risk_after_sales_review",
                related_type="ticket",
                related_id=str(ticket.get("ticket_id")),
                title="人工审核高风险售后工单",
                description="高风险售后问题需要人工客服优先审核。",
                owner="human_after_sales_queue",
                status="open",
            ))

    if handoff_record.get("created"):
        tasks.append(create_task(
            task_type="human_handoff_followup",
            related_type="handoff",
            related_id=str(handoff_record.get("handoff_id")),
            title="人工客服处理用户高风险请求",
            description=f"人工兜底原因：{handoff_record.get('reason')}",
            owner="human_support_team",
            status="open",
        ))

    if recovery_log and recovery_log.get("created"):
        tasks.append(create_task(
            task_type="cart_recovery_conversion_followup",
            related_type="recovery_log",
            related_id=str(recovery_log.get("log_id")),
            title="跟进弃单优惠转化状态",
            description="检查用户是否使用优惠码完成下单。",
            owner="growth_ops_team",
            status="open",
        ))

    return {
        "agent": "task_agent",
        "success": True,
        "tasks_created": tasks,
        "task_count": len(tasks),
    }
