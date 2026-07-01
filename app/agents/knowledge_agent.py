from typing import Any, Dict


def run_knowledge_agent(message: str) -> Dict[str, Any]:
    return {
        "agent": "knowledge_agent",
        "success": True,
        "knowledge_scope": [
            "material_guidance",
            "care_policy",
            "return_exchange_policy",
            "shipping_policy",
            "refund_rule",
        ],
        "rag_instruction": (
            "Use Dify RAG knowledge base to answer jewelry material, care, shipping, "
            "return/exchange and refund-rule questions. Do not fabricate order status, "
            "refund result, coupon, ticket id or logistics status."
        ),
        "response_policy": (
            "For refund, replacement or compensation questions, do not make direct promises. "
            "Guide the user to after-sales review or human support when necessary."
        ),
    }
