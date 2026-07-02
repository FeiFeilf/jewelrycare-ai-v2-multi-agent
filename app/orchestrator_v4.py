from typing import Any, Dict

from app.orchestrator import orchestrate_message_v3
from app.agents.react_planner_agent import run_react_planner_agent

def _vision_summary_suggests_after_sales(summary: str, message: str = "") -> bool:
    text = (summary or "").lower()
    msg = (message or "").lower()

    high_or_medium_keywords = [
        "severity: high",
        "severity high",
        "severity: medium",
        "severity medium",
        "missing_stone",
        "missing stone",
        "broken",
        "breakage",
        "crack",
        "damaged setting",
        "visible_issue: yes",
        "掉钻",
        "缺石",
        "断裂",
        "裂开",
        "破损",
        "损坏",
        "高风险",
        "中风险",
    ]

    if any(k in text for k in high_or_medium_keywords):
        return True

    # 图片不清楚/低风险时，如果用户明确是在说订单商品有问题，也要进入售后工单流程
    has_image_context = (
        "has_image: true" in text
        or "visible_issue:" in text
        or "damage summary" in text
        or "image" in text
        or "picture" in text
        or "photo" in text
        or "图片" in text
        or "照片" in text
    )

    after_sales_message_keywords = [
        "有问题",
        "帮我看",
        "帮我处理",
        "订单号",
        "戒指",
        "项链",
        "手链",
        "耳环",
        "损坏",
        "坏了",
        "质量",
        "售后",
        "退款",
        "problem",
        "damage",
        "damaged",
        "refund",
        "order id",
    ]

    if has_image_context and any(k in msg for k in after_sales_message_keywords):
        return True

    return False


def _vision_summary_severity_for_routing(summary: str) -> str:
    text = (summary or "").lower()

    if "severity: high" in text or "severity high" in text:
        return "high"
    if "severity: medium" in text or "severity medium" in text:
        return "medium"
    if "severity: low" in text or "severity low" in text:
        return "low"

    if any(k in text for k in ["missing_stone", "missing stone", "broken", "breakage", "crack", "damaged setting"]):
        return "high"

    if any(k in text for k in ["scratch", "fading", "oxidation", "color difference"]):
        return "medium"

    return "low"


def _build_vision_routing_hint(summary: str) -> str:
    severity = _vision_summary_severity_for_routing(summary)

    if severity == "high":
        return (
            "图片初筛显示可能存在明确商品损坏，按高风险售后定损场景处理，"
            "需要创建售后工单，并进入人工复核流程。"
        )

    if severity == "medium":
        return (
            "图片初筛显示可能存在一般商品损坏，按中等风险售后定损场景处理，"
            "需要创建售后工单，并要求用户补充证据。"
        )

    return (
        "图片初筛结果不清晰或风险较低，但用户正在咨询订单商品问题，"
        "按低风险售后证据补充场景处理，需要创建售后工单，"
        "并要求用户提供更清晰的商品照片或视频。"
    )



