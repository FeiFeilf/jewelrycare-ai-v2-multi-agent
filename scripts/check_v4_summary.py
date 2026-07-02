import json
import urllib.request
import urllib.error


BASE_URL = "http://127.0.0.1:8000"

payload = {
    "message": "我的戒指掉钻了，订单号 ORD1001，请帮我处理。",
    "session_id": "quick-check-v4",
    "files": [],
    "vision_summary": ""
}


def post_json(path, data):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    data = post_json("/tools/handle_message_v4", payload)

    order = data.get("order") or {}
    ticket = data.get("ticket") or {}
    image = data.get("image_assessment") or {}
    react = data.get("react_planner") or {}

    print("\n========== v4 核心检查结果 ==========")
    print(f"version:            {data.get('version')}")
    print(f"mode:               {data.get('mode')}")
    print(f"intent:             {data.get('intent')}")
    print(f"target_agent:       {data.get('target_agent')}")
    print(f"order_id:           {data.get('order_id')}")
    print(f"order_found:        {order.get('found')}")
    print(f"order_status:       {order.get('status')}")
    print(f"logistics_status:   {order.get('logistics_status')}")
    print(f"product:            {order.get('product')}")
    print(f"risk_level:         {image.get('risk_level')}")
    print(f"ticket_created:     {ticket.get('created')}")
    print(f"ticket_id:          {ticket.get('ticket_id')}")
    print(f"handoff:            {data.get('handoff')}")
    print(f"handoff_reason:     {data.get('handoff_reason')}")
    print(f"task_count:         {data.get('task_count')}")
    print(f"react_step_count:   {react.get('react_step_count')}")

    print("\n========== ReAct Steps ==========")
    for step in data.get("react_steps", []):
        print(f"\nStep {step.get('step_index')}")
        print(f"Thought:     {step.get('thought')}")
        print(f"Action:      {step.get('action')}")
        print(f"Success:     {step.get('success')}")
        observation = step.get("observation")
        if isinstance(observation, dict):
            print("Observation:")
            for k, v in observation.items():
                print(f"  - {k}: {v}")
        else:
            print(f"Observation: {observation}")

    print("\n========== 验收判断 ==========")

    checks = [
        ("version = v4_react_trace", data.get("version") == "v4_react_trace"),
        ("mode = closed_loop_multi_agent_with_react_trace", data.get("mode") == "closed_loop_multi_agent_with_react_trace"),
        ("intent = after_sales", data.get("intent") == "after_sales"),
        ("ticket 已创建", ticket.get("created") is True),
        ("handoff = true", data.get("handoff") is True),
        ("tasks 不为空", (data.get("task_count") or 0) > 0),
        ("react_steps 不为空", len(data.get("react_steps", [])) > 0),
        ("react_planner 正常", react.get("success") is True),
    ]

    passed = 0
    for name, ok in checks:
        mark = "✅" if ok else "❌"
        print(f"{mark} {name}")
        if ok:
            passed += 1

    print(f"\n通过 {passed}/{len(checks)} 项")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        print("请求失败，请确认后端是否启动：")
        print("curl http://127.0.0.1:8000/health")
        print(e)
    except Exception as e:
        print("检查脚本执行失败：")
        print(type(e).__name__, e)
