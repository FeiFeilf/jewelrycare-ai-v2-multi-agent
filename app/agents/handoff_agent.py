from typing import Any, Dict, Optional
from app.tools.handoff_tool import create_handoff_record


def infer_handoff_reason(
    intent: str,
    message: str,
    order: Optional[Dict[str, Any]] = None,
    risk_level: Optional[str] = None,
) -> str:
    text = (message or "").lower()
    order = order or {}

    complaint_words = [
        "complaint", "angry", "scam", "fraud", "bad review",
        "投诉", "欺骗", "骗子", "差评", "生气", "举报", "维权",
    ]
    refund_words = [
        "must refund", "refund now", "immediately refund",
        "必须退款", "马上退款", "立刻退款", "不接受", "赔偿",
    ]

    if intent == "human_complaint" or any(w in text for w in complaint_words):
        return "customer_complaint"
    if any(w in text for w in refund_words):
        return "refund_dispute"
    if order and order.get("found") is False:
        return "order_not_found"
    if risk_level == "high":
        return "high_risk_after_sales"
    return "manual_review_required"


def run_handoff_agent(
    session_id: str,
    order_id: Optional[str],
    intent: str,
    message: str,
    order: Optional[Dict[str, Any]] = None,
    risk_level: Optional[str] = None,
) -> Dict[str, Any]:
    reason = infer_handoff_reason(intent, message, order=order, risk_level=risk_level)
    record = create_handoff_record(
        session_id=session_id,
        order_id=order_id,
        reason=reason,
        user_message=message,
    )
    return {
        "agent": "handoff_agent",
        "success": True,
        "handoff": True,
        "handoff_reason": reason,
        "handoff_message": "This case should be escalated to a human customer service agent.",
        "handoff_record": record,
        "next_action": "human_handoff_created",
    }
