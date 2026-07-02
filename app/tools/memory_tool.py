import json
import re
import time
from typing import Any, Dict, List, Optional

from app.db import get_conn


def _now() -> int:
    return int(time.time())


def _json_list(values: List[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def get_or_create_customer_profile(
    session_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    preferred_language: Optional[str] = None,
) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    row = cur.execute(
        "SELECT * FROM customer_profiles WHERE session_id = ?",
        (session_id,)
    ).fetchone()

    if row:
        profile = dict(row)
        conn.close()
        return profile

    cur.execute(
        """
        INSERT INTO customer_profiles(
            session_id,
            name,
            email,
            preferred_language,
            last_order_id,
            purchase_count,
            risk_tags,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            name,
            email,
            preferred_language or "auto",
            None,
            0,
            _json_list([]),
            _now(),
            _now()
        )
    )

    customer_id = cur.lastrowid
    conn.commit()

    row = cur.execute(
        "SELECT * FROM customer_profiles WHERE customer_id = ?",
        (customer_id,)
    ).fetchone()

    conn.close()
    return dict(row)


def update_customer_profile(
    customer_id: int,
    last_order_id: Optional[str] = None,
    risk_tag: Optional[str] = None,
    preferred_language: Optional[str] = None,
):
    conn = get_conn()
    cur = conn.cursor()

    row = cur.execute(
        "SELECT * FROM customer_profiles WHERE customer_id = ?",
        (customer_id,)
    ).fetchone()

    if not row:
        conn.close()
        return None

    profile = dict(row)

    risk_tags = []
    try:
        risk_tags = json.loads(profile.get("risk_tags") or "[]")
    except Exception:
        risk_tags = []

    if risk_tag and risk_tag not in risk_tags:
        risk_tags.append(risk_tag)

    cur.execute(
        """
        UPDATE customer_profiles
        SET last_order_id = COALESCE(?, last_order_id),
            preferred_language = COALESCE(?, preferred_language),
            risk_tags = ?,
            updated_at = ?
        WHERE customer_id = ?
        """,
        (
            last_order_id,
            preferred_language,
            _json_list(risk_tags),
            _now(),
            customer_id
        )
    )

    conn.commit()

    row = cur.execute(
        "SELECT * FROM customer_profiles WHERE customer_id = ?",
        (customer_id,)
    ).fetchone()

    conn.close()
    return dict(row)


def create_memory_item(
    session_id: str,
    customer_id: Optional[int],
    memory_type: str,
    content: str,
    source: str,
    importance: int = 3
) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO memory_items(
            session_id,
            customer_id,
            memory_type,
            content,
            source,
            importance,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            customer_id,
            memory_type,
            content,
            source,
            importance,
            _now(),
            _now()
        )
    )

    memory_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "created": True,
        "memory_id": memory_id,
        "session_id": session_id,
        "customer_id": customer_id,
        "memory_type": memory_type,
        "content": content,
        "source": source,
        "importance": importance
    }


def list_memory_items(
    session_id: Optional[str] = None,
    customer_id: Optional[int] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    conn = get_conn()

    sql = "SELECT * FROM memory_items WHERE 1=1"
    params = []

    if session_id:
        sql += " AND session_id = ?"
        params.append(session_id)

    if customer_id is not None:
        sql += " AND customer_id = ?"
        params.append(customer_id)

    sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_customer_profiles(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT * FROM customer_profiles
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def extract_memory_candidates(message: str, result: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = message or ""
    lower = text.lower()
    memories = []

    if any(k in lower for k in ["gift", "girlfriend", "wife", "mother", "送女朋友", "送礼", "送妈妈", "生日礼物"]):
        memories.append({
            "memory_type": "purchase_intent",
            "content": f"用户存在送礼需求：{text[:120]}",
            "importance": 4
        })

    if any(k in lower for k in ["18k", "gold", "silver", "pearl", "黄金", "18k金", "银", "珍珠"]):
        memories.append({
            "memory_type": "material_preference",
            "content": f"用户关注或偏好材质信息：{text[:120]}",
            "importance": 3
        })

    budget_match = re.search(r"(\d+)\s*(美元|美金|usd|dollar|\$)", lower, re.IGNORECASE)
    if budget_match:
        memories.append({
            "memory_type": "budget_preference",
            "content": f"用户预算偏好约为 {budget_match.group(1)} {budget_match.group(2)}",
            "importance": 4
        })

    order_id = result.get("order_id")
    if order_id:
        memories.append({
            "memory_type": "recent_order",
            "content": f"用户最近提到订单 {order_id}",
            "importance": 4
        })

    risk_level = ((result.get("image_assessment") or {}).get("risk_level")
                  or ((result.get("vision_agent") or {}).get("vision_assessment") or {}).get("severity"))

    if result.get("handoff") or risk_level == "high":
        memories.append({
            "memory_type": "risk_tag",
            "content": f"用户出现高风险售后或人工兜底场景，risk_level={risk_level}",
            "importance": 5
        })

    if result.get("cart_id"):
        memories.append({
            "memory_type": "recent_cart",
            "content": f"用户最近提到购物车 {result.get('cart_id')}",
            "importance": 3
        })

    return memories
