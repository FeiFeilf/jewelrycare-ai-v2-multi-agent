from typing import Optional
from fastapi import FastAPI

from app.db import init_db, get_conn, DB_PATH
from app.schemas import (
    HandleMessageRequest,
    TicketStatusUpdate,
    HandoffStatusUpdate,
    RecoveryConversionUpdate,
    RecoveryTouchUpdate,
    TaskStatusUpdate,
)
from app.orchestrator import orchestrate_message_v3
from app.agents.ops_agent import dashboard_summary, ticket_stats, recovery_stats
from app.tools.order_tool import list_orders
from app.tools.ticket_tool import list_tickets, get_ticket, update_ticket_status
from app.tools.handoff_tool import list_handoffs, get_handoff, update_handoff_status
from app.tools.recovery_tool import list_recovery_logs, update_recovery_conversion, update_recovery_touch
from app.tools.task_tool import list_tasks, get_task, update_task_status


app = FastAPI(
    title="JewelryCare AI v2 Multi-Agent Backend",
    description="Closed-loop Multi-Agent backend for cross-border jewelry customer service, after-sales risk control, abandoned cart recovery and operations.",
    version="2.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root():
    return {"service": "JewelryCare AI v2 Multi-Agent Backend", "version": "2.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "customer-tools", "version": "2.0.0", "db_path": DB_PATH}


@app.post("/tools/handle_message_v3", operation_id="handle_customer_message_v3")
def handle_message_v3(req: HandleMessageRequest):
    return orchestrate_message_v3(req)


@app.post("/tools/handle_message_v2", operation_id="handle_customer_message_v2")
def handle_message_v2(req: HandleMessageRequest):
    return orchestrate_message_v3(req)


@app.get("/tools/orders")
def api_list_orders():
    orders = list_orders()
    return {"count": len(orders), "orders": orders}


@app.get("/tools/tickets")
def api_list_tickets(status: Optional[str] = None, risk_level: Optional[str] = None):
    tickets = list_tickets(status=status, risk_level=risk_level)
    return {"count": len(tickets), "tickets": tickets}


@app.get("/tools/tickets/{ticket_id}")
def api_get_ticket(ticket_id: int):
    return get_ticket(ticket_id)


@app.post("/tools/tickets/{ticket_id}/status")
def api_update_ticket_status(ticket_id: int, req: TicketStatusUpdate):
    return update_ticket_status(ticket_id, req.status)


@app.get("/tools/handoffs")
def api_list_handoffs(status: Optional[str] = None, reason: Optional[str] = None):
    handoffs = list_handoffs(status=status, reason=reason)
    return {"count": len(handoffs), "handoffs": handoffs}


@app.get("/tools/handoffs/{handoff_id}")
def api_get_handoff(handoff_id: int):
    return get_handoff(handoff_id)


@app.post("/tools/handoffs/{handoff_id}/status")
def api_update_handoff_status(handoff_id: int, req: HandoffStatusUpdate):
    return update_handoff_status(handoff_id, req.status)


@app.get("/tools/recovery_logs")
def api_list_recovery_logs(touch_status: Optional[str] = None, conversion_status: Optional[str] = None):
    logs = list_recovery_logs(touch_status=touch_status, conversion_status=conversion_status)
    return {"count": len(logs), "recovery_logs": logs}


@app.post("/tools/recovery_logs/{log_id}/conversion")
def api_update_recovery_conversion(log_id: int, req: RecoveryConversionUpdate):
    return update_recovery_conversion(log_id, req.conversion_status)


@app.post("/tools/recovery_logs/{log_id}/touch")
def api_update_recovery_touch(log_id: int, req: RecoveryTouchUpdate):
    return update_recovery_touch(log_id, req.touch_status)


@app.get("/tools/tasks")
def api_list_tasks(status: Optional[str] = None, task_type: Optional[str] = None):
    tasks = list_tasks(status=status, task_type=task_type)
    return {"count": len(tasks), "tasks": tasks}


@app.get("/tools/tasks/{task_id}")
def api_get_task(task_id: int):
    return get_task(task_id)


@app.post("/tools/tasks/{task_id}/status")
def api_update_task_status(task_id: int, req: TaskStatusUpdate):
    return update_task_status(task_id, req.status)


@app.get("/tools/conversations")
def api_list_conversations():
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM conversations
        ORDER BY created_at DESC
        LIMIT 50
    """).fetchall()
    conn.close()
    return {"count": len(rows), "conversations": [dict(row) for row in rows]}


@app.get("/tools/agent_traces")
def api_list_agent_traces(conversation_id: Optional[int] = None):
    conn = get_conn()
    if conversation_id:
        rows = conn.execute("""
            SELECT * FROM agent_traces
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """, (conversation_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM agent_traces
            ORDER BY created_at DESC
            LIMIT 100
        """).fetchall()
    conn.close()
    return {"count": len(rows), "agent_traces": [dict(row) for row in rows]}


@app.get("/tools/dashboard/summary")
def api_dashboard_summary():
    return dashboard_summary()


@app.get("/tools/dashboard/ticket_stats")
def api_ticket_stats():
    return ticket_stats()


@app.get("/tools/dashboard/recovery_stats")
def api_recovery_stats():
    return recovery_stats()
