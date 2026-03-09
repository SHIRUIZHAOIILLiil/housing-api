import sqlite3
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from app.schemas import NotFoundError, ConflictError
from app.services.service_audit import log_audit_event


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ensure_unique_username_email(
    conn: sqlite3.Connection,
    username: str,
    email: str,
) -> None:
    """
    Ensure username/email are not already used.
    """
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT 1
        FROM users
        WHERE username = ? OR email = ?
        LIMIT 1
        """,
        (username, email),
    ).fetchone()

    if row is not None:
        raise ConflictError("Username or email already exists")


def create_user(
    conn: sqlite3.Connection,
    username: str,
    email: str,
    password_hash: str,
) -> int:
    """
    Create a new user row and return the new user id.
    """
    conn.row_factory = sqlite3.Row

    # Perform explicit conflict checks first
    # (better readability and more controllable error messages).
    _ensure_unique_username_email(conn, username=username, email=email)

    try:
        cur = conn.execute(
            """
            INSERT INTO users (username, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (username, email, password_hash, _utc_iso()),
        )

        user_id = int(cur.lastrowid)

        log_audit_event(
            conn=conn,
            user_id=user_id,
            action="CREATE",
            resource_type="users",
            resource_id=user_id,
            detail={
                "username": username,
                "email": email
            }
        )

        conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        # # Defense: UNIQUE constraints may still be triggered under concurrent/extreme conditions
        raise ConflictError("Username or email already exists")


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT id, username, email, password_hash, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def get_user_by_login_key(conn: sqlite3.Connection, login: str) -> Optional[sqlite3.Row]:
    """
    Login key can be either username or email.
    Because both username and email are UNIQUE, at most one row can match.
    """
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        SELECT id, username, email, password_hash, created_at
        FROM users
        WHERE username = ? OR email = ?
        """,
        (login, login),
    ).fetchone()
