from typing import Any, Dict, Optional
from app.tools.ticket_tool import create_ticket


def assess_damage_level(message: str, vision_summary: str = "", has_image: bool = False) -> Dict[str, Any]:
    text = f"{message or ''} {vision_summary or ''}".lower()

    high_words = [
        "broken", "crack", "cracked", "stone missing", "missing stone",
        "serious damage", "severe damage", "断裂", "裂开", "破裂", "掉钻",
        "严重损坏", "严重破损", "断了",
    ]
    medium_words = [
        "scratch", "scratched", "damaged", "defect", "color fading",
        "fading", "oxidized", "color difference", "划痕", "刮痕", "损坏",
        "瑕疵", "褪色", "氧化", "色差", "发黑", "掉色",
    ]

    if any(w in text for w in high_words):
        return {
            "risk_level": "high",
            "defect_type": "severe_damage_or_missing_stone",
            "suggested_action": "create_ticket_and_escalate_to_human",
            "has_image": has_image,
            "vision_summary": vision_summary,
        }

    if any(w in text for w in medium_words):
        return {
            "risk_level": "medium",
            "defect_type": "surface_scratch_or_color_issue",
            "suggested_action": "create_ticket_and_request_evidence",
            "has_image": has_image,
            "vision_summary": vision_summary,
        }

    return {
        "risk_level": "low",
        "defect_type": "unclear_or_low_risk_issue",
        "suggested_action": "ask_customer_for_more_information",
        "has_image": has_image,
        "vision_summary": vision_summary,
    }


def run_after_sales_agent(
    message: str,
    order_id: Optional[str],
    order_found: bool,
    has_image: bool = False,
    vision_summary: str = "",
) -> Dict[str, Any]:
    assessment = assess_damage_level(message, vision_summary, has_image)

    if not order_id:
        return {
            "agent": "after_sales_agent",
            "success": False,
            "image_assessment": assessment,
            "ticket": None,
            "need_handoff": False,
            "next_action": "ask_user_to_provide_order_id_and_damage_evidence",
        }

    if not order_found:
        return {
            "agent": "after_sales_agent",
            "success": False,
            "image_assessment": assessment,
            "ticket": None,
            "need_handoff": True,
            "next_action": "order_not_found_need_handoff",
        }

    ticket = create_ticket(
        order_id=order_id,
        issue_type="after_sales_triage",
        description=f"{message} | has_image={has_image} | vision_summary={vision_summary}",
        risk_level=assessment["risk_level"],
        has_image=has_image,
    )
    return {
        "agent": "after_sales_agent",
        "success": True,
        "image_assessment": assessment,
        "ticket": ticket,
        "need_handoff": assessment["risk_level"] == "high",
        "next_action": (
            "after_sales_ticket_created_and_handoff"
            if assessment["risk_level"] == "high"
            else "after_sales_ticket_created"
        ),
    }
