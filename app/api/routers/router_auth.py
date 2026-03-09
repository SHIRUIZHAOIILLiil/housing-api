import sqlite3
from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_conn
from app.schemas import UnauthorizedError
from app.schemas.schema_auth import UserCreate, UserOut, TokenOut
from app.services.service_users import create_user, get_user_by_login_key, get_user_by_id
from app.security.password import hash_password, verify_password
from app.security.jwt import create_access_token
from app.services import log_audit_event


router = APIRouter()


@router.post(
    "/register",
    response_model=UserOut,
    summary="Register a new user",
)
def api_register(
    payload: UserCreate,
    conn: sqlite3.Connection = Depends(get_conn),
):
    """
    Create a user account.
    - Stores password as a secure hash (never stores plaintext password)
    - Enforces unique username/email via service layer
    """
    user_id = create_user(
        conn,
        username=payload.username,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
    )

    row = get_user_by_id(conn, user_id)
    return UserOut(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        created_at=row["created_at"],
    )


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Login and get access token",
)
def api_login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    conn: sqlite3.Connection = Depends(get_conn),
):
    """
    Login with username OR email (form.username field can be either).
    Returns JWT bearer token.
    """
    user = get_user_by_login_key(conn, form.username)
    request_id = getattr(request.state, "request_id", None)

    if user is None:
        log_audit_event(
            conn=conn,
            user_id=None,
            action="LOGIN_FAILED",
            resource_type="auth",
            detail={
                "login": form.username,
                "reason": "user not found",
            },
        )
        conn.commit()
        raise UnauthorizedError("Invalid credentials")

    if not verify_password(form.password, user["password_hash"]):
        log_audit_event(
            conn=conn,
            user_id=int(user["id"]),
            action="LOGIN_FAILED",
            resource_type="auth",
            request_id=request_id,
            detail={
                "login": form.username,
                "reason": "invalid password",
            },
        )
        conn.commit()
        raise UnauthorizedError("Invalid credentials")

    log_audit_event(
        conn=conn,
        user_id=int(user["id"]),
        action="LOGIN_SUCCESS",
        resource_type="auth",
        request_id=request_id,
        detail={
            "login": form.username,
        },
    )
    conn.commit()

    token = create_access_token(int(user["id"]))
    return TokenOut(access_token=token, token_type="bearer")