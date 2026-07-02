from typing import Any, Dict, List

from app.tools.react_tool import create_react_step


def _safe_get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def run_react_planner_agent(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    ReAct Planner Agent

    该 Agent 不替代业务 Agent，而是在一次 Multi-Agent 处理完成后，
    将实际发生的路由、工具调用和业务动作转化为 Thought-Action-Observation 轨迹。
    这样既保持系统稳定，又能显式展示 ReAct 式任务规划过程。
    """

    session_id = result.get("session_id") or "default-session"
    conversation_id = int(result.get("conversation_id") or 0)
    message = result.get("original_message") or ""
    intent = result.get("intent") or "unknown"
    order_id = result.get("order_id")
    cart_id = result.get("cart_id")

    steps: List[Dict[str, Any]] = []
    idx = 1

    def add(thought: str, action: str, action_input=None, observation=None, success: bool = True):
        nonlocal idx
        step = create_react_step(
            session_id=session_id,
            conversation_id=conversation_id,
            step_index=idx,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation,
            success=success,
        )
        steps.append(step)
        idx += 1

    add(
        thought="需要先理解用户当前问题，并判断应交给哪个业务 Agent 处理。",
        action="RouterAgent.route_message",
        action_input={"message": message},
        observation={
            "intent": intent,
            "target_agent": result.get("target_agent"),
            "confidence": result.get("confidence"),
            "order_id": order_id,
            "cart_id": cart_id,
        },
        success=True,
    )

    if order_id:
        order = result.get("order") or {}
        add(
            thought="用户提供了订单号，需要查询订单是否存在以及当前订单和物流状态。",
            action="OrderAgent.query_order",
            action_input={"order_id": order_id},
            observation={
                "found": order.get("found"),
                "status": order.get("status"),
                "logistics_status": order.get("logistics_status"),
                "product": order.get("product"),
            },
            success=bool(order.get("found")),
        )

    if intent in ["after_sales", "after_sales_image_triage"]:
        image_assessment = result.get("image_assessment") or {}
        ticket = result.get("ticket") or {}

        add(
            thought="用户反馈商品损坏，需要结合文本描述和图片信息进行售后风险初筛。",
            action="AfterSalesAgent.assess_damage_and_create_ticket",
            action_input={
                "order_id": order_id,
                "message": message,
                "has_image": _safe_get(image_assessment, "has_image", default=False),
            },
            observation={
                "risk_level": image_assessment.get("risk_level"),
                "defect_type": image_assessment.get("defect_type"),
                "ticket_created": ticket.get("created"),
                "ticket_id": ticket.get("ticket_id"),
            },
            success=bool(ticket.get("created")) or not bool(order_id),
        )

    if intent == "abandoned_cart_recovery":
        recovery = result.get("cart_recovery") or {}
        recovery_log = result.get("recovery_log") or {}

        add(
            thought="用户询问购物车优惠，需要查询弃单购物车并选择合适的挽回策略。",
            action="RecoveryAgent.recover_abandoned_cart",
            action_input={"cart_id": cart_id},
            observation={
                "cart_found": recovery.get("found"),
                "coupon": recovery.get("coupon"),
                "strategy": recovery.get("strategy"),
                "recovery_log_created": recovery_log.get("created"),
                "log_id": recovery_log.get("log_id"),
            },
            success=bool(recovery.get("found")),
        )

    if intent in ["knowledge_question", "general_consultation", "pre_sale_guidance"]:
        knowledge = result.get("knowledge") or result.get("pre_sale") or {}
        add(
            thought="该问题属于知识问答或售前咨询，应结合 RAG 知识库生成专业客服回复。",
            action="KnowledgeAgent.answer_with_rag_policy",
            action_input={"message": message},
            observation={
                "knowledge_available": bool(knowledge),
                "knowledge_scope": knowledge.get("knowledge_scope") if isinstance(knowledge, dict) else None,
            },
            success=True,
        )

    if result.get("handoff"):
        handoff_record = result.get("handoff_record") or {}
        add(
            thought="当前问题涉及投诉、订单异常、退款争议或高风险售后，不能由大模型直接裁决，需要转人工。",
            action="HandoffAgent.create_handoff_record",
            action_input={
                "order_id": order_id,
                "intent": intent,
                "message": message,
            },
            observation={
                "handoff_created": handoff_record.get("created"),
                "handoff_id": handoff_record.get("handoff_id"),
                "reason": result.get("handoff_reason") or handoff_record.get("reason"),
            },
            success=bool(handoff_record.get("created")),
        )

    tasks = result.get("tasks") or []
    add(
        thought="需要把本次处理结果转化为可跟进的业务任务，保证后续流程闭环。",
        action="TaskAgent.create_followup_tasks",
        action_input={
            "intent": intent,
            "handoff": result.get("handoff"),
            "ticket_created": bool(result.get("ticket")),
            "recovery_log_created": bool(result.get("recovery_log")),
        },
        observation={
            "task_count": result.get("task_count", len(tasks)),
            "tasks_created": [
                {
                    "task_id": t.get("task_id"),
                    "task_type": t.get("task_type"),
                    "status": t.get("status"),
                }
                for t in tasks
                if isinstance(t, dict)
            ],
        },
        success=True,
    )

    return {
        "agent": "react_planner_agent",
        "success": True,
        "react_step_count": len(steps),
        "react_steps": steps,
    }
