from typing import Any, Dict

from app.db import create_conversation, update_conversation, log_agent_trace
from app.agents.router_agent import route_message
from app.agents.knowledge_agent import run_knowledge_agent
from app.agents.order_agent import run_order_agent
from app.agents.after_sales_agent import run_after_sales_agent
from app.agents.recovery_agent import run_recovery_agent
from app.agents.handoff_agent import run_handoff_agent
from app.agents.task_agent import run_task_agent


def orchestrate_message_v3(req) -> Dict[str, Any]:
    message = req.message or ""
    session_id = req.session_id or "default-session"
    files = req.files or []
    vision_summary = req.vision_summary or ""
    has_image = len(files) > 0

    conversation_id = create_conversation(session_id=session_id, user_message=message)
    traces = []

    router = route_message(message, has_image=has_image)
    traces.append(log_agent_trace(
        session_id=session_id,
        conversation_id=conversation_id,
        agent_name="router_agent",
        input_summary=message[:300],
        output_summary=f"intent={router['intent']}, target_agent={router['target_agent']}",
        tool_called="route_message",
        success=True,
    ))

    result: Dict[str, Any] = {
        "product": "JewelryCare AI v2",
        "mode": "closed_loop_multi_agent",
        "conversation_id": conversation_id,
        "session_id": session_id,
        "original_message": message,
        "intent": router["intent"],
        "confidence": router["confidence"],
        "target_agent": router["target_agent"],
        "order_id": router.get("order_id"),
        "cart_id": router.get("cart_id"),
        "order": None,
        "ticket": None,
        "image_assessment": None,
        "cart_recovery": None,
        "recovery_log": None,
        "knowledge": None,
        "handoff": False,
        "handoff_record": None,
        "tasks": [],
        "agent_traces": traces,
        "next_action": router["next_action"],
    }

    if result["order_id"]:
        order_result = run_order_agent(result["order_id"])
        result["order"] = order_result.get("order")
        found = bool(result["order"] and result["order"].get("found"))
        traces.append(log_agent_trace(
            session_id=session_id,
            conversation_id=conversation_id,
            agent_name="order_agent",
            input_summary=f"order_id={result['order_id']}",
            output_summary=f"found={found}",
            tool_called="query_order",
            success=found,
        ))
        if result["order"] and result["order"].get("found") is False:
            result["handoff"] = True
            result["next_action"] = "order_not_found_need_handoff"

    if result["intent"] in ["knowledge_question", "general_consultation"]:
        knowledge = run_knowledge_agent(message)
        result["knowledge"] = knowledge
        traces.append(log_agent_trace(
            session_id=session_id,
            conversation_id=conversation_id,
            agent_name="knowledge_agent",
            input_summary=message[:300],
            output_summary="knowledge_scope_ready_for_dify_rag",
            tool_called="rag_policy",
            success=True,
        ))

    if result["intent"] == "logistics_query":
        if not result["order_id"]:
            result["next_action"] = "ask_user_to_provide_order_id"
        elif result["order"] and result["order"].get("found"):
            result["next_action"] = "reply_order_logistics_status"

    if result["intent"] == "after_sales":
        order_found = bool(result["order"] and result["order"].get("found"))
        after_sales = run_after_sales_agent(
            message=message,
            order_id=result["order_id"],
            order_found=order_found,
            has_image=has_image,
            vision_summary=vision_summary,
        )
        result["ticket"] = after_sales.get("ticket")
        result["image_assessment"] = after_sales.get("image_assessment")
        result["next_action"] = after_sales.get("next_action")
        traces.append(log_agent_trace(
            session_id=session_id,
            conversation_id=conversation_id,
            agent_name="after_sales_agent",
            input_summary=f"order_id={result['order_id']}, has_image={has_image}",
            output_summary=(
                f"risk_level={result['image_assessment'].get('risk_level') if result['image_assessment'] else None}, "
                f"ticket_created={bool(result['ticket'])}"
            ),
            tool_called="assess_damage_level/create_ticket",
            success=after_sales.get("success", False),
        ))
        if after_sales.get("need_handoff"):
            result["handoff"] = True

    if result["intent"] == "abandoned_cart_recovery":
        recovery = run_recovery_agent(result["cart_id"])
        result["cart_recovery"] = recovery.get("cart_recovery")
        result["recovery_log"] = recovery.get("recovery_log")
        result["next_action"] = recovery.get("next_action")
        traces.append(log_agent_trace(
            session_id=session_id,
            conversation_id=conversation_id,
            agent_name="recovery_agent",
            input_summary=f"cart_id={result['cart_id']}",
            output_summary=f"success={recovery.get('success')}, log_created={bool(result['recovery_log'])}",
            tool_called="query_cart/create_recovery_log",
            success=recovery.get("success", False),
        ))
        if recovery.get("need_handoff"):
            result["handoff"] = True

    if result["intent"] == "human_complaint":
        result["handoff"] = True

    if result["handoff"]:
        risk_level = None
        if result.get("image_assessment"):
            risk_level = result["image_assessment"].get("risk_level")
        handoff = run_handoff_agent(
            session_id=session_id,
            order_id=result.get("order_id"),
            intent=result["intent"],
            message=message,
            order=result.get("order"),
            risk_level=risk_level,
        )
        result["handoff_record"] = handoff.get("handoff_record")
        result["handoff_reason"] = handoff.get("handoff_reason")
        result["handoff_message"] = handoff.get("handoff_message")
        result["next_action"] = handoff.get("next_action")
        traces.append(log_agent_trace(
            session_id=session_id,
            conversation_id=conversation_id,
            agent_name="handoff_agent",
            input_summary=f"intent={result['intent']}, order_id={result.get('order_id')}",
            output_summary=f"reason={result.get('handoff_reason')}",
            tool_called="create_handoff_record",
            success=True,
        ))

    task_result = run_task_agent(result)
    result["tasks"] = task_result.get("tasks_created", [])
    result["task_count"] = task_result.get("task_count", 0)
    traces.append(log_agent_trace(
        session_id=session_id,
        conversation_id=conversation_id,
        agent_name="task_agent",
        input_summary=f"intent={result['intent']}, handoff={result['handoff']}",
        output_summary=f"task_count={result['task_count']}",
        tool_called="create_task",
        success=True,
    ))

    result["agent_traces"] = traces
    response_draft = build_response_draft(result)
    result["response_draft"] = response_draft
    update_conversation(conversation_id=conversation_id, intent=result["intent"], final_response=response_draft)
    return result