def _create_vision_fallback_ticket(result: dict, vision_result: dict) -> dict:
    """
    当真实视觉模型返回 low/unclear，但用户确实在咨询订单商品问题时，
    创建一个低风险售后证据补充工单。

    规则：
    1. low/medium 可以建工单；
    2. low/medium 不自动转人工；
    3. low/medium 不创建退款审核；
    4. high 风险仍交给原有高风险售后流程处理。
    """
    from app.db import get_conn
    import json
    import time

    if result.get("ticket"):
        return result

    order_id = result.get("order_id")
    original_message = result.get("original_message") or result.get("message") or ""

    assessment = (vision_result or {}).get("vision_assessment") or {}
    severity = assessment.get("severity")
    damage_type = assessment.get("damage_type")

    if not order_id:
        return result

    if severity not in ["low", "medium"]:
        return result

    evidence_required = [
        "商品整体照片",
        "问题部位近距离清晰照片",
        "包装照片",
        "吊牌照片",
        "物流面单照片",
        "如图片不清楚，请补充一段展示问题部位的清晰视频"
    ]

    suggested_resolution = (
        "当前图片初筛结果不清晰或风险较低，系统已创建售后证据补充工单。"
        "请用户补充更清晰的照片或视频后再进入进一步审核。"
    )

    assigned_to = "auto_support_queue"

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO tickets(
            order_id,
            issue_type,
            description,
            risk_level,
            evidence_required,
            suggested_resolution,
            assigned_to,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            "vision_low_risk_evidence_followup",
            original_message[:500],
            severity,
            json.dumps(evidence_required, ensure_ascii=False),
            suggested_resolution,
            assigned_to,
            "open",
            int(time.time())
        )
    )

    ticket_id = cur.lastrowid
    conn.commit()
    conn.close()

    result["intent"] = "after_sales"
    result["ticket"] = {
        "created": True,
        "ticket_id": ticket_id,
        "order_id": order_id,
        "issue_type": "vision_low_risk_evidence_followup",
        "risk_level": severity,
        "damage_type": damage_type,
        "evidence_required": evidence_required,
        "suggested_resolution": suggested_resolution,
        "assigned_to": assigned_to,
        "status": "open"
    }

    # low / medium 风险只建工单，不强制转人工，不创建退款审核
    result["handoff"] = False
    result["vision_fallback_ticket_created"] = True

    return result



def _stage5_business_routing_hint(message: str) -> str:
    """
    阶段 5 Bad Case 优化用的确定性路由提示。
    目标：
    1. 区分售前知识问答 vs 售后工单；
    2. 区分物流政策 vs 订单物流查询；
    3. 强投诉 / 退款争议必须转人工；
    4. 有订单号 + 商品问题应进入售后。
    """
    import re

    msg = (message or "").lower()
    raw = message or ""

    has_order = re.search(r"\bORD\d+\b", raw, re.IGNORECASE) is not None
    has_cart = re.search(r"\bCART\d+\b", raw, re.IGNORECASE) is not None

    complaint_words = [
        "投诉", "举报", "欺骗", "差评", "赔偿", "必须马上", "不接受",
        "人工客服", "转人工", "非常生气", "机器人别回复",
        "complain", "complaint", "unacceptable", "demand", "human agent",
        "refund now", "compensation"
    ]

    cart_words = [
        "cart", "购物车", "coupon", "discount", "优惠", "优惠码", "折扣",
        "free shipping"
    ]

    logistics_query_words = [
        "where is my order", "order status", "has my", "shipped",
        "查物流", "查询物流", "订单到哪里", "到哪里了", "是不是已经送到",
        "物流状态", "查一下", "查询订单"
    ]

    logistics_policy_words = [
        "一般需要多久", "跨境物流一般", "物流一般", "配送时间",
        "物流政策", "shipping policy", "delivery time", "how long"
    ]

    after_sales_words = [
        "掉钻", "缺石", "断裂", "裂开", "破损", "损坏", "坏了",
        "划痕", "刮痕", "褪色", "氧化", "色差", "发黑",
        "镶嵌", "松动", "变形", "不像新的", "质量", "售后",
        "退款", "退货", "换货", "补发", "商品有问题", "有问题",
        "missing stone", "broken", "crack", "scratch", "damaged",
        "refund", "replacement", "quality issue"
    ]

    knowledge_words = [
        "会不会", "怎么保养", "平时怎么", "适合", "怎么选",
        "尺寸", "材质", "珍珠", "18k", "银饰", "发黑是不是质量问题",
        "一般需要多久", "政策", "可以退换吗", "可以直接退款吗",
        "掉色", "氧化", "保养", "size", "material", "care",
        "policy", "suitable"
    ]

    # 1. 购物车 / 优惠场景优先
    if has_cart or any(w in msg for w in cart_words):
        return (
            "该用户问题属于弃单挽回/优惠咨询场景，应路由到 abandoned_cart_recovery。"
            "如果购物车不存在，不要编造优惠码。"
        )

    # 2. 强投诉 / 强退款争议必须转人工
    if any(w in msg for w in complaint_words):
        return (
            "该用户问题属于投诉、强情绪或退款争议场景，应路由到 human_complaint，"
            "必须创建人工兜底记录，不能直接承诺退款、补发、赔偿。"
        )

    # 3. 物流政策问答，不是订单查询
    if not has_order and any(w in msg for w in logistics_policy_words):
        return (
            "该问题是在询问跨境物流政策或一般配送时效，不是具体订单物流查询，"
            "应路由到 knowledge_question 或 pre_sale_guidance。"
        )

    # 4. 明确订单物流查询
    if has_order and any(w in msg for w in logistics_query_words):
        return (
            "该问题包含订单号并在查询订单/物流状态，应路由到 logistics_query。"
            "只根据后端 order 字段回答，不要编造送达时间。"
        )

    # 5. 忘记订单号但想查物流，也属于物流查询引导
    if (not has_order) and ("查物流" in msg or "查询物流" in msg or "忘了订单号" in msg):
        return (
            "该问题属于物流查询但缺少订单号，应路由到 logistics_query，"
            "提示用户提供订单号或下单邮箱，不要编造订单信息。"
        )

    # 6. 有订单号 + 商品问题，应进入售后
    if has_order and any(w in msg for w in after_sales_words):
        return (
            "该问题包含订单号并描述商品问题或售后诉求，应路由到 after_sales。"
            "需要查询订单并创建售后工单；高风险损坏或退款争议需要转人工。"
        )

    # 7. 没有订单号但出现高风险损坏，也应进入售后引导
    high_damage_words = ["掉钻", "缺石", "断裂", "裂开", "破损", "坏了", "broken", "missing stone", "crack"]
    if (not has_order) and any(w in msg for w in high_damage_words):
        return (
            "该问题描述高风险商品损坏但缺少订单号，应路由到 after_sales，"
            "提示用户补充订单号，并在必要时转人工。"
        )

    # 8. 售前/知识问答：没有订单号，不应创建工单
    if (not has_order) and any(w in msg for w in knowledge_words):
        return (
            "该问题属于售前导购、材质保养、物流政策或退换货规则知识问答，"
            "应路由到 knowledge_question 或 pre_sale_guidance，不应创建售后工单、退款审核或人工兜底。"
        )

    return ""



