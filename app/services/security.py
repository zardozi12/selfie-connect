import datetime as dt
import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from argon2 import PasswordHasher
from app.config import settings


bearer = HTTPBearer()
ph = PasswordHasher()


class AuthUser:
    def __init__(self, user_id: str):
        self.user_id = user_id


def create_token(user_id: str) -> str:
    # Use datetime.now() with UTC timezone instead of deprecated utcnow()
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MIN)
    
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp())
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_password(pw: str, pw_hash: str) -> bool:
    try:
        ph.verify(pw_hash, pw)
        return True
    except Exception:
        return False


def hash_password(pw: str) -> str:
    return ph.hash(pw)


async def require_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> AuthUser:
    if not creds or not creds.scheme.lower().startswith("bearer"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth")
    
    try:
        payload = jwt.decode(creds.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        return AuthUser(str(payload["sub"]))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")