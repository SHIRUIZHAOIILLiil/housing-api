from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.schemas import UnauthorizedError
from app.core import Settings

settings = Settings()

jwt_expire_minutes = settings.JWT_EXPIRE_MINUTES
jwt_algorithm = settings.JWT_ALGORITHM

class TokenError(Exception):
    pass


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET , algorithm=jwt_algorithm)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedError("invalid token")
        return int(sub)
    except (JWTError, ValueError):
        raise UnauthorizedError("invalid token")