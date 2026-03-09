import json
import sqlite3
from typing import Any, Optional


def log_audit_event(
    conn: sqlite3.Connection,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    request_id=None,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, request_id, detail)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            action,
            resource_type,
            resource_id,
            request_id,
            json.dumps(detail, ensure_ascii=False) if detail is not None else None,
        ),
    )