def build_response_draft(result: Dict[str, Any]) -> str:
    intent = result.get("intent")
    order = result.get("order") or {}
    ticket = result.get("ticket") or {}
    recovery = result.get("cart_recovery") or {}
    handoff = result.get("handoff_record") or {}

    if intent == "logistics_query":
        if not result.get("order_id"):
            return "请提供订单号，我可以帮您查询物流状态。"
        if not order.get("found"):
            return "未查询到该订单，请核对订单号。系统已建议转人工进一步处理。"
        return f"已查询到订单 {order.get('order_id')}，当前订单状态为 {order.get('status')}，物流状态为 {order.get('logistics_status')}。"

    if intent == "after_sales":
        if not result.get("order_id"):
            return "请先提供订单号，并补充商品问题照片或视频，方便售后审核。"
        if order and order.get("found") is False:
            return "未查询到该订单，系统已记录人工处理请求，请核对订单号或联系人工客服。"
        if ticket.get("created"):
            if result.get("handoff"):
                return f"已创建售后工单 #{ticket.get('ticket_id')}。该问题风险较高，将由人工客服进一步审核。"
            return f"已创建售后工单 #{ticket.get('ticket_id')}。请根据证据要求补充照片或视频，售后客服会进一步审核。"

    if intent == "abandoned_cart_recovery":
        if recovery.get("found"):
            return f"您的购物车商品仍可继续下单，本次可使用优惠码 {recovery.get('coupon')}。"
        return "未查询到该购物车记录，请核对购物车编号或联系人工客服。"

    if intent == "human_complaint":
        if handoff.get("created"):
            return "很抱歉给您带来不好的体验。系统已记录人工处理请求，将由人工客服进一步跟进。"
        return "很抱歉给您带来不好的体验，该问题将转交人工客服进一步处理。"

    if intent in ["knowledge_question", "general_consultation"]:
        return "我可以为您解答珠宝材质、保养方式、物流政策、退换货政策和退款规则等问题。具体回复请结合 Dify RAG 知识库生成。"

    return "系统已收到您的问题，并完成 Multi-Agent 初步处理。"
