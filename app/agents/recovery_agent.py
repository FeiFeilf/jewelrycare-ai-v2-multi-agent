from typing import Any, Dict, Optional
from app.tools.recovery_tool import query_cart, build_cart_recovery, create_recovery_log


def run_recovery_agent(cart_id: Optional[str]) -> Dict[str, Any]:
    if not cart_id:
        return {
            "agent": "recovery_agent",
            "success": False,
            "cart_recovery": None,
            "recovery_log": None,
            "need_handoff": False,
            "next_action": "ask_user_to_provide_cart_id",
        }

    cart = query_cart(cart_id)
    if not cart.get("found"):
        return {
            "agent": "recovery_agent",
            "success": False,
            "cart": cart,
            "cart_recovery": {"found": False, "message": "Cart not found."},
            "recovery_log": None,
            "need_handoff": True,
            "next_action": "cart_not_found_need_handoff",
        }

    recovery = build_cart_recovery(cart)
    log = create_recovery_log(recovery)
    return {
        "agent": "recovery_agent",
        "success": True,
        "cart": cart,
        "cart_recovery": recovery,
        "recovery_log": log,
        "need_handoff": False,
        "next_action": "abandoned_cart_recovery_logged",
    }
