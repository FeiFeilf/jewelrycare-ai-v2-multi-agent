import time
from typing import Any, Dict, Optional
from app.db import get_conn


def query_cart(cart_id: str) -> Dict[str, Any]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM carts WHERE cart_id = ?", (cart_id,)).fetchone()
    conn.close()
    if not row:
        return {"found": False, "cart_id": cart_id, "message": "Cart not found."}
    data = dict(row)
    data["found"] = True
    return data


def build_cart_recovery(cart: Dict[str, Any]) -> Dict[str, Any]:
    if not cart.get("found"):
        return {"found": False, "message": "Cart not found."}
    if int(cart.get("last_active_minutes") or 0) <= 60:
        coupon = "FREE-SHIPPING"
        strategy = "gentle_reminder"
    else:
        coupon = "SAVE10"
        strategy = "discount_recovery"
    return {
        "found": True,
        "cart": cart,
        "strategy": strategy,
        "coupon": coupon,
        "message": f"Hi {cart['customer_name']}, your {cart['product']} is still waiting in your cart. Complete checkout now and use code {coupon}.",
    }


def create_recovery_log(cart_recovery: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not cart_recovery or not cart_recovery.get("found"):
        return None
    cart = cart_recovery.get("cart") or {}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO recovery_logs(
            cart_id, customer_name, product, coupon, strategy,
            touch_status, conversion_status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cart.get("cart_id"),
        cart.get("customer_name"),
        cart.get("product"),
        cart_recovery.get("coupon"),
        cart_recovery.get("strategy"),
        "sent",
        "pending",
        int(time.time()),
    ))
    log_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return {
        "created": True,
        "log_id": log_id,
        "cart_id": cart.get("cart_id"),
        "customer_name": cart.get("customer_name"),
        "product": cart.get("product"),
        "coupon": cart_recovery.get("coupon"),
        "strategy": cart_recovery.get("strategy"),
        "touch_status": "sent",
        "conversion_status": "pending",
    }


def list_recovery_logs(touch_status: Optional[str] = None, conversion_status: Optional[str] = None) -> list[dict[str, Any]]:
    conn = get_conn()
    sql = "SELECT * FROM recovery_logs WHERE 1=1"
    params: list[Any] = []
    if touch_status:
        sql += " AND touch_status = ?"
        params.append(touch_status)
    if conversion_status:
        sql += " AND conversion_status = ?"
        params.append(conversion_status)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_recovery_conversion(log_id: int, conversion_status: str) -> Dict[str, Any]:
    allowed = {"pending", "converted", "not_converted", "expired"}
    if conversion_status not in allowed:
        return {"updated": False, "message": f"Invalid conversion_status. Allowed values: {sorted(list(allowed))}"}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE recovery_logs SET conversion_status = ? WHERE log_id = ?", (conversion_status, log_id))
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        return {"updated": False, "message": "Recovery log not found."}
    row = conn.execute("SELECT * FROM recovery_logs WHERE log_id = ?", (log_id,)).fetchone()
    conn.close()
    return {"updated": True, "recovery_log": dict(row)}


def update_recovery_touch(log_id: int, touch_status: str) -> Dict[str, Any]:
    allowed = {"pending", "sent", "failed", "cancelled"}
    if touch_status not in allowed:
        return {"updated": False, "message": f"Invalid touch_status. Allowed values: {sorted(list(allowed))}"}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE recovery_logs SET touch_status = ? WHERE log_id = ?", (touch_status, log_id))
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        return {"updated": False, "message": "Recovery log not found."}
    row = conn.execute("SELECT * FROM recovery_logs WHERE log_id = ?", (log_id,)).fetchone()
    conn.close()
    return {"updated": True, "recovery_log": dict(row)}