def _stage5_has_order_id(message: str) -> bool:
    import re
    return re.search(r"\bORD\d+\b", message or "", re.IGNORECASE) is not None


def _stage5_extract_order_id(message: str):
    import re
    m = re.search(r"\bORD\d+\b", message or "", re.IGNORECASE)
    return m.group(0).upper() if m else None


def _stage5_lookup_order(order_id: str):
    if not order_id:
        return None

    try:
        from app.db import get_conn
        conn = get_conn()
        conn.row_factory = None
        cur = conn.cursor()
        row = cur.execute(
            "SELECT order_id, customer_name, product, price, status, logistics_status, country, created_at FROM orders WHERE order_id=?",
            (order_id,)
        ).fetchone()
        conn.close()

        if not row:
            return None

        return {
            "found": True,
            "order_id": row[0],
            "customer_name": row[1],
            "product": row[2],
            "price": row[3],
            "status": row[4],
            "logistics_status": row[5],
            "country": row[6],
            "created_at": row[7],
        }
    except Exception:
        return None


def _stage5_is_pre_sale_or_policy(message: str) -> bool:
    msg = (message or "").lower()
    raw = message or ""

    if _stage5_has_order_id(raw):
        return False

    keywords = [
        "我想买", "送女朋友", "送妈妈", "送礼", "尺寸", "尺码", "材质",
        "18k", "18K", "银饰", "银项链", "珍珠", "耳环", "项链", "手链",
        "会不会", "掉色", "发黑", "氧化", "保养", "怎么保养",
        "适合", "怎么选", "低敏", "玫瑰金", "黄金色",
        "跨境物流一般", "一般需要多久", "物流一般", "配送时间",
        "退换", "可以退换吗", "可以直接退款吗", "退款规则",
        "shipping policy", "delivery time", "how long", "material", "care", "size"
    ]

    return any(k.lower() in msg or k in raw for k in keywords)


