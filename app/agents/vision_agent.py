import time
from typing import Any, Dict, List, Optional

from app.db import get_conn


def _now() -> int:
    return int(time.time())


def _lower(text: str) -> str:
    return (text or "").lower()


def analyze_damage_from_text(message: str, vision_summary: str = "", files: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    files = files or []
    text = _lower(f"{message or ''} {vision_summary or ''}")

    high_keywords = [
        "missing stone", "stone missing", "broken", "crack", "cracked", "fracture",
        "severe damage", "serious damage",
        "掉钻", "钻掉", "断裂", "裂开", "破裂", "严重损坏", "严重破损", "断了"
    ]

    medium_keywords = [
        "scratch", "scratched", "fading", "oxidized", "color difference",
        "defect", "damaged", "wear",
        "划痕", "刮痕", "褪色", "氧化", "色差", "瑕疵", "发黑", "掉色", "轻微损坏"
    ]

    has_image = len(files) > 0 or bool(vision_summary)

    if any(k in text for k in high_keywords):
        return {
            "has_image": has_image,
            "damage_detected": True,
            "damage_type": "missing_stone_or_severe_breakage",
            "severity": "high",
            "confidence": 0.86 if has_image else 0.74,
            "need_human_review": True,
            "vision_summary": vision_summary,
            "business_rule": "Vision Agent only provides initial triage. High-risk after-sales cases must be reviewed by human staff."
        }

    if any(k in text for k in medium_keywords):
        return {
            "has_image": has_image,
            "damage_detected": True,
            "damage_type": "surface_scratch_or_color_issue",
            "severity": "medium",
            "confidence": 0.78 if has_image else 0.66,
            "need_human_review": False,
            "vision_summary": vision_summary,
            "business_rule": "Medium-risk cases require evidence collection and after-sales review."
        }

    return {
        "has_image": has_image,
        "damage_detected": False if not has_image else True,
        "damage_type": "unclear_or_low_risk",
        "severity": "low",
        "confidence": 0.55 if has_image else 0.42,
        "need_human_review": False,
        "vision_summary": vision_summary,
        "business_rule": "If evidence is insufficient, ask the customer to provide clearer photos or videos."
    }


def save_vision_assessment(
    session_id: str,
    conversation_id: int,
    order_id: Optional[str],
    message: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO vision_assessments(
            session_id,
            conversation_id,
            order_id,
            damage_detected,
            damage_type,
            severity,
            confidence,
            need_human_review,
            vision_summary,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            conversation_id,
            order_id,
            1 if result.get("damage_detected") else 0,
            result.get("damage_type"),
            result.get("severity"),
            float(result.get("confidence") or 0),
            1 if result.get("need_human_review") else 0,
            result.get("vision_summary") or message[:300],
            _now()
        )
    )

    assessment_id = cur.lastrowid
    conn.commit()
    conn.close()

    saved = dict(result)
    saved["assessment_id"] = assessment_id
    saved["created"] = True
    return saved


def run_vision_agent(
    session_id: str,
    conversation_id: int,
    message: str,
    order_id: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
    vision_summary: str = "",
    intent: str = "",
) -> Dict[str, Any]:
    should_run = intent in ["after_sales", "after_sales_image_triage"] or bool(files) or bool(vision_summary)

    if not should_run:
        return {
            "agent": "vision_agent",
            "success": True,
            "skipped": True,
            "reason": "not_after_sales_or_no_image_context"
        }

    result = analyze_damage_from_text(
        message=message,
        vision_summary=vision_summary,
        files=files
    )

    saved = save_vision_assessment(
        session_id=session_id,
        conversation_id=conversation_id,
        order_id=order_id,
        message=message,
        result=result
    )

    return {
        "agent": "vision_agent",
        "success": True,
        "skipped": False,
        "vision_assessment": saved
    }


def list_vision_assessments(limit: int = 100):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT * FROM vision_assessments
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
