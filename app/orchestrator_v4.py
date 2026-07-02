from typing import Any, Dict

from app.orchestrator import orchestrate_message_v3
from app.agents.react_planner_agent import run_react_planner_agent


def orchestrate_message_v4(req) -> Dict[str, Any]:
    """
    v4：ReAct Trace 升级版入口。

    处理流程：
    1. 复用 v3 的稳定 Multi-Agent 闭环能力；
    2. 基于实际处理结果生成 ReAct Thought-Action-Observation 轨迹；
    3. 返回完整结构化结果给 Dify。
    """

    result = orchestrate_message_v3(req)

    react_result = run_react_planner_agent(result)

    result["version"] = "v4_react_trace"
    result["mode"] = "closed_loop_multi_agent_with_react_trace"
    result["react_planner"] = {
        "success": react_result.get("success"),
        "react_step_count": react_result.get("react_step_count"),
    }
    result["react_steps"] = react_result.get("react_steps", [])

    return result
