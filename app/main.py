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
from app.orchestrator_v4 import orchestrate_message_v4
from app.agents.ops_agent import dashboard_summary, ticket_stats, recovery_stats
from app.tools.order_tool import list_orders
from app.tools.ticket_tool import list_tickets, get_ticket, update_ticket_status
from app.tools.handoff_tool import list_handoffs, get_handoff, update_handoff_status
from app.tools.recovery_tool import list_recovery_logs, update_recovery_conversion, update_recovery_touch
from app.tools.task_tool import list_tasks, get_task, update_task_status
from app.agents.vision_agent import list_vision_assessments
from app.tools.memory_tool import list_memory_items, list_customer_profiles
from app.tools.evaluation_tool import list_bad_case_logs, list_evaluation_results
from app.tools.shopify_mock_tool import (
    get_shopify_order,
    get_shopify_cart,
    create_discount_code,
    create_refund_review,
    list_discount_codes,
    list_refund_reviews,
    update_discount_code_status,
    update_refund_review_status,
)


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



@app.post("/tools/handle_message_v4", operation_id="handle_customer_message_v4")
def handle_message_v4(req: HandleMessageRequest):
    return orchestrate_message_v4(req)


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



@app.get("/tools/react_steps")
def api_list_react_steps(
    conversation_id: Optional[int] = None,
    session_id: Optional[str] = None,
    limit: int = 100
):
    from app.tools.react_tool import list_react_steps

    steps = list_react_steps(
        conversation_id=conversation_id,
        session_id=session_id,
        limit=limit
    )

    return {
        "count": len(steps),
        "react_steps": steps
    }



@app.get("/mock_shopify/orders/{order_id}")
def api_mock_shopify_get_order(order_id: str):
    return get_shopify_order(order_id)


@app.get("/mock_shopify/carts/{cart_id}")
def api_mock_shopify_get_cart(cart_id: str):
    return get_shopify_cart(cart_id)


@app.post("/mock_shopify/discount_codes")
def api_mock_shopify_create_discount_code(payload: dict):
    return create_discount_code(
        cart_id=payload.get("cart_id"),
        customer_name=payload.get("customer_name"),
        product=payload.get("product"),
        strategy=payload.get("strategy", "free_shipping"),
        discount_type=payload.get("discount_type", "shipping"),
        value=payload.get("value", "FREE_SHIPPING"),
        reason=payload.get("reason", "manual_test")
    )


@app.post("/mock_shopify/refund_reviews")
def api_mock_shopify_create_refund_review(payload: dict):
    return create_refund_review(
        order_id=payload.get("order_id"),
        ticket_id=payload.get("ticket_id"),
        reason=payload.get("reason", "manual_test"),
        risk_level=payload.get("risk_level", "manual_review_required"),
        requested_action=payload.get("requested_action", "refund_or_replacement_review"),
        user_message=payload.get("user_message", ""),
        status=payload.get("status", "pending_review")
    )


@app.get("/tools/discount_codes")
def api_list_discount_codes(status: Optional[str] = None):
    codes = list_discount_codes(status=status)
    return {
        "count": len(codes),
        "discount_codes": codes
    }


@app.get("/tools/refund_reviews")
def api_list_refund_reviews(status: Optional[str] = None):
    reviews = list_refund_reviews(status=status)
    return {
        "count": len(reviews),
        "refund_reviews": reviews
    }


@app.post("/tools/discount_codes/{discount_id}/status")
def api_update_discount_code_status(discount_id: int, payload: dict):
    return update_discount_code_status(discount_id, payload.get("status", ""))


@app.post("/tools/refund_reviews/{review_id}/status")
def api_update_refund_review_status(review_id: int, payload: dict):
    return update_refund_review_status(review_id, payload.get("status", ""))



@app.get("/tools/vision_assessments")
def api_list_vision_assessments(limit: int = 100):
    items = list_vision_assessments(limit=limit)
    return {
        "count": len(items),
        "vision_assessments": items
    }


@app.get("/tools/memory_items")
def api_list_memory_items(
    session_id: Optional[str] = None,
    customer_id: Optional[int] = None,
    limit: int = 100
):
    items = list_memory_items(session_id=session_id, customer_id=customer_id, limit=limit)
    return {
        "count": len(items),
        "memory_items": items
    }


@app.get("/tools/customer_profiles")
def api_list_customer_profiles(limit: int = 100):
    profiles = list_customer_profiles(limit=limit)
    return {
        "count": len(profiles),
        "customer_profiles": profiles
    }


@app.get("/tools/bad_case_logs")
def api_list_bad_case_logs(limit: int = 100):
    logs = list_bad_case_logs(limit=limit)
    return {
        "count": len(logs),
        "bad_case_logs": logs
    }


@app.get("/tools/evaluation/results")
def api_list_evaluation_results(limit: int = 20):
    results = list_evaluation_results(limit=limit)
    return {
        "count": len(results),
        "evaluation_results": results
    }


@app.post("/tools/evaluation/run")
def api_run_evaluation():
    from app.agents.evaluation_agent import run_evaluation_suite
    from app.orchestrator_v4 import orchestrate_message_v4
    from app.schemas import HandleMessageRequest

    return run_evaluation_suite(orchestrate_message_v4, HandleMessageRequest)



@app.post("/tools/vision_from_url")
def api_vision_from_url(payload: dict):
    from app.tools.vision_adapter import analyze_image_url

    message = payload.get("message", "")
    image_url = payload.get("image_url") or payload.get("url")

    return analyze_image_url(
        message=message,
        image_url=image_url
    )


@app.get("/tools/dashboard/summary")
def api_dashboard_summary():
    return dashboard_summary()


@app.get("/tools/dashboard/ticket_stats")
def api_ticket_stats():
    return ticket_stats()


@app.get("/tools/dashboard/recovery_stats")
def api_recovery_stats():
    return recovery_stats()
