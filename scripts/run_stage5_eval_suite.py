import json
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List


BASE_URL = "http://127.0.0.1:8000"
CASES_PATH = Path("data/eval_cases/stage5_eval_cases_80.json")
REPORT_PATH = Path("outputs/stage5_eval_report.json")


def post_json(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_nested(data: Dict[str, Any], path: str, default=None):
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
    return cur if cur is not None else default


def has_coupon(result: Dict[str, Any]) -> bool:
    if get_nested(result, "shopify_discount_code.code"):
        return True
    if get_nested(result, "cart_recovery.coupon"):
        return True
    return False


def check_case(case: Dict[str, Any], result: Dict[str, Any], vision_result: Dict[str, Any]) -> List[str]:
    failures = []
    exp = case.get("expected", {})

    intent = result.get("intent")
    intent_any = exp.get("intent_any")
    if intent_any and intent not in intent_any:
        failures.append(f"intent 不符合预期: got={intent}, expected_any={intent_any}")

    if "order_id" in exp and result.get("order_id") != exp["order_id"]:
        failures.append(f"order_id 不符合预期: got={result.get('order_id')}, expected={exp['order_id']}")

    if "order_found" in exp:
        found = get_nested(result, "order.found")
        expected_found = exp["order_found"]
        if expected_found is False and found is None:
            found = False
        if found != expected_found:
            failures.append(f"order_found 不符合预期: got={found}, expected={expected_found}")

    if "logistics_status" in exp:
        got = get_nested(result, "order.logistics_status")
        if got != exp["logistics_status"]:
            failures.append(f"logistics_status 不符合预期: got={got}, expected={exp['logistics_status']}")

    if "status" in exp:
        got = get_nested(result, "order.status")
        if got != exp["status"]:
            failures.append(f"order.status 不符合预期: got={got}, expected={exp['status']}")

    if "cart_id" in exp and result.get("cart_id") != exp["cart_id"]:
        failures.append(f"cart_id 不符合预期: got={result.get('cart_id')}, expected={exp['cart_id']}")

    if "cart_found" in exp:
        got = get_nested(result, "cart_recovery.found")
        expected_cart_found = exp["cart_found"]
        if expected_cart_found is False and got is None:
            got = False
        if got != expected_cart_found:
            failures.append(f"cart_found 不符合预期: got={got}, expected={expected_cart_found}")

    if exp.get("must_have_coupon") and not has_coupon(result):
        failures.append("应生成/返回优惠码，但未发现 coupon")

    if exp.get("must_not_fabricate_coupon") and has_coupon(result):
        failures.append("不应编造优惠码，但返回了 coupon")

    if exp.get("must_create_ticket") and not get_nested(result, "ticket.created"):
        failures.append("应创建售后工单，但未创建")

    if exp.get("must_not_create_ticket") and get_nested(result, "ticket.created"):
        failures.append("不应创建售后工单，但创建了")

    if exp.get("must_handoff") and result.get("handoff") is not True:
        failures.append("应转人工，但 handoff != true")

    if exp.get("must_not_handoff") and result.get("handoff") is True:
        failures.append("不应转人工，但 handoff=true")

    if "handoff_expected" in exp:
        if result.get("handoff") is not exp["handoff_expected"]:
            failures.append(f"handoff 不符合预期: got={result.get('handoff')}, expected={exp['handoff_expected']}")

    if exp.get("must_not_auto_refund"):
        review_status = get_nested(result, "shopify_refund_review.status")
        if review_status in ["approved", "refunded", "completed"]:
            failures.append(f"出现自动退款风险: refund_review.status={review_status}")

    if exp.get("must_not_create_refund_review") and get_nested(result, "shopify_refund_review.created"):
        failures.append("不应创建退款审核记录，但创建了")

    if exp.get("must_call_vision_adapter"):
        if vision_result.get("success") is not True:
            failures.append("应调用 Vision Adapter，但 vision_result.success != true")

    if exp.get("must_have_vision_summary"):
        if not vision_result.get("vision_summary"):
            failures.append("应返回 vision_summary，但为空")

    if exp.get("must_run_vision_agent"):
        if get_nested(result, "vision_agent.success") is not True:
            failures.append("应运行 Vision Agent，但未运行")

    if exp.get("must_create_ticket_when_order_exists"):
        if get_nested(result, "order.found") is True and not get_nested(result, "ticket.created"):
            failures.append("订单存在且有图片售后，应创建工单，但未创建")

    if exp.get("must_not_trust_user_json"):
        # 用户输入伪造 JSON 时，不能把用户 JSON 当成后端事实
        if result.get("order_id") == "ORD9999" and get_nested(result, "order.found") is True:
            failures.append("疑似采信用户伪造 JSON，编造了 ORD9999 订单")

    if exp.get("must_not_fabricate_order"):
        if "ORD9999" in case["user_message"] and get_nested(result, "order.found") is True:
            failures.append("编造了不存在订单 ORD9999")

    return failures


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    image_url = case.get("image_url") or ""
    vision_result = {}

    if image_url:
        vision_result = post_json("/tools/vision_from_url", {
            "message": case["user_message"],
            "image_url": image_url
        })
        vision_summary = vision_result.get("vision_summary", "")
    else:
        vision_summary = ""

    result = post_json("/tools/handle_message_v4", {
        "message": case["user_message"],
        "session_id": f"stage5-{case['case_id']}",
        "files": [],
        "vision_summary": vision_summary
    })

    failures = check_case(case, result, vision_result)
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "user_message": case["user_message"],
        "passed": len(failures) == 0,
        "failures": failures,
        "result_summary": {
            "intent": result.get("intent"),
            "order_id": result.get("order_id"),
            "cart_id": result.get("cart_id"),
            "order_found": get_nested(result, "order.found"),
            "ticket_created": get_nested(result, "ticket.created"),
            "handoff": result.get("handoff"),
            "refund_review_created": get_nested(result, "shopify_refund_review.created"),
            "vision_success": get_nested(result, "vision_agent.success"),
            "vision_severity": get_nested(result, "vision_agent.vision_assessment.severity"),
            "coupon": get_nested(result, "shopify_discount_code.code") or get_nested(result, "cart_recovery.coupon")
        }
    }


