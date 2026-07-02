import time
import uuid
from typing import Any, Dict, List, Optional

from app.db import get_conn
from app.tools.order_tool import query_order
from app.tools.recovery_tool import query_cart


def _now() -> int:
    return int(time.time())


def _make_discount_code(strategy: str, cart_id: Optional[str] = None) -> str:
    prefix = "JC"
    if strategy == "free_shipping":
        return f"{prefix}-FREESHIP-{str(uuid.uuid4())[:6].upper()}"
    if strategy == "save10":
        return f"{prefix}-SAVE10-{str(uuid.uuid4())[:6].upper()}"
    if cart_id:
        return f"{prefix}-{cart_id[-4:]}-{str(uuid.uuid4())[:6].upper()}"
    return f"{prefix}-OFFER-{str(uuid.uuid4())[:6].upper()}"


def get_shopify_order(order_id: str) -> Dict[str, Any]:
    order = query_order(order_id)
    return {
        "tool": "mock_shopify.get_order",
        "found": order.get("found", False),
        "order": order,
        "source": "mock_shopify_api"
    }


def get_shopify_cart(cart_id: str) -> Dict[str, Any]:
    cart = query_cart(cart_id)
    return {
        "tool": "mock_shopify.get_cart",
        "found": cart.get("found", False),
        "cart": cart,
        "source": "mock_shopify_api"
    }


def create_discount_code(
    cart_id: Optional[str],
    customer_name: Optional[str],
    product: Optional[str],
    strategy: str,
    discount_type: str,
    value: str,
    reason: str = "abandoned_cart_recovery"
) -> Dict[str, Any]:
    code = _make_discount_code(strategy=strategy, cart_id=cart_id)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO discount_codes(
            code,
            cart_id,
            customer_name,
            product,
            strategy,
            discount_type,
            value,
            reason,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            code,
            cart_id,
            customer_name,
            product,
            strategy,
            discount_type,
            value,
            reason,
            "active",
            _now()
        )
    )

    discount_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "tool": "mock_shopify.create_discount_code",
        "created": True,
        "discount_id": discount_id,
        "code": code,
        "cart_id": cart_id,
        "customer_name": customer_name,
        "product": product,
        "strategy": strategy,
        "discount_type": discount_type,
        "value": value,
        "reason": reason,
        "status": "active",
        "source": "mock_shopify_api"
    }


def create_refund_review(
    order_id: Optional[str],
    ticket_id: Optional[int],
    reason: str,
    risk_level: str,
    requested_action: str,
    user_message: str,
    status: str = "pending_review"
) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO refund_reviews(
            order_id,
            ticket_id,
            reason,
            risk_level,
            requested_action,
            user_message,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            ticket_id,
            reason,
            risk_level,
            requested_action,
            user_message,
            status,
            _now()
        )
    )

    review_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "tool": "mock_shopify.create_refund_review",
        "created": True,
        "review_id": review_id,
        "order_id": order_id,
        "ticket_id": ticket_id,
        "reason": reason,
        "risk_level": risk_level,
        "requested_action": requested_action,
        "status": status,
        "source": "mock_shopify_api",
        "business_rule": "Refund, replacement and compensation must be reviewed by human staff before final approval."
    }


def list_discount_codes(status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_conn()

    sql = "SELECT * FROM discount_codes WHERE 1=1"
    params = []

    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY created_at DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]


def list_refund_reviews(status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_conn()

    sql = "SELECT * FROM refund_reviews WHERE 1=1"
    params = []

    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY created_at DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_discount_code_status(discount_id: int, status: str) -> Dict[str, Any]:
    allowed = {"active", "used", "expired", "cancelled"}

    if status not in allowed:
        return {
            "updated": False,
            "message": f"Invalid status. Allowed values: {sorted(list(allowed))}"
        }

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE discount_codes SET status = ? WHERE discount_id = ?",
        (status, discount_id)
    )
    conn.commit()

    if cur.rowcount == 0:
        conn.close()
        return {"updated": False, "message": "Discount code not found."}

    row = conn.execute(
        "SELECT * FROM discount_codes WHERE discount_id = ?",
        (discount_id,)
    ).fetchone()

    conn.close()
    return {"updated": True, "discount_code": dict(row)}


def update_refund_review_status(review_id: int, status: str) -> Dict[str, Any]:
    allowed = {
        "pending_review",
        "in_review",
        "approved",
        "rejected",
        "need_more_evidence",
        "closed"
    }

    if status not in allowed:
        return {
            "updated": False,
            "message": f"Invalid status. Allowed values: {sorted(list(allowed))}"
        }

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE refund_reviews SET status = ? WHERE review_id = ?",
        (status, review_id)
    )
    conn.commit()

    if cur.rowcount == 0:
        conn.close()
        return {"updated": False, "message": "Refund review not found."}

    row = conn.execute(
        "SELECT * FROM refund_reviews WHERE review_id = ?",
        (review_id,)
    ).fetchone()

    conn.close()
    return {"updated": True, "refund_review": dict(row)}
