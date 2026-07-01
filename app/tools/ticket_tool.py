import time
from typing import Any, Dict, Optional
from app.db import get_conn


def build_ticket_business_fields(risk_level: str, has_image: bool = False) -> Dict[str, str]:
    if risk_level == "high":
        evidence_required = (
            "请提供商品整体照片、问题部位近距离照片、包装照片、吊牌照片、物流面单照片；"
            "如涉及断裂、掉钻或严重破损，请补充清晰视频。"
        )
        suggested_resolution = (
            "高风险售后问题，需人工客服优先审核。客服应核实商品状态、物流状态和用户证据后，"
            "再判断是否进入退款、补发或换货审核流程。"
        )
        assigned_to = "human_after_sales_queue"
    elif risk_level == "medium":
        evidence_required = "请提供商品整体照片、问题部位近距离照片、包装照片、吊牌照片和物流面单照片。"
        suggested_resolution = (
            "中等风险售后问题，进入售后审核流程。客服需根据照片和订单信息判断是否属于质量问题，"
            "暂不直接承诺退款、补发或换货。"
        )
        assigned_to = "after_sales_review_queue"
    else:
        evidence_required = "当前信息不足，请补充订单号、商品整体照片、问题部位照片和更完整的问题描述。"
        suggested_resolution = "低风险或信息不足问题，先引导用户补充证据，不直接进入退款或补发判断。"
        assigned_to = "auto_support_queue"

    if not has_image:
        evidence_required += " 当前尚未收到图片，请用户补充清晰照片或视频。"

    return {
        "evidence_required": evidence_required,
        "suggested_resolution": suggested_resolution,
        "assigned_to": assigned_to,
    }


def create_ticket(order_id: str, issue_type: str, description: str, risk_level: str, has_image: bool = False) -> Dict[str, Any]:
    fields = build_ticket_business_fields(risk_level, has_image)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tickets(
            order_id, issue_type, description, risk_level,
            evidence_required, suggested_resolution, assigned_to,
            status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_id,
        issue_type,
        description,
        risk_level,
        fields["evidence_required"],
        fields["suggested_resolution"],
        fields["assigned_to"],
        "open",
        int(time.time()),
    ))
    ticket_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return {
        "created": True,
        "ticket_id": ticket_id,
        "order_id": order_id,
        "issue_type": issue_type,
        "risk_level": risk_level,
        "status": "open",
        "evidence_required": fields["evidence_required"],
        "suggested_resolution": fields["suggested_resolution"],
        "assigned_to": fields["assigned_to"],
    }


def list_tickets(status: Optional[str] = None, risk_level: Optional[str] = None) -> list[dict[str, Any]]:
    conn = get_conn()
    sql = "SELECT * FROM tickets WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if risk_level:
        sql += " AND risk_level = ?"
        params.append(risk_level)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_ticket(ticket_id: int) -> Dict[str, Any]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    conn.close()
    if not row:
        return {"found": False, "message": "Ticket not found."}
    return {"found": True, "ticket": dict(row)}


def update_ticket_status(ticket_id: int, status: str) -> Dict[str, Any]:
    allowed = {"open", "in_review", "waiting_customer_evidence", "escalated_to_human", "resolved", "closed"}
    if status not in allowed:
        return {"updated": False, "message": f"Invalid status. Allowed values: {sorted(list(allowed))}"}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE tickets SET status = ? WHERE ticket_id = ?", (status, ticket_id))
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        return {"updated": False, "message": "Ticket not found."}
    row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    conn.close()
    return {"updated": True, "ticket": dict(row)}