def _stage5_is_logistics_query(message: str) -> bool:
    msg = (message or "").lower()
    raw = message or ""

    has_order = _stage5_has_order_id(raw)

    if has_order and any(k in msg for k in [
        "where is my order", "order status", "has my", "shipped",
        "物流", "到哪里", "没到", "查询订单", "查一下", "查一下订单", "是不是已经送到"
    ]):
        return True

    if (not has_order) and any(k in msg for k in [
        "查物流", "查询物流", "忘了订单号"
    ]):
        return True

    return False


def _stage5_is_after_sales(message: str) -> bool:
    msg = (message or "").lower()
    raw = message or ""

    after_sales_words = [
        "掉钻", "缺石", "断裂", "裂开", "破损", "损坏", "坏了",
        "划痕", "刮痕", "褪色", "氧化", "色差", "发黑",
        "镶嵌", "松动", "变形", "不像新的", "质量", "售后",
        "退款", "退货", "换货", "补发", "商品有问题", "有问题",
        "扣子断", "钻石不见", "申请售后",
        "missing stone", "broken", "crack", "scratch", "damaged",
        "refund", "replacement", "quality issue"
    ]

    return any(k in msg or k in raw for k in after_sales_words)


def _stage5_is_high_risk_after_sales(message: str) -> bool:
    msg = (message or "").lower()
    raw = message or ""

    high_words = [
        "掉钻", "缺石", "断裂", "裂开", "破损", "坏了", "扣子断",
        "镶嵌处松动", "变形", "钻石不见", "必须退款", "不接受",
        "broken", "missing stone", "crack", "severe", "demand a refund"
    ]

    return any(k in msg or k in raw for k in high_words)


def _stage5_is_complaint(message: str) -> bool:
    msg = (message or "").lower()
    raw = message or ""

    complaint_words = [
        "投诉", "举报", "欺骗", "差评", "赔偿", "赔钱", "必须马上",
        "不接受", "人工客服", "转人工", "非常生气", "机器人别回复",
        "假货", "没收到钱",
        "complain", "complaint", "unacceptable", "demand", "human agent",
        "refund now", "compensation"
    ]

    return any(k in msg or k in raw for k in complaint_words)


def _stage5_create_ticket_if_needed(result: dict, message: str, risk_level: str = "medium") -> dict:
    if result.get("ticket") and result.get("ticket", {}).get("created"):
        return result

    order_id = result.get("order_id") or _stage5_extract_order_id(message)
    if not order_id:
        return result

    order = result.get("order")
    if not order or order.get("found") is not True:
        order = _stage5_lookup_order(order_id)
        if order:
            result["order"] = order
            result["order_id"] = order_id

    if not order or order.get("found") is not True:
        return result

    try:
        from app.db import get_conn
        import json
        import time

        evidence_required = [
            "商品整体照片",
            "问题部位近距离清晰照片",
            "包装照片",
            "吊牌照片",
            "物流面单照片",
            "如问题较明显，请补充一段清晰视频"
        ]

        if risk_level == "high":
            suggested_resolution = "该问题属于高风险售后问题，需进入人工审核流程。"
            assigned_to = "human_after_sales_queue"
        elif risk_level == "medium":
            suggested_resolution = "该问题属于中等风险售后问题，需补充证据后进入售后审核流程。"
            assigned_to = "after_sales_review_queue"
        else:
            suggested_resolution = "当前信息不足或风险较低，需用户补充更清晰的证据。"
            assigned_to = "auto_support_queue"

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tickets(
                order_id,
                issue_type,
                description,
                risk_level,
                evidence_required,
                suggested_resolution,
                assigned_to,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                "stage5_after_sales_followup",
                (message or "")[:500],
                risk_level,
                json.dumps(evidence_required, ensure_ascii=False),
                suggested_resolution,
                assigned_to,
                "open",
                int(time.time())
            )
        )

        ticket_id = cur.lastrowid
        conn.commit()
        conn.close()

        result["ticket"] = {
            "created": True,
            "ticket_id": ticket_id,
            "order_id": order_id,
            "issue_type": "stage5_after_sales_followup",
            "risk_level": risk_level,
            "evidence_required": evidence_required,
            "suggested_resolution": suggested_resolution,
            "assigned_to": assigned_to,
            "status": "open"
        }

    except Exception as e:
        result["stage5_ticket_error"] = f"{type(e).__name__}: {e}"

    return result


