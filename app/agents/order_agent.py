from typing import Any, Dict, Optional
from app.tools.order_tool import query_order


def run_order_agent(order_id: Optional[str]) -> Dict[str, Any]:
    if not order_id:
        return {
            "agent": "order_agent",
            "success": False,
            "order": None,
            "message": "No order_id provided.",
            "next_action": "ask_user_to_provide_order_id",
        }

    order = query_order(order_id)
    return {
        "agent": "order_agent",
        "success": bool(order.get("found")),
        "order": order,
        "next_action": "order_found" if order.get("found") else "ask_user_to_confirm_order_or_handoff",
    }
