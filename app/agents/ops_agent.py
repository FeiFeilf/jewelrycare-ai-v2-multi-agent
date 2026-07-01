from typing import Any, Dict
from app.db import count_rows, get_conn


def dashboard_summary() -> Dict[str, Any]:
    total_orders = count_rows("orders")
    paid_orders = count_rows("orders", "status = ?", ("paid",))
    refunded_orders = count_rows("orders", "status = ?", ("refunded",))
    total_carts = count_rows("carts")
    abandoned_carts = count_rows("carts", "status = ?", ("abandoned",))
    total_tickets = count_rows("tickets")
    high_risk_tickets = count_rows("tickets", "risk_level = ?", ("high",))
    medium_risk_tickets = count_rows("tickets", "risk_level = ?", ("medium",))
    low_risk_tickets = count_rows("tickets", "risk_level = ?", ("low",))
    total_handoffs = count_rows("handoffs")
    open_handoffs = count_rows("handoffs", "status = ?", ("open",))
    total_recovery_logs = count_rows("recovery_logs")
    converted_recoveries = count_rows("recovery_logs", "conversion_status = ?", ("converted",))
    pending_recoveries = count_rows("recovery_logs", "conversion_status = ?", ("pending",))
    total_tasks = count_rows("tasks")
    open_tasks = count_rows("tasks", "status = ?", ("open",))
    total_traces = count_rows("agent_traces")
    total_conversations = count_rows("conversations")
    conversion_rate = round(converted_recoveries / total_recovery_logs, 4) if total_recovery_logs else 0.0

    return {
        "product": "JewelryCare AI v2",
        "dashboard_type": "multi_agent_operation_summary",
        "orders": {"total_orders": total_orders, "paid_orders": paid_orders, "refunded_orders": refunded_orders},
        "carts": {"total_carts": total_carts, "abandoned_carts": abandoned_carts},
        "tickets": {
            "total_tickets": total_tickets,
            "high_risk_tickets": high_risk_tickets,
            "medium_risk_tickets": medium_risk_tickets,
            "low_risk_tickets": low_risk_tickets,
        },
        "handoffs": {"total_handoffs": total_handoffs, "open_handoffs": open_handoffs},
        "recovery": {
            "total_recovery_logs": total_recovery_logs,
            "converted_recoveries": converted_recoveries,
            "pending_recoveries": pending_recoveries,
            "conversion_rate": conversion_rate,
        },
        "multi_agent": {
            "total_conversations": total_conversations,
            "total_agent_traces": total_traces,
            "total_tasks": total_tasks,
            "open_tasks": open_tasks,
        },
        "business_meaning": (
            "The system records conversations, agent decisions, business actions and follow-up tasks, "
            "forming a closed-loop multi-agent customer service operation workflow."
        ),
    }


def ticket_stats() -> Dict[str, Any]:
    conn = get_conn()
    risk_rows = conn.execute("""
        SELECT risk_level, COUNT(*) AS count
        FROM tickets
        GROUP BY risk_level
        ORDER BY count DESC
    """).fetchall()
    status_rows = conn.execute("""
        SELECT status, COUNT(*) AS count
        FROM tickets
        GROUP BY status
        ORDER BY count DESC
    """).fetchall()
    queue_rows = conn.execute("""
        SELECT assigned_to, COUNT(*) AS count
        FROM tickets
        GROUP BY assigned_to
        ORDER BY count DESC
    """).fetchall()
    recent_rows = conn.execute("""
        SELECT ticket_id, order_id, issue_type, risk_level, assigned_to, status, created_at
        FROM tickets
        ORDER BY created_at DESC
        LIMIT 10
    """).fetchall()
    conn.close()
    return {
        "dashboard_type": "ticket_stats",
        "by_risk_level": [dict(row) for row in risk_rows],
        "by_status": [dict(row) for row in status_rows],
        "by_assigned_queue": [dict(row) for row in queue_rows],
        "recent_tickets": [dict(row) for row in recent_rows],
    }


def recovery_stats() -> Dict[str, Any]:
    conn = get_conn()
    strategy_rows = conn.execute("""
        SELECT strategy, COUNT(*) AS count FROM recovery_logs GROUP BY strategy ORDER BY count DESC
    """).fetchall()
    coupon_rows = conn.execute("""
        SELECT coupon, COUNT(*) AS count FROM recovery_logs GROUP BY coupon ORDER BY count DESC
    """).fetchall()
    touch_rows = conn.execute("""
        SELECT touch_status, COUNT(*) AS count FROM recovery_logs GROUP BY touch_status ORDER BY count DESC
    """).fetchall()
    conversion_rows = conn.execute("""
        SELECT conversion_status, COUNT(*) AS count FROM recovery_logs GROUP BY conversion_status ORDER BY count DESC
    """).fetchall()
    total = conn.execute("SELECT COUNT(*) AS cnt FROM recovery_logs").fetchone()["cnt"]
    converted = conn.execute(
        "SELECT COUNT(*) AS cnt FROM recovery_logs WHERE conversion_status = ?",
        ("converted",),
    ).fetchone()["cnt"]
    conn.close()
    return {
        "dashboard_type": "recovery_stats",
        "total_recovery_logs": total,
        "converted_recoveries": converted,
        "conversion_rate": round(converted / total, 4) if total else 0.0,
        "by_strategy": [dict(row) for row in strategy_rows],
        "by_coupon": [dict(row) for row in coupon_rows],
        "by_touch_status": [dict(row) for row in touch_rows],
        "by_conversion_status": [dict(row) for row in conversion_rows],
    }