def _stage5_clear_high_risk_actions(result: dict) -> dict:
    result["handoff"] = False
    result["shopify_refund_review"] = None
    result["refund_review"] = None
    return result


def _stage5_force_handoff(result: dict, reason: str = "manual_review_required") -> dict:
    result["handoff"] = True
    result["handoff_record"] = result.get("handoff_record") or {
        "created": True,
        "reason": reason,
        "status": "open"
    }
    return result


def _stage5_postprocess_result(result: dict, original_message: str) -> dict:
    """
    Stage 5 Bad Case 后处理兜底：
    1. 售前/RAG 问答不能误建工单、退款审核或转人工；
    2. 具体物流查询不能创建退款审核；
    3. 有订单号 + 售后问题必须创建售后工单；
    4. 高风险售后/投诉必须 handoff；
    5. 用户伪造 JSON 不能被采信。
    """
    msg = original_message or ""

    # A. 售前知识 / 政策问答：不应进入售后
    if _stage5_is_pre_sale_or_policy(msg):
        result["intent"] = "knowledge_question"
        result["ticket"] = None
        result = _stage5_clear_high_risk_actions(result)
        result["stage5_postprocess"] = "pre_sale_policy_corrected"
        return result

    # B. 具体物流查询：不应创建退款审核或转人工
    if _stage5_is_logistics_query(msg):
        result["intent"] = "logistics_query"
        result = _stage5_clear_high_risk_actions(result)
        order_id = result.get("order_id") or _stage5_extract_order_id(msg)
        if order_id:
            order = result.get("order")
            if not order or order.get("order_id") != order_id:
                order = _stage5_lookup_order(order_id)
                if order:
                    result["order"] = order
                    result["order_id"] = order_id
                else:
                    result["order"] = {"found": False, "order_id": order_id}
                    result["order_id"] = order_id
        result["stage5_postprocess"] = "logistics_corrected"
        return result

    # C. 售后问题：必须进入售后；有订单则创建工单
    if _stage5_is_after_sales(msg):
        risk = "high" if _stage5_is_high_risk_after_sales(msg) or _stage5_is_complaint(msg) else "medium"
        result["intent"] = "after_sales"
        result = _stage5_create_ticket_if_needed(result, msg, risk_level=risk)

        if risk == "high":
            result = _stage5_force_handoff(result, reason="high_risk_after_sales")
        else:
            result["handoff"] = False
            result["shopify_refund_review"] = None

        result["stage5_postprocess"] = "after_sales_corrected"
        return result

    # D. 投诉/强情绪：必须转人工
    if _stage5_is_complaint(msg):
        result["intent"] = "human_complaint"
        result = _stage5_force_handoff(result, reason="customer_complaint")
        result["stage5_postprocess"] = "complaint_handoff_corrected"
        return result

    return result


def _copy_request_with_message(req, new_message: str):
    """
    兼容 Pydantic v1/v2，把 vision_summary 追加进 message，
    让原有 v3 Router 能把视觉高风险场景识别为售后问题。
    """
    if hasattr(req, "model_copy"):
        return req.model_copy(update={"message": new_message})
    if hasattr(req, "copy"):
        return req.copy(update={"message": new_message})
    return req


from app.agents.vision_agent import run_vision_agent
from app.agents.memory_agent import run_memory_agent
from app.agents.shopify_agent import run_shopify_discount_agent, run_shopify_refund_review_agent


