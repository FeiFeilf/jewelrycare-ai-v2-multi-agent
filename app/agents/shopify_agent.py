from typing import Any, Dict, Optional

from app.tools.shopify_mock_tool import (
    get_shopify_order,
    get_shopify_cart,
    create_discount_code,
    create_refund_review,
)


def choose_discount_strategy(cart: Dict[str, Any]) -> Dict[str, str]:
    last_active = int(cart.get("last_active_minutes") or 0)

    if last_active <= 60:
        return {
            "strategy": "free_shipping",
            "discount_type": "shipping",
            "value": "FREE_SHIPPING"
        }

    return {
        "strategy": "save10",
        "discount_type": "percentage",
        "value": "10%"
    }


def run_shopify_discount_agent(cart_id: Optional[str]) -> Dict[str, Any]:
    if not cart_id:
        return {
            "agent": "shopify_agent",
            "success": False,
            "action": "create_discount_code",
            "message": "No cart_id provided.",
            "discount_code": None
        }

    cart_result = get_shopify_cart(cart_id)
    cart = cart_result.get("cart") or {}

    if not cart_result.get("found"):
        return {
            "agent": "shopify_agent",
            "success": False,
            "action": "create_discount_code",
            "cart_result": cart_result,
            "discount_code": None,
            "message": "Cart not found."
        }

    policy = choose_discount_strategy(cart)

    discount = create_discount_code(
        cart_id=cart.get("cart_id"),
        customer_name=cart.get("customer_name"),
        product=cart.get("product"),
        strategy=policy["strategy"],
        discount_type=policy["discount_type"],
        value=policy["value"],
        reason="abandoned_cart_recovery"
    )

    return {
        "agent": "shopify_agent",
        "success": True,
        "action": "create_discount_code",
        "cart_result": cart_result,
        "discount_code": discount
    }


def run_shopify_refund_review_agent(
    order_id: Optional[str],
    ticket_id: Optional[int],
    risk_level: str,
    user_message: str,
    requested_action: str = "refund_or_replacement_review"
) -> Dict[str, Any]:
    order_result = None
    if order_id:
        order_result = get_shopify_order(order_id)

    review = create_refund_review(
        order_id=order_id,
        ticket_id=ticket_id,
        reason="after_sales_or_refund_dispute",
        risk_level=risk_level,
        requested_action=requested_action,
        user_message=user_message,
        status="pending_review"
    )

    return {
        "agent": "shopify_agent",
        "success": True,
        "action": "create_refund_review",
        "order_result": order_result,
        "refund_review": review,
        "business_boundary": "The system only creates a refund review record. It does not approve refund automatically."
    }
