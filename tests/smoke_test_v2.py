import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def request_json(method, path, payload=None):
    url = BASE_URL + path
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {path} failed: {e.code}, {body}") from e
    except Exception as e:
        raise RuntimeError(f"{method} {path} failed: {e}") from e


def get(path):
    return request_json("GET", path)


def post(path, payload):
    return request_json("POST", path, payload)


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_health():
    data = get("/health")
    assert_true(data.get("status") == "ok", "health 接口异常")


def test_after_sales_closed_loop():
    data = post("/tools/handle_message_v3", {
        "message": "我的戒指掉钻了，订单号 ORD1001，请帮我处理。",
        "session_id": "test-v2-after-sales",
        "files": [],
    })
    assert_true(data.get("intent") == "after_sales", "售后意图识别失败")
    assert_true(data.get("order", {}).get("found") is True, "订单未查询成功")
    assert_true(data.get("ticket", {}).get("created") is True, "售后工单未创建")
    assert_true(data.get("image_assessment", {}).get("risk_level") == "high", "掉钻应为 high")
    assert_true(data.get("handoff") is True, "高风险售后应转人工")
    assert_true(data.get("handoff_record", {}).get("created") is True, "人工兜底记录未创建")
    assert_true(data.get("task_count", 0) >= 2, "售后闭环任务数量不足")
    assert_true(len(data.get("agent_traces", [])) >= 4, "Agent trace 数量不足")


def test_cart_recovery_closed_loop():
    data = post("/tools/handle_message_v3", {
        "message": "I left CART2001 in my cart. Do you have any discount?",
        "session_id": "test-v2-cart",
        "files": [],
    })
    assert_true(data.get("intent") == "abandoned_cart_recovery", "弃单意图识别失败")
    assert_true(data.get("cart_recovery", {}).get("coupon") == "FREE-SHIPPING", "CART2001 优惠码错误")
    assert_true(data.get("recovery_log", {}).get("created") is True, "弃单挽回记录未创建")
    assert_true(data.get("task_count", 0) >= 1, "弃单转化跟进任务未创建")


def test_complaint_closed_loop():
    data = post("/tools/handle_message_v3", {
        "message": "你们欺骗消费者，我要投诉，订单号 ORD9999。",
        "session_id": "test-v2-complaint",
        "files": [],
    })
    assert_true(data.get("intent") == "human_complaint", "投诉意图识别失败")
    assert_true(data.get("order", {}).get("found") is False, "ORD9999 应不存在")
    assert_true(data.get("handoff") is True, "投诉应转人工")
    assert_true(data.get("handoff_record", {}).get("created") is True, "投诉兜底记录未创建")
    assert_true(data.get("task_count", 0) >= 1, "人工处理任务未创建")


def test_logistics_and_refunded():
    data = post("/tools/handle_message_v3", {
        "message": "Where is my order? My order ID is ORD1002.",
        "session_id": "test-v2-logistics",
        "files": [],
    })
    assert_true(data.get("intent") == "logistics_query", "物流意图识别失败")
    assert_true(data.get("order", {}).get("logistics_status") == "in_transit", "ORD1002 应为 in_transit")

    data2 = post("/tools/handle_message_v3", {
        "message": "我的订单 ORD1003 到哪里了？",
        "session_id": "test-v2-refunded",
        "files": [],
    })
    assert_true(data2.get("order", {}).get("status") == "refunded", "ORD1003 应为 refunded")


def test_observability_endpoints():
    summary = get("/tools/dashboard/summary")
    assert_true("multi_agent" in summary, "dashboard 缺少 multi_agent 指标")
    conversations = get("/tools/conversations")
    assert_true(conversations.get("count", 0) >= 1, "conversations 没有记录")
    traces = get("/tools/agent_traces")
    assert_true(traces.get("count", 0) >= 1, "agent_traces 没有记录")
    tasks = get("/tools/tasks")
    assert_true(tasks.get("count", 0) >= 1, "tasks 没有记录")


TESTS = [
    ("健康检查", test_health),
    ("售后闭环", test_after_sales_closed_loop),
    ("弃单挽回闭环", test_cart_recovery_closed_loop),
    ("订单不存在 + 投诉闭环", test_complaint_closed_loop),
    ("物流在途 + 已退款订单", test_logistics_and_refunded),
    ("可观测性接口", test_observability_endpoints),
]


def main():
    passed = 0
    failed = 0
    print(f"BASE_URL = {BASE_URL}")
    print("开始 JewelryCare AI v2 Multi-Agent Smoke Test...\n")
    for name, fn in TESTS:
        try:
            fn()
            print(f"✅ PASS - {name}")
            passed += 1
        except Exception as e:
            print(f"❌ FAIL - {name}")
            print(f"   原因：{e}")
            failed += 1
    print("\n测试完成")
    print(f"通过：{passed}")
    print(f"失败：{failed}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