def orchestrate_message_v4(req) -> Dict[str, Any]:
    """
    v4：ReAct Trace 升级版入口。

    处理流程：
    1. 复用 v3 的稳定 Multi-Agent 闭环能力；
    2. 基于实际处理结果生成 ReAct Thought-Action-Observation 轨迹；
    3. 返回完整结构化结果给 Dify。
    """

    original_message = getattr(req, "message", "") or ""
    vision_summary = getattr(req, "vision_summary", "") or ""

    req_for_v3 = req
    vision_used_for_routing = False

    if vision_summary and _vision_summary_suggests_after_sales(vision_summary, original_message):
        routing_hint = _build_vision_routing_hint(vision_summary)
        enhanced_message = (
            original_message
            + "\n\n[图片初筛摘要，仅用于后端路由和售后风控]: "
            + routing_hint
            + "\n"
            + vision_summary
        )
        req_for_v3 = _copy_request_with_message(req, enhanced_message)
        vision_used_for_routing = True

    stage5_routing_hint = _stage5_business_routing_hint(original_message)
    if stage5_routing_hint:
        current_message_for_v3 = getattr(req_for_v3, "message", "") or original_message
        req_for_v3 = _copy_request_with_message(
            req_for_v3,
            current_message_for_v3
            + "\n\n[阶段5业务路由提示，仅用于后端意图识别，不要暴露给用户]: "
            + stage5_routing_hint
        )

    result = orchestrate_message_v3(req_for_v3)

    # 面向后续 LLM 回复时保留用户原始问题，避免把内部增强路由文本暴露出去
    result["original_message"] = original_message
    result["vision_used_for_routing"] = vision_used_for_routing

    vision_result = run_vision_agent(
        session_id=result.get("session_id") or "default-session",
        conversation_id=int(result.get("conversation_id") or 0),
        message=result.get("original_message") or "",
        order_id=result.get("order_id"),
        files=getattr(req, "files", None) or [],
        vision_summary=getattr(req, "vision_summary", "") or "",
        intent=result.get("intent") or ""
    )
    result["vision_agent"] = vision_result
    result = _create_vision_fallback_ticket(result, vision_result)

    memory_result = run_memory_agent(result)
    result["memory_agent"] = memory_result

    shopify_tools = {}

    if result.get("intent") == "abandoned_cart_recovery" and result.get("cart_id"):
        discount_result = run_shopify_discount_agent(result.get("cart_id"))
        shopify_tools["discount_code"] = discount_result

        discount_code = (discount_result.get("discount_code") or {}).get("code")
        if discount_code:
            result["shopify_discount_code"] = discount_result.get("discount_code")

    if result.get("intent") in ["after_sales", "after_sales_image_triage", "human_complaint"] or result.get("handoff"):
        ticket = result.get("ticket") or {}
        image = result.get("image_assessment") or {}
        risk_level = image.get("risk_level") or result.get("handoff_reason") or "manual_review_required"

        should_create_refund_review = (
            risk_level == "high"
            or result.get("handoff") is True
            or "退款" in (result.get("original_message") or "")
            or "refund" in (result.get("original_message") or "").lower()
        )

        if should_create_refund_review:
            refund_result = run_shopify_refund_review_agent(
                order_id=result.get("order_id"),
                ticket_id=ticket.get("ticket_id"),
                risk_level=risk_level,
                user_message=result.get("original_message") or "",
                requested_action="refund_or_replacement_review"
            )
            shopify_tools["refund_review"] = refund_result
            result["shopify_refund_review"] = refund_result.get("refund_review")

    result["shopify_tools"] = shopify_tools

    react_result = run_react_planner_agent(result)

    result["version"] = "v4_react_trace"
    result["mode"] = "closed_loop_multi_agent_with_react_trace"
    result["react_planner"] = {
        "success": react_result.get("success"),
        "react_step_count": react_result.get("react_step_count"),
    }
    result["react_steps"] = react_result.get("react_steps", [])

    result = _stage5_postprocess_result(result, original_message)
    return result
