import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


BASE_URL = "http://127.0.0.1:8000"


def request_json(method: str, path: str, payload: Optional[Dict[str, Any]] = None):
    url = BASE_URL + path
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def get(path: str):
    return request_json("GET", path)


def post(path: str, payload: Dict[str, Any]):
    return request_json("POST", path, payload)


def mark(ok: bool) -> str:
    return "✅" if ok else "❌"


def short(value: Any, max_len: int = 160) -> str:
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= max_len else text[:max_len] + "..."


def print_title(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_kv(key: str, value: Any):
    print(f"{key:<24}: {value}")


def check_items(items: List[tuple]) -> int:
    passed = 0
    for name, ok in items:
        print(f"{mark(ok)} {name}")
        if ok:
            passed += 1
    print(f"通过 {passed}/{len(items)} 项")
    return passed


def summarize_v4_response(data: Dict[str, Any]):
    order = data.get("order") or {}
    ticket = data.get("ticket") or {}
    image = data.get("image_assessment") or {}
    recovery = data.get("cart_recovery") or {}
    recovery_log = data.get("recovery_log") or {}
    handoff_record = data.get("handoff_record") or {}
    react = data.get("react_planner") or {}

    print_kv("version", data.get("version"))
    print_kv("mode", data.get("mode"))
    print_kv("intent", data.get("intent"))
    print_kv("target_agent", data.get("target_agent"))
    print_kv("order_id", data.get("order_id"))
    print_kv("cart_id", data.get("cart_id"))

    if order:
        print_kv("order_found", order.get("found"))
        print_kv("order_status", order.get("status"))
        print_kv("logistics_status", order.get("logistics_status"))
        print_kv("product", order.get("product"))

    if image:
        print_kv("risk_level", image.get("risk_level"))
        print_kv("defect_type", image.get("defect_type"))

    if ticket:
        print_kv("ticket_created", ticket.get("created"))
        print_kv("ticket_id", ticket.get("ticket_id"))
        print_kv("ticket_status", ticket.get("status"))

    if recovery:
        print_kv("cart_found", recovery.get("found"))
        print_kv("coupon", recovery.get("coupon"))
        print_kv("strategy", recovery.get("strategy"))

    if recovery_log:
        print_kv("recovery_log_created", recovery_log.get("created"))
        print_kv("log_id", recovery_log.get("log_id"))

    print_kv("handoff", data.get("handoff"))
    print_kv("handoff_reason", data.get("handoff_reason"))

    if handoff_record:
        print_kv("handoff_created", handoff_record.get("created"))
        print_kv("handoff_id", handoff_record.get("handoff_id"))

    print_kv("task_count", data.get("task_count"))
    print_kv("react_step_count", react.get("react_step_count"))


def summarize_react_steps(data: Dict[str, Any]):
    steps = data.get("react_steps") or []

    print("\n--- ReAct Steps 摘要 ---")
    if not steps:
        print("(empty)")
        return

    for step in steps:
        print(f"{step.get('step_index')}. {step.get('action')} | success={step.get('success')}")
        print(f"   Thought: {step.get('thought')}")
        obs = step.get("observation")
        if isinstance(obs, dict):
            print(f"   Observation: {short(obs, 140)}")
        else:
            print(f"   Observation: {obs}")


def test_health():
    print_title("1. 健康检查")
    data = get("/health")
    print_kv("status", data.get("status"))
    print_kv("service", data.get("service"))
    print_kv("version", data.get("version"))
    return check_items([
        ("服务状态为 ok", data.get("status") == "ok"),
        ("服务名为 customer-tools", data.get("service") == "customer-tools"),
    ])


def test_after_sales_v4():
    print_title("2. v4 高风险售后 ReAct 闭环")

    data = post("/tools/handle_message_v4", {
        "message": "我的戒指掉钻了，订单号 ORD1001，请帮我处理。",
        "session_id": "e2e-v4-after-sales",
        "files": [],
        "vision_summary": ""
    })

    summarize_v4_response(data)
    summarize_react_steps(data)

    ticket = data.get("ticket") or {}
    image = data.get("image_assessment") or {}
    react = data.get("react_planner") or {}

    return check_items([
        ("version = v4_react_trace", data.get("version") == "v4_react_trace"),
        ("mode = closed_loop_multi_agent_with_react_trace", data.get("mode") == "closed_loop_multi_agent_with_react_trace"),
        ("intent = after_sales", data.get("intent") == "after_sales"),
        ("订单 ORD1001 查询成功", (data.get("order") or {}).get("found") is True),
        ("风险等级为 high", image.get("risk_level") == "high"),
        ("售后工单已创建", ticket.get("created") is True),
        ("handoff = true", data.get("handoff") is True),
        ("任务已创建", (data.get("task_count") or 0) > 0),
        ("ReAct 轨迹已创建", react.get("success") is True and (react.get("react_step_count") or 0) > 0),
    ])


def test_cart_recovery_v4():
    print_title("3. 弃单优惠闭环")

    data = post("/tools/handle_message_v4", {
        "message": "I left CART2001 in my cart. Do you have any discount?",
        "session_id": "e2e-v4-cart",
        "files": [],
        "vision_summary": ""
    })

    summarize_v4_response(data)
    summarize_react_steps(data)

    recovery = data.get("cart_recovery") or {}
    log = data.get("recovery_log") or {}

    return check_items([
        ("intent = abandoned_cart_recovery", data.get("intent") == "abandoned_cart_recovery"),
        ("购物车 CART2001 查询成功", recovery.get("found") is True),
        ("优惠码为 FREE-SHIPPING", recovery.get("coupon") == "FREE-SHIPPING"),
        ("弃单触达记录已创建", log.get("created") is True),
        ("任务已创建", (data.get("task_count") or 0) > 0),
        ("ReAct 轨迹已创建", len(data.get("react_steps") or []) > 0),
    ])


def test_complaint_order_not_found_v4():
    print_title("4. 订单不存在 + 投诉闭环")

    data = post("/tools/handle_message_v4", {
        "message": "你们欺骗消费者，我要投诉，订单号 ORD9999。",
        "session_id": "e2e-v4-complaint",
        "files": [],
        "vision_summary": ""
    })

    summarize_v4_response(data)
    summarize_react_steps(data)

    order = data.get("order") or {}
    handoff_record = data.get("handoff_record") or {}

    return check_items([
        ("intent = human_complaint", data.get("intent") == "human_complaint"),
        ("订单 ORD9999 未找到", order.get("found") is False),
        ("handoff = true", data.get("handoff") is True),
        ("人工兜底记录已创建", handoff_record.get("created") is True),
        ("任务已创建", (data.get("task_count") or 0) > 0),
        ("ReAct 轨迹已创建", len(data.get("react_steps") or []) > 0),
    ])


def test_logistics_in_transit_v4():
    print_title("5. 物流在途订单")

    data = post("/tools/handle_message_v4", {
        "message": "Where is my order? My order ID is ORD1002.",
        "session_id": "e2e-v4-logistics",
        "files": [],
        "vision_summary": ""
    })

    summarize_v4_response(data)
    summarize_react_steps(data)

    order = data.get("order") or {}

    return check_items([
        ("intent = logistics_query", data.get("intent") == "logistics_query"),
        ("订单 ORD1002 查询成功", order.get("found") is True),
        ("订单状态为 paid", order.get("status") == "paid"),
        ("物流状态为 in_transit", order.get("logistics_status") == "in_transit"),
        ("ReAct 轨迹已创建", len(data.get("react_steps") or []) > 0),
    ])


def test_refunded_order_v4():
    print_title("6. 已退款订单")

    data = post("/tools/handle_message_v4", {
        "message": "我的订单 ORD1003 到哪里了？",
        "session_id": "e2e-v4-refunded",
        "files": [],
        "vision_summary": ""
    })

    summarize_v4_response(data)
    summarize_react_steps(data)

    order = data.get("order") or {}

    return check_items([
        ("订单 ORD1003 查询成功", order.get("found") is True),
        ("订单状态为 refunded", order.get("status") == "refunded"),
        ("物流状态为 delivered", order.get("logistics_status") == "delivered"),
        ("ReAct 轨迹已创建", len(data.get("react_steps") or []) > 0),
    ])


def test_backend_records():
    print_title("7. 后端闭环记录验证")

    react_steps = get("/tools/react_steps")
    traces = get("/tools/agent_traces")
    tasks = get("/tools/tasks")
    dashboard = get("/tools/dashboard/summary")

    print_kv("react_steps.count", react_steps.get("count"))
    print_kv("agent_traces.count", traces.get("count"))
    print_kv("tasks.count", tasks.get("count"))
    print_kv("dashboard.product", dashboard.get("product"))

    multi_agent = dashboard.get("multi_agent") or {}
    print_kv("dashboard.total_conversations", multi_agent.get("total_conversations"))
    print_kv("dashboard.total_agent_traces", multi_agent.get("total_agent_traces"))
    print_kv("dashboard.total_tasks", multi_agent.get("total_tasks"))

    return check_items([
        ("react_steps 有记录", (react_steps.get("count") or 0) > 0),
        ("agent_traces 有记录", (traces.get("count") or 0) > 0),
        ("tasks 有记录", (tasks.get("count") or 0) > 0),
        ("dashboard 可访问", dashboard.get("product") in ["JewelryCare AI v2", "JewelryCare AI"]),
    ])


def main():
    tests = [
        test_health,
        test_after_sales_v4,
        test_cart_recovery_v4,
        test_complaint_order_not_found_v4,
        test_logistics_in_transit_v4,
        test_refunded_order_v4,
        test_backend_records,
    ]

    total_passed = 0
    total_checks = 0

    for fn in tests:
        try:
            before_print = fn()
            total_passed += before_print
            # 无法直接知道每个函数检查总数，这里在最后给场景级通过即可
        except Exception as e:
            print(f"\n❌ 测试函数执行失败：{fn.__name__}")
            print(type(e).__name__, e)

    print_title("最终结论")
    print("如果以上各场景关键检查均为 ✅，说明 v4 ReAct Multi-Agent 端到端闭环测试通过。")
    print("该脚本可用于后续阶段测试、截图、报告整理和面试演示。")


if __name__ == "__main__":
    main()
