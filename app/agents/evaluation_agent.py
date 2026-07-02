from typing import Any, Callable, Dict, List

from app.tools.evaluation_tool import save_bad_case, save_evaluation_result


DEFAULT_EVALUATION_CASES = [
    {
        "case_id": "EVAL-001",
        "case_name": "订单存在高风险售后",
        "message": "我的戒指掉钻了，订单号 ORD1001，可以退款吗？",
        "session_id": "eval-after-sales-high",
        "expected": {
            "intent": "after_sales",
            "order_found": True,
            "handoff": True,
            "refund_review": True
        }
    },
    {
        "case_id": "EVAL-002",
        "case_name": "订单不存在投诉",
        "message": "你们欺骗消费者，我要投诉，订单号 ORD9999。",
        "session_id": "eval-complaint-not-found",
        "expected": {
            "intent": "human_complaint",
            "order_found": False,
            "handoff": True
        }
    },
    {
        "case_id": "EVAL-003",
        "case_name": "物流在途",
        "message": "Where is my order? My order ID is ORD1002.",
        "session_id": "eval-logistics",
        "expected": {
            "intent": "logistics_query",
            "order_found": True,
            "logistics_status": "in_transit"
        }
    },
    {
        "case_id": "EVAL-004",
        "case_name": "弃单优惠",
        "message": "I left CART2001 in my cart. Do you have any discount?",
        "session_id": "eval-cart",
        "expected": {
            "intent": "abandoned_cart_recovery",
            "discount_code": True
        }
    },
    {
        "case_id": "EVAL-005",
        "case_name": "已退款订单",
        "message": "我的订单 ORD1003 到哪里了？",
        "session_id": "eval-refunded",
        "expected": {
            "order_found": True,
            "order_status": "refunded"
        }
    },
]


def _make_request(request_cls, message: str, session_id: str):
    return request_cls(
        message=message,
        session_id=session_id,
        files=[],
        vision_summary=""
    )


def evaluate_case_output(case: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
    expected = case.get("expected") or {}
    failures = []

    order = output.get("order") or {}

    if "intent" in expected and output.get("intent") != expected["intent"]:
        failures.append(f"intent expected {expected['intent']} but got {output.get('intent')}")

    if "order_found" in expected and order.get("found") is not expected["order_found"]:
        failures.append(f"order_found expected {expected['order_found']} but got {order.get('found')}")

    if "handoff" in expected and output.get("handoff") is not expected["handoff"]:
        failures.append(f"handoff expected {expected['handoff']} but got {output.get('handoff')}")

    if "logistics_status" in expected and order.get("logistics_status") != expected["logistics_status"]:
        failures.append(f"logistics_status expected {expected['logistics_status']} but got {order.get('logistics_status')}")

    if "order_status" in expected and order.get("status") != expected["order_status"]:
        failures.append(f"order_status expected {expected['order_status']} but got {order.get('status')}")

    if expected.get("discount_code") and not output.get("shopify_discount_code"):
        failures.append("expected shopify_discount_code but missing")

    if expected.get("refund_review") and not output.get("shopify_refund_review"):
        failures.append("expected shopify_refund_review but missing")

    if output.get("intent") == "human_complaint" and not output.get("handoff"):
        failures.append("complaint case should be handed off")

    if ((output.get("image_assessment") or {}).get("risk_level") == "high") and not output.get("handoff"):
        failures.append("high-risk after-sales case should be handed off")

    return {
        "passed": len(failures) == 0,
        "failures": failures
    }


def run_evaluation_suite(orchestrate_func: Callable, request_cls) -> Dict[str, Any]:
    case_results = []

    hallucination_risk_count = 0
    refund_promise_violation_count = 0
    handoff_missing_count = 0

    passed = 0
    failed = 0

    for case in DEFAULT_EVALUATION_CASES:
        req = _make_request(
            request_cls=request_cls,
            message=case["message"],
            session_id=case["session_id"]
        )

        output = orchestrate_func(req)
        eval_result = evaluate_case_output(case, output)

        if eval_result["passed"]:
            passed += 1
        else:
            failed += 1
            save_bad_case(
                case_id=case["case_id"],
                case_name=case["case_name"],
                user_message=case["message"],
                failure_type="rule_check_failed",
                detail="; ".join(eval_result["failures"]),
                severity="high" if output.get("handoff") is False else "medium"
            )

        if case["case_name"].find("投诉") >= 0 and not output.get("handoff"):
            handoff_missing_count += 1

        if output.get("shopify_refund_review") and output.get("shopify_refund_review", {}).get("status") == "approved":
            refund_promise_violation_count += 1

        if (output.get("order") or {}).get("found") is False and (output.get("order") or {}).get("product"):
            hallucination_risk_count += 1

        case_results.append({
            "case_id": case["case_id"],
            "case_name": case["case_name"],
            "passed": eval_result["passed"],
            "failures": eval_result["failures"],
            "intent": output.get("intent"),
            "handoff": output.get("handoff"),
            "react_step_count": (output.get("react_planner") or {}).get("react_step_count"),
            "has_discount_code": bool(output.get("shopify_discount_code")),
            "has_refund_review": bool(output.get("shopify_refund_review"))
        })

    total = len(DEFAULT_EVALUATION_CASES)

    metrics = {
        "hallucination_risk_count": hallucination_risk_count,
        "refund_promise_violation_count": refund_promise_violation_count,
        "handoff_missing_count": handoff_missing_count,
        "hallucination_risk_rate": round(hallucination_risk_count / total, 4) if total else 0,
        "refund_promise_violation_rate": round(refund_promise_violation_count / total, 4) if total else 0,
        "handoff_missing_rate": round(handoff_missing_count / total, 4) if total else 0
    }

    saved = save_evaluation_result(
        suite_name="jewelrycare_v4_rag_bad_case_eval",
        total_cases=total,
        passed_cases=passed,
        failed_cases=failed,
        metrics=metrics
    )

    return {
        "agent": "evaluation_agent",
        "success": True,
        "evaluation_result": saved,
        "case_results": case_results
    }
