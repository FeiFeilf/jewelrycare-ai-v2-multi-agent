import time
from typing import Any, Dict, Optional
from app.db import get_conn


def create_task(
    task_type: str,
    related_type: str,
    related_id: str,
    title: str,
    description: str,
    owner: str,
    status: str = "open",
    due_at: Optional[int] = None,
) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks(
            task_type, related_type, related_id, title,
            description, owner, status, due_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (task_type, related_type, str(related_id), title, description, owner, status, due_at, int(time.time())))
    task_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return {
        "created": True,
        "task_id": task_id,
        "task_type": task_type,
        "related_type": related_type,
        "related_id": str(related_id),
        "title": title,
        "description": description,
        "owner": owner,
        "status": status,
        "due_at": due_at,
    }


def list_tasks(status: Optional[str] = None, task_type: Optional[str] = None) -> list[dict[str, Any]]:
    conn = get_conn()
    sql = "SELECT * FROM tasks WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if task_type:
        sql += " AND task_type = ?"
        params.append(task_type)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_task(task_id: int) -> Dict[str, Any]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    conn.close()
    if not row:
        return {"found": False, "message": "Task not found."}
    return {"found": True, "task": dict(row)}


def update_task_status(task_id: int, status: str) -> Dict[str, Any]:
    allowed = {"open", "in_progress", "waiting_customer", "done", "cancelled", "closed"}
    if status not in allowed:
        return {"updated": False, "message": f"Invalid status. Allowed values: {sorted(list(allowed))}"}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (status, task_id))
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        return {"updated": False, "message": "Task not found."}
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    conn.close()
    return {"updated": True, "task": dict(row)}
