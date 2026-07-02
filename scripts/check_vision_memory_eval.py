import json
import urllib.request
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

    with urllib.request.urlopen(req, timeout=60) as resp:
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


def test_vision_agent():
    print_title("1. Vision Agent 多模态售后定损")

    data = post("/tools/handle_message_v4", {
        "message": "我的戒指有问题，订单号 ORD1001，请帮我看一下。",
        "session_id": "check-vision-agent",
        "files": [{"name": "ring_damage.jpg", "url": "mock://ring_damage.jpg"}],
        "vision_summary": "The ring appears to have a missing stone and damaged setting."
    })

    vision = (data.get("vision_agent") or {}).get("vision_assessment") or {}
    image = data.get("image_assessment") or {}

    print_kv("intent", data.get("intent"))
    print_kv("order_id", data.get("order_id"))
    print_kv("vision.has_image", vision.get("has_image"))
    print_kv("vision.damage_detected", vision.get("damage_detected"))
    print_kv("vision.damage_type", vision.get("damage_type"))
    print_kv("vision.severity", vision.get("severity"))
    print_kv("vision.confidence", vision.get("confidence"))
    print_kv("vision.need_human_review", vision.get("need_human_review"))

    print("\n--- ReAct Vision Steps ---")
    for step in data.get("react_steps", []):
        if "VisionAgent" in str(step.get("action")):
            print(f"Step {step.get('step_index')} | {step.get('action')}")
            print(f"Thought: {step.get('thought')}")
            print(f"Observation: {step.get('observation')}")

    return check_items([
        ("Vision Agent 已运行", (data.get("vision_agent") or {}).get("success") is True),
        ("识别到图片上下文", vision.get("has_image") is True),
        ("识别到损坏", vision.get("damage_detected") is True),
        ("严重程度为 high", vision.get("severity") == "high"),
        ("需要人工复核", vision.get("need_human_review") is True),
        ("ReAct 中包含 VisionAgent", any("VisionAgent" in str(s.get("action")) for s in data.get("react_steps", []))),
    ])


def test_memory_agent():
    print_title("2. Memory Agent 长期记忆")

    first = post("/tools/handle_message_v4", {
        "message": "我想买一条送女朋友的18K金项链，预算100美元以内。",
        "session_id": "check-memory-user",
        "files": [],
        "vision_summary": ""
    })

    second = post("/tools/handle_message_v4", {
        "message": "上次那个适合送礼吗？",
        "session_id": "check-memory-user",
        "files": [],
        "vision_summary": ""
    })

    memory = second.get("memory_agent") or {}
    profile = memory.get("customer_profile") or {}
    recent = memory.get("recent_memories") or []

    print_kv("profile.customer_id", profile.get("customer_id"))
    print_kv("profile.session_id", profile.get("session_id"))
    print_kv("profile.preferred_language", profile.get("preferred_language"))
    print_kv("memory_created_count", memory.get("memory_created_count"))
    print_kv("recent_memory_count", len(recent))

    print("\n--- Recent Memories ---")
    for item in recent[:5]:
        print(f"- [{item.get('memory_type')}] {item.get('content')}")

    print("\n--- ReAct Memory Steps ---")
    for step in second.get("react_steps", []):
        if "MemoryAgent" in str(step.get("action")):
            print(f"Step {step.get('step_index')} | {step.get('action')}")
            print(f"Thought: {step.get('thought')}")
            print(f"Observation: {step.get('observation')}")

    return check_items([
        ("Memory Agent 已运行", memory.get("success") is True),
        ("用户画像已创建", bool(profile.get("customer_id"))),
        ("存在长期记忆", len(recent) > 0),
        ("ReAct 中包含 MemoryAgent", any("MemoryAgent" in str(s.get("action")) for s in second.get("react_steps", []))),
    ])


def test_evaluation_agent():
    print_title("3. RAG / Bad Case 风控评测")

    data = post("/tools/evaluation/run", {})

    result = data.get("evaluation_result") or {}
    metrics = result.get("metrics") or {}
    cases = data.get("case_results") or []

    print_kv("suite_name", result.get("suite_name"))
    print_kv("total_cases", result.get("total_cases"))
    print_kv("passed_cases", result.get("passed_cases"))
    print_kv("failed_cases", result.get("failed_cases"))
    print_kv("pass_rate", result.get("pass_rate"))
    print_kv("hallucination_risk_rate", metrics.get("hallucination_risk_rate"))
    print_kv("refund_promise_violation_rate", metrics.get("refund_promise_violation_rate"))
    print_kv("handoff_missing_rate", metrics.get("handoff_missing_rate"))

    print("\n--- Evaluation Cases ---")
    for case in cases:
        print(f"{mark(case.get('passed'))} {case.get('case_id')} | {case.get('case_name')} | intent={case.get('intent')} | handoff={case.get('handoff')}")

    return check_items([
        ("评测执行成功", data.get("success") is True),
        ("测试用例数量大于 0", (result.get("total_cases") or 0) > 0),
        ("退款承诺违规率为 0", metrics.get("refund_promise_violation_rate") == 0),
        ("人工兜底遗漏率为 0", metrics.get("handoff_missing_rate") == 0),
    ])


def test_records():
    print_title("4. 后端记录验证")

    vision = get("/tools/vision_assessments")
    memories = get("/tools/memory_items")
    profiles = get("/tools/customer_profiles")
    evals = get("/tools/evaluation/results")
    bad_cases = get("/tools/bad_case_logs")

    print_kv("vision_assessments.count", vision.get("count"))
    print_kv("memory_items.count", memories.get("count"))
    print_kv("customer_profiles.count", profiles.get("count"))
    print_kv("evaluation_results.count", evals.get("count"))
    print_kv("bad_case_logs.count", bad_cases.get("count"))

    return check_items([
        ("vision_assessments 有记录", (vision.get("count") or 0) > 0),
        ("memory_items 有记录", (memories.get("count") or 0) > 0),
        ("customer_profiles 有记录", (profiles.get("count") or 0) > 0),
        ("evaluation_results 有记录", (evals.get("count") or 0) > 0),
    ])


def main():
    for fn in [test_vision_agent, test_memory_agent, test_evaluation_agent, test_records]:
        try:
            fn()
        except Exception as e:
            print(f"\n❌ 测试失败：{fn.__name__}")
            print(type(e).__name__, e)

    print_title("最终结论")
    print("如果以上核心检查均为 ✅，说明任务 3/4/5 合并包已经跑通。")


if __name__ == "__main__":
    main()
