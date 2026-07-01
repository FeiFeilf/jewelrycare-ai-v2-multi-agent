from typing import Any, Dict, List
from app.db import get_conn


def query_order(order_id: str) -> Dict[str, Any]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    if not row:
        return {"found": False, "order_id": order_id, "message": "Order not found."}
    data = dict(row)
    data["found"] = True
    return data


def list_orders() -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]
