import json
import time
from typing import Any, Dict, List, Optional

from app.db import get_conn


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def create_react_step(
    session_id: str,
    conversation_id: int,
    step_index: int,
    thought: str,
    action: str,
    action_input: Any = None,
    observation: Any = None,
    success: bool = True,
) -> Dict[str, Any]:
    """
    记录 ReAct 单步轨迹：
    Thought -> Action -> Observation
    """

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO react_steps(
            session_id,
            conversation_id,
            step_index,
            thought,
            action,
            action_input,
            observation,
            success,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            conversation_id,
            step_index,
            thought,
            action,
            _to_text(action_input),
            _to_text(observation),
            1 if success else 0,
            int(time.time()),
        )
    )

    step_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "step_id": step_id,
        "session_id": session_id,
        "conversation_id": conversation_id,
        "step_index": step_index,
        "thought": thought,
        "action": action,
        "action_input": action_input,
        "observation": observation,
        "success": success,
    }


def list_react_steps(
    conversation_id: Optional[int] = None,
    session_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    conn = get_conn()

    sql = "SELECT * FROM react_steps WHERE 1=1"
    params = []

    if conversation_id is not None:
        sql += " AND conversation_id = ?"
        params.append(conversation_id)

    if session_id:
        sql += " AND session_id = ?"
        params.append(session_id)

    sql += " ORDER BY created_at DESC, step_index ASC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]
