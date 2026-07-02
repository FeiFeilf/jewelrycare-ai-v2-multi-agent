import json
import time
from typing import Any, Dict, List, Optional

from app.db import get_conn


def _now() -> int:
    return int(time.time())


def save_bad_case(
    case_id: str,
    case_name: str,
    user_message: str,
    failure_type: str,
    detail: str,
    severity: str = "medium"
) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO bad_case_logs(
            case_id,
            case_name,
            user_message,
            failure_type,
            detail,
            severity,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            case_name,
            user_message,
            failure_type,
            detail,
            severity,
            _now()
        )
    )

    bad_case_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "created": True,
        "bad_case_id": bad_case_id,
        "case_id": case_id,
        "failure_type": failure_type,
        "severity": severity
    }


def save_evaluation_result(
    suite_name: str,
    total_cases: int,
    passed_cases: int,
    failed_cases: int,
    metrics: Dict[str, Any]
) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    pass_rate = round(passed_cases / total_cases, 4) if total_cases else 0

    cur.execute(
        """
        INSERT INTO evaluation_results(
            suite_name,
            total_cases,
            passed_cases,
            failed_cases,
            pass_rate,
            metrics_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            suite_name,
            total_cases,
            passed_cases,
            failed_cases,
            pass_rate,
            json.dumps(metrics, ensure_ascii=False),
            _now()
        )
    )

    evaluation_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "created": True,
        "evaluation_id": evaluation_id,
        "suite_name": suite_name,
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "pass_rate": pass_rate,
        "metrics": metrics
    }


def list_bad_case_logs(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT * FROM bad_case_logs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_evaluation_results(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT * FROM evaluation_results
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        try:
            item["metrics"] = json.loads(item.get("metrics_json") or "{}")
        except Exception:
            item["metrics"] = {}
        results.append(item)

    return results