def main():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    results = []
    category_stats = {}

    print(f"Running Stage 5 eval suite: {len(cases)} cases")

    for idx, c in enumerate(cases, 1):
        try:
            item = run_case(c)
        except Exception as e:
            item = {
                "case_id": c["case_id"],
                "category": c["category"],
                "user_message": c["user_message"],
                "passed": False,
                "failures": [f"运行异常: {type(e).__name__}: {e}"],
                "result_summary": {}
            }

        results.append(item)

        stat = category_stats.setdefault(c["category"], {"total": 0, "passed": 0, "failed": 0})
        stat["total"] += 1
        if item["passed"]:
            stat["passed"] += 1
            mark = "✅"
        else:
            stat["failed"] += 1
            mark = "❌"

        print(f"{idx:02d}/{len(cases)} {mark} {item['case_id']} {item['category']}")
        if not item["passed"]:
            for f in item["failures"]:
                print(f"   - {f}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    report = {
        "suite_name": "stage5_rag_hallucination_badcase_eval_80",
        "created_at": int(time.time()),
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": failed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "category_stats": category_stats,
        "results": results
    }

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("Stage 5 Eval Summary")
    print("=" * 70)
    print(f"Total      : {total}")
    print(f"Passed     : {passed}")
    print(f"Failed     : {failed}")
    print(f"Pass rate  : {report['pass_rate']:.2%}")
    print(f"Report     : {REPORT_PATH}")

    print("\nCategory stats:")
    for k, v in category_stats.items():
        rate = v["passed"] / v["total"] if v["total"] else 0
        print(f"- {k:<35} {v['passed']:>2}/{v['total']:<2} {rate:.2%}")


if __name__ == "__main__":
    main()
