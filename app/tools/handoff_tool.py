import time
from typing import Any, Dict, Optional
from app.db import get_conn


def create_handoff_record(session_id: str, order_id: Optional[str], reason: str, user_message: str) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO handoffs(session_id, order_id, reason, user_message, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, order_id, reason, user_message, "open", int(time.time())))
    handoff_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return {"created": True, "handoff_id": handoff_id, "reason": reason, "status": "open"}


def list_handoffs(status: Optional[str] = None, reason: Optional[str] = None) -> list[dict[str, Any]]:
    conn = get_conn()
    sql = "SELECT * FROM handoffs WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if reason:
        sql += " AND reason = ?"
        params.append(reason)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_handoff(handoff_id: int) -> Dict[str, Any]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,)).fetchone()
    conn.close()
    if not row:
        return {"found": False, "message": "Handoff record not found."}
    return {"found": True, "handoff": dict(row)}


def update_handoff_status(handoff_id: int, status: str) -> Dict[str, Any]:
    allowed = {"open", "assigned", "in_progress", "resolved", "closed"}
    if status not in allowed:
        return {"updated": False, "message": f"Invalid status. Allowed values: {sorted(list(allowed))}"}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE handoffs SET status = ? WHERE handoff_id = ?", (status, handoff_id))
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        return {"updated": False, "message": "Handoff record not found."}
    row = conn.execute("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,)).fetchone()
    conn.close()
    return {"updated": True, "handoff": dict(row)}
