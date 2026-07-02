import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "customer_service.db"
DB_PATH = os.getenv("DB_PATH", str(DEFAULT_DB_PATH))


def get_conn() -> sqlite3.Connection:
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(cur: sqlite3.Cursor, table: str, column: str, column_type: str) -> None:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row[1] for row in rows}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            product TEXT,
            price REAL,
            status TEXT,
            logistics_status TEXT,
            country TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS carts (
            cart_id TEXT PRIMARY KEY,
            customer_name TEXT,
            product TEXT,
            price REAL,
            status TEXT,
            last_active_minutes INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            issue_type TEXT,
            description TEXT,
            risk_level TEXT,
            evidence_required TEXT,
            suggested_resolution TEXT,
            assigned_to TEXT,
            status TEXT,
            created_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS handoffs (
            handoff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            order_id TEXT,
            reason TEXT,
            user_message TEXT,
            status TEXT,
            created_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recovery_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cart_id TEXT,
            customer_name TEXT,
            product TEXT,
            coupon TEXT,
            strategy TEXT,
            touch_status TEXT,
            conversion_status TEXT,
            created_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_message TEXT,
            intent TEXT,
            final_response TEXT,
            created_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_traces (
            trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            conversation_id INTEGER,
            agent_name TEXT,
            input_summary TEXT,
            output_summary TEXT,
            tool_called TEXT,
            success INTEGER,
            created_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT,
            related_type TEXT,
            related_id TEXT,
            title TEXT,
            description TEXT,
            owner TEXT,
            status TEXT,
            due_at INTEGER,
            created_at INTEGER
        )
    """)

    # 兼容旧版本数据库：如果旧表已存在但缺字段，则自动补字段。
    for col, typ in [
        ("evidence_required", "TEXT"),
        ("suggested_resolution", "TEXT"),
        ("assigned_to", "TEXT"),
    ]:
        ensure_column(cur, "tickets", col, typ)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS react_steps (
            step_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            conversation_id INTEGER,
            step_index INTEGER,
            thought TEXT,
            action TEXT,
            action_input TEXT,
            observation TEXT,
            success INTEGER,
            created_at INTEGER
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS discount_codes (
            discount_id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            cart_id TEXT,
            customer_name TEXT,
            product TEXT,
            strategy TEXT,
            discount_type TEXT,
            value TEXT,
            reason TEXT,
            status TEXT,
            created_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS refund_reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            ticket_id INTEGER,
            reason TEXT,
            risk_level TEXT,
            requested_action TEXT,
            user_message TEXT,
            status TEXT,
            created_at INTEGER
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS vision_assessments (
            assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            conversation_id INTEGER,
            order_id TEXT,
            damage_detected INTEGER,
            damage_type TEXT,
            severity TEXT,
            confidence REAL,
            need_human_review INTEGER,
            vision_summary TEXT,
            created_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_profiles (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            name TEXT,
            email TEXT,
            preferred_language TEXT,
            last_order_id TEXT,
            purchase_count INTEGER,
            risk_tags TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory_items (
            memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            customer_id INTEGER,
            memory_type TEXT,
            content TEXT,
            source TEXT,
            importance INTEGER,
            created_at INTEGER,
            updated_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bad_case_logs (
            bad_case_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            case_name TEXT,
            user_message TEXT,
            failure_type TEXT,
            detail TEXT,
            severity TEXT,
            created_at INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_results (
            evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            suite_name TEXT,
            total_cases INTEGER,
            passed_cases INTEGER,
            failed_cases INTEGER,
            pass_rate REAL,
            metrics_json TEXT,
            created_at INTEGER
        )
    """)

    seed_orders = [
        ("ORD1001", "Alice", "18K Gold Ring", 129.99, "paid", "delivered", "US", "2026-06-01"),
        ("ORD1002", "Bob", "Silver Necklace", 59.99, "paid", "in_transit", "UK", "2026-06-05"),
        ("ORD1003", "Cindy", "Pearl Earrings", 89.99, "refunded", "delivered", "CA", "2026-06-07"),
    ]
    for row in seed_orders:
        cur.execute("""
            INSERT OR IGNORE INTO orders
            (order_id, customer_name, product, price, status, logistics_status, country, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, row)

    seed_carts = [
        ("CART2001", "Daisy", "Rose Gold Bracelet", 79.99, "abandoned", 45),
        ("CART2002", "Eva", "Moissanite Ring", 199.99, "abandoned", 180),
    ]
    for row in seed_carts:
        cur.execute("""
            INSERT OR IGNORE INTO carts
            (cart_id, customer_name, product, price, status, last_active_minutes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, row)

    conn.commit()
    conn.close()


def create_conversation(session_id: str, user_message: str, intent: str = "", final_response: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO conversations(session_id, user_message, intent, final_response, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, user_message, intent, final_response, int(time.time())))
    conversation_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return conversation_id


def update_conversation(conversation_id: int, intent: str = "", final_response: str = "") -> None:
    conn = get_conn()
    conn.execute("""
        UPDATE conversations
        SET intent = ?, final_response = ?
        WHERE conversation_id = ?
    """, (intent, final_response, conversation_id))
    conn.commit()
    conn.close()


def log_agent_trace(
    session_id: str,
    conversation_id: int,
    agent_name: str,
    input_summary: str,
    output_summary: str,
    tool_called: str = "",
    success: bool = True,
) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO agent_traces(
            session_id, conversation_id, agent_name,
            input_summary, output_summary, tool_called, success, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        conversation_id,
        agent_name,
        input_summary,
        output_summary,
        tool_called,
        1 if success else 0,
        int(time.time()),
    ))
    trace_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return {
        "trace_id": trace_id,
        "agent_name": agent_name,
        "tool_called": tool_called,
        "success": success,
        "output_summary": output_summary,
    }


def count_rows(table_name: str, where_clause: str = "", params: tuple = ()) -> int:
    conn = get_conn()
    sql = f"SELECT COUNT(*) AS cnt FROM {table_name}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return int(row["cnt"]) if row else 0


def fetch_dicts(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]
