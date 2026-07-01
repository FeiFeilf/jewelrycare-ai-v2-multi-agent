import re
from typing import Any, Dict, Optional


def extract_order_id(message: str) -> Optional[str]:
    match = re.search(r"ORD\d+", message or "", re.IGNORECASE)
    return match.group(0).upper() if match else None


def extract_cart_id(message: str) -> Optional[str]:
    match = re.search(r"CART\d+", message or "", re.IGNORECASE)
    return match.group(0).upper() if match else None


def route_message(message: str, has_image: bool = False) -> Dict[str, Any]:
    text = (message or "").lower()

    complaint_keywords = [
        "complaint", "angry", "scam", "fraud", "bad review",
        "投诉", "欺骗", "骗子", "差评", "生气", "举报", "维权",
        "必须退款", "马上退款", "立刻退款", "不接受", "赔偿",
    ]

    after_sales_keywords = [
        "refund", "return", "broken", "scratch", "damaged", "defect",
        "stone missing", "color fading", "crack", "refund now",
        "划痕", "刮痕", "损坏", "退款", "退货", "坏了", "瑕疵",
        "掉钻", "褪色", "断裂", "破损", "裂开", "色差", "掉色",
    ]

    logistics_keywords = [
        "tracking", "shipment", "delivery", "where is my order", "shipping status",
        "物流", "快递", "到哪", "发货", "追踪", "运输", "送达", "订单到哪里",
    ]

    cart_keywords = [
        "cart", "checkout", "coupon", "discount", "abandoned",
        "购物车", "优惠", "折扣", "下单", "未支付", "优惠码",
    ]

    knowledge_keywords = [
        "material", "size", "sizing", "gift", "recommend", "care",
        "gold", "silver", "pearl", "necklace", "ring", "bracelet",
        "材质", "尺寸", "尺码", "推荐", "适合", "送女朋友", "送礼",
        "保养", "18k", "银", "珍珠", "戒指", "项链", "手链", "耳环",
        "多久发货", "配送多久", "运费", "退换货政策", "退款规则",
    ]

    order_id = extract_order_id(message)
    cart_id = extract_cart_id(message)

    if any(k in text for k in complaint_keywords):
        intent = "human_complaint"
        target_agent = "handoff_agent"
        confidence = 0.94
        next_action = "human_handoff"
    elif any(k in text for k in after_sales_keywords) or has_image:
        intent = "after_sales"
        target_agent = "after_sales_agent"
        confidence = 0.90
        next_action = "order_check_and_after_sales_triage"
    elif any(k in text for k in logistics_keywords):
        intent = "logistics_query"
        target_agent = "order_agent"
        confidence = 0.86
        next_action = "query_order"
    elif any(k in text for k in cart_keywords):
        intent = "abandoned_cart_recovery"
        target_agent = "recovery_agent"
        confidence = 0.83
        next_action = "recover_abandoned_cart"
    elif any(k in text for k in knowledge_keywords):
        intent = "knowledge_question"
        target_agent = "knowledge_agent"
        confidence = 0.78
        next_action = "answer_with_rag_knowledge"
    else:
        intent = "general_consultation"
        target_agent = "knowledge_agent"
        confidence = 0.60
        next_action = "general_customer_service_reply"

    return {
        "agent": "router_agent",
        "intent": intent,
        "target_agent": target_agent,
        "confidence": confidence,
        "next_action": next_action,
        "order_id": order_id,
        "cart_id": cart_id,
        "need_handoff": intent == "human_complaint",
    }
