from typing import Any, Dict

from app.tools.memory_tool import (
    get_or_create_customer_profile,
    update_customer_profile,
    create_memory_item,
    list_memory_items,
    extract_memory_candidates,
)


def _detect_language(message: str) -> str:
    if any('\u4e00' <= ch <= '\u9fff' for ch in message or ""):
        return "zh"
    return "en"


def run_memory_agent(result: Dict[str, Any]) -> Dict[str, Any]:
    session_id = result.get("session_id") or "default-session"
    message = result.get("original_message") or ""
    order_id = result.get("order_id")
    risk_level = ((result.get("image_assessment") or {}).get("risk_level")
                  or ((result.get("vision_agent") or {}).get("vision_assessment") or {}).get("severity"))

    profile = get_or_create_customer_profile(
        session_id=session_id,
        preferred_language=_detect_language(message)
    )

    risk_tag = None
    if result.get("handoff") or risk_level == "high":
        risk_tag = "high_risk_after_sales_or_handoff"

    updated_profile = update_customer_profile(
        customer_id=profile["customer_id"],
        last_order_id=order_id,
        risk_tag=risk_tag,
        preferred_language=_detect_language(message)
    )

    candidates = extract_memory_candidates(message, result)

    created = []
    for item in candidates:
        created.append(create_memory_item(
            session_id=session_id,
            customer_id=profile["customer_id"],
            memory_type=item["memory_type"],
            content=item["content"],
            source="multi_agent_runtime",
            importance=item.get("importance", 3)
        ))

    recent = list_memory_items(
        session_id=session_id,
        customer_id=profile["customer_id"],
        limit=10
    )

    return {
        "agent": "memory_agent",
        "success": True,
        "customer_profile": updated_profile or profile,
        "memory_items_created": created,
        "memory_created_count": len(created),
        "recent_memories": recent
    }
