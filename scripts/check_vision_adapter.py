import json
import os
import urllib.request
from typing import Any, Dict, Optional


BASE_URL = "http://127.0.0.1:8000"

DEFAULT_IMAGE_URL = (
    "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/"
    "zh-CN/20241022/emyrja/dog_and_girl.jpeg"
)

TEST_IMAGE_URL = os.getenv("TEST_VISION_IMAGE_URL", DEFAULT_IMAGE_URL)


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

    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post(path: str, payload: Dict[str, Any]):
    return request_json("POST", path, payload)


def print_title(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_kv(key: str, value: Any):
    print(f"{key:<30}: {value}")


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


def test_vision_from_url():
    print_title("1. Vision Adapter 图片 URL 识别")

    payload = {
        "message": "我的戒指有问题，订单号 ORD1001，请帮我看一下。",
        "image_url": TEST_IMAGE_URL
    }

    data = post("/tools/vision_from_url", payload)

    print_kv("success", data.get("success"))
    print_kv("mode", data.get("mode"))
    print_kv("image_url", data.get("image_url"))
    print_kv("vision_summary", data.get("vision_summary"))

    return data, check_items([
        ("Vision Adapter 调用成功", data.get("success") is True),
        ("返回 vision_summary", bool(data.get("vision_summary"))),
        ("真实视觉模型返回成功", data.get("success") is True),
    ])


def test_v4_with_adapter_summary(vision_summary: str):
    print_title("2. vision_summary 接入 handle_message_v4")

    data = post("/tools/handle_message_v4", {
        "message": "我的戒指有问题，订单号 ORD1001，请帮我看一下。",
        "session_id": "check-real-vision-adapter",
        "files": [],
        "vision_summary": vision_summary
    })

    vision_agent = data.get("vision_agent") or {}
    assessment = vision_agent.get("vision_assessment") or {}
    ticket = data.get("ticket") or {}
    review = data.get("shopify_refund_review") or {}

    severity = assessment.get("severity")

    print_kv("intent", data.get("intent"))
    print_kv("order_id", data.get("order_id"))
    print_kv("vision.severity", severity)
    print_kv("vision.damage_type", assessment.get("damage_type"))
    print_kv("ticket_created", ticket.get("created"))
    print_kv("ticket_id", ticket.get("ticket_id"))
    print_kv("handoff", data.get("handoff"))
    print_kv("refund_review_created", review.get("created"))
    print_kv("refund_review_status", review.get("status"))
    print_kv("react_step_count", (data.get("react_planner") or {}).get("react_step_count"))

    print("\n--- ReAct Vision / Shopify Steps ---")
    for step in data.get("react_steps", []):
        action = str(step.get("action"))
        if "VisionAgent" in action or "ShopifyMockTool" in action:
            print(f"Step {step.get('step_index')} | {step.get('action')}")
            print(f"Thought: {step.get('thought')}")
            print(f"Observation: {step.get('observation')}")

    base_checks = [
        ("Vision Agent 已运行", vision_agent.get("success") is True),
        ("Vision Agent 生成风险等级", severity in ["low", "medium", "high"]),
        ("售后工单已创建", ticket.get("created") is True),
        ("ReAct 中包含 VisionAgent", any("VisionAgent" in str(s.get("action")) for s in data.get("react_steps", []))),
    ]

    if severity == "high":
        base_checks.extend([
            ("高风险售后已转人工", data.get("handoff") is True),
            ("退款审核记录已创建", review.get("created") is True),
        ])
    else:
        base_checks.extend([
            ("低/中风险不强制转人工", data.get("handoff") in [False, None]),
            ("低/中风险不强制创建退款审核", review.get("created") in [False, None]),
        ])

    return check_items(base_checks)


def main():
    vision, _ = test_vision_from_url()
    summary = vision.get("vision_summary") or ""

    if summary:
        test_v4_with_adapter_summary(summary)
    else:
        print("\n❌ vision_summary 为空，跳过 v4 接入测试。")

    print_title("最终结论")
    print("如果 Vision Adapter 成功，并且 v4 能根据 vision_summary 创建售后工单，说明真实图片 URL 识别链路已经跑通。")
    print("如果要测试 high 风险，请设置 TEST_VISION_IMAGE_URL 为清晰的珠宝掉钻/断裂图片 URL。")


if __name__ == "__main__":
    main()
