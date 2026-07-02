import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional


BASE_URL = "http://127.0.0.1:8000"


def request_json(method: str, path: str, payload: Optional[Dict[str, Any]] = None):
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get(path: str):
    return request_json("GET", path)


def post(path: str, payload: Dict[str, Any]):
    return request_json("POST", path, payload)


def print_title(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_kv(key: str, value: Any):
    print(f"{key:<28}: {value}")


def mark(ok: bool) -> str:
    return "✅" if ok else "❌"


def check_items(items):
    passed = 0
    for name, ok in items:
        print(f"{mark(ok)} {name}")
        if ok:
            passed += 1
    print(f"通过 {passed}/{len(items)} 项")
    return passed


def test_mock_order():
    print_title("1. Mock Shopify 订单查询")
    data = get("/mock_shopify/orders/ORD1001")
    order = data.get("order") or {}

    print_kv("tool", data.get("tool"))
    print_kv("source", data.get("source"))
    print_kv("found", data.get("found"))
    print_kv("order_id", order.get("order_id"))
    print_kv("product", order.get("product"))
    print_kv("status", order.get("status"))
    print_kv("logistics_status", order.get("logistics_status"))

    return check_items([
        ("工具名正确", data.get("tool") == "mock_shopify.get_order"),
        ("订单查询成功", data.get("found") is True),
        ("订单号正确", order.get("order_id") == "ORD1001"),
    ])


def test_mock_cart():
    print_title("2. Mock Shopify 购物车查询")
    data = get("/mock_shopify/carts/CART2001")
    cart = data.get("cart") or {}

    print_kv("tool", data.get("tool"))
    print_kv("source", data.get("source"))
    print_kv("found", data.get("found"))
    print_kv("cart_id", cart.get("cart_id"))
    print_kv("product", cart.get("product"))
    print_kv("status", cart.get("status"))
    print_kv("last_active_minutes", cart.get("last_active_minutes"))

    return check_items([
        ("工具名正确", data.get("tool") == "mock_shopify.get_cart"),
        ("购物车查询成功", data.get("found") is True),
        ("购物车编号正确", cart.get("cart_id") == "CART2001"),
    ])


def test_v4_cart_discount():
    print_title("3. v4 弃单挽回触发 Mock Shopify 优惠码")

    data = post("/tools/handle_message_v4", {
        "message": "I left CART2001 in my cart. Do you have any discount?",
        "session_id": "check-shopify-cart",
        "files": [],
        "vision_summary": ""
    })

    discount = data.get("shopify_discount_code") or {}
    shopify_tools = data.get("shopify_tools") or {}

    print_kv("intent", data.get("intent"))
    print_kv("cart_id", data.get("cart_id"))
    print_kv("discount_created", discount.get("created"))
    print_kv("discount_id", discount.get("discount_id"))
    print_kv("discount_code", discount.get("code"))
    print_kv("discount_status", discount.get("status"))
    print_kv("shopify_tools_keys", list(shopify_tools.keys()))
    print_kv("react_step_count", (data.get("react_planner") or {}).get("react_step_count"))

    print("\n--- ReAct Shopify Steps ---")
    for step in data.get("react_steps", []):
        if "ShopifyMockTool" in str(step.get("action")):
            print(f"Step {step.get('step_index')} | {step.get('action')}")
            print(f"Thought: {step.get('thought')}")
            print(f"Observation: {step.get('observation')}")

    return check_items([
        ("intent = abandoned_cart_recovery", data.get("intent") == "abandoned_cart_recovery"),
        ("shopify_discount_code 已创建", discount.get("created") is True),
        ("优惠码存在", bool(discount.get("code"))),
        ("ReAct 中包含 ShopifyMockTool", any("ShopifyMockTool" in str(s.get("action")) for s in data.get("react_steps", []))),
    ])


def test_v4_after_sales_refund_review():
    print_title("4. v4 高风险售后触发 Mock Shopify 退款审核")

    data = post("/tools/handle_message_v4", {
        "message": "我的戒指掉钻了，订单号 ORD1001，可以退款吗？",
        "session_id": "check-shopify-refund",
        "files": [],
        "vision_summary": ""
    })

    review = data.get("shopify_refund_review") or {}
    ticket = data.get("ticket") or {}
    image = data.get("image_assessment") or {}
    shopify_tools = data.get("shopify_tools") or {}

    print_kv("intent", data.get("intent"))
    print_kv("order_id", data.get("order_id"))
    print_kv("risk_level", image.get("risk_level"))
    print_kv("ticket_id", ticket.get("ticket_id"))
    print_kv("refund_review_created", review.get("created"))
    print_kv("review_id", review.get("review_id"))
    print_kv("review_status", review.get("status"))
    print_kv("business_rule", review.get("business_rule"))
    print_kv("shopify_tools_keys", list(shopify_tools.keys()))
    print_kv("react_step_count", (data.get("react_planner") or {}).get("react_step_count"))

    print("\n--- ReAct Shopify Steps ---")
    for step in data.get("react_steps", []):
        if "ShopifyMockTool" in str(step.get("action")):
            print(f"Step {step.get('step_index')} | {step.get('action')}")
            print(f"Thought: {step.get('thought')}")
            print(f"Observation: {step.get('observation')}")

    return check_items([
        ("intent = after_sales", data.get("intent") == "after_sales"),
        ("风险等级为 high", image.get("risk_level") == "high"),
        ("售后工单已创建", ticket.get("created") is True),
        ("shopify_refund_review 已创建", review.get("created") is True),
        ("退款审核状态为 pending_review", review.get("status") == "pending_review"),
        ("ReAct 中包含 ShopifyMockTool", any("ShopifyMockTool" in str(s.get("action")) for s in data.get("react_steps", []))),
    ])


def test_records():
    print_title("5. Shopify Mock 记录验证")

    discounts = get("/tools/discount_codes")
    reviews = get("/tools/refund_reviews")

    print_kv("discount_codes.count", discounts.get("count"))
    print_kv("refund_reviews.count", reviews.get("count"))

    latest_discount = (discounts.get("discount_codes") or [{}])[0]
    latest_review = (reviews.get("refund_reviews") or [{}])[0]

    print_kv("latest_discount_code", latest_discount.get("code"))
    print_kv("latest_discount_status", latest_discount.get("status"))
    print_kv("latest_review_id", latest_review.get("review_id"))
    print_kv("latest_review_status", latest_review.get("status"))

    return check_items([
        ("discount_codes 有记录", (discounts.get("count") or 0) > 0),
        ("refund_reviews 有记录", (reviews.get("count") or 0) > 0),
    ])


def main():
    tests = [
        test_mock_order,
        test_mock_cart,
        test_v4_cart_discount,
        test_v4_after_sales_refund_review,
        test_records,
    ]

    for fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"\n❌ 测试失败：{fn.__name__}")
            print(type(e).__name__, e)

    print_title("最终结论")
    print("如果以上核心检查均为 ✅，说明任务 2：模拟 Shopify 后台工具链已经跑通。")


if __name__ == "__main__":
    main()
