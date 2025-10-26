import datetime as dt
import secrets
import hashlib
from jose import jwt
from fastapi import HTTPException, status, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from argon2 import PasswordHasher
from app.config import settings
from app.models.user import User
from app.models.session import Session


bearer = HTTPBearer()
ph = PasswordHasher()


class AuthUser:
    def __init__(self, user_id: str, is_admin: bool = False):
        self.user_id = user_id
        self.is_admin = is_admin


def create_token(user_id: str) -> str:
    # Validate JWT secret
    if not settings.JWT_SECRET or len(settings.JWT_SECRET.strip()) < 32:
        # In non-production, fall back to a safe dev secret to avoid 500s in tests
        if (settings.APP_ENV or "").strip().lower() != "production":
            secret = "dev-jwt-secret-change-me-very-long-32-chars-minimum"
        else:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
    else:
        secret = settings.JWT_SECRET

    # Use datetime.now() with UTC timezone
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MIN)
    payload = {"sub": user_id, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, secret, algorithm="HS256")


async def create_session_token(user_id: str) -> str:
    """Create a secure session token for refresh functionality"""
    token = secrets.token_urlsafe(32)
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30)
    
    # Revoke existing sessions for this user (optional - single session per user)
    await Session.filter(user_id=user_id).update(revoked=True)
    
    # Create new session
    await Session.create(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        revoked=False
    )
    
    return token


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token"""
    return secrets.token_urlsafe(32)


def create_csrf_token_hash(token: str) -> str:
    """Create a hash of the CSRF token for double-submit validation"""
    return hashlib.sha256(token.encode()).hexdigest()


def validate_csrf_tokens(header_token: str, cookie_token: str) -> bool:
    """Validate CSRF double-submit tokens"""
    if not header_token or not cookie_token:
        return False
    
    # Compare the hash of the header token with the cookie token
    header_hash = create_csrf_token_hash(header_token)
    return secrets.compare_digest(header_hash, cookie_token)


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
        payload = jwt.decode(
            creds.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            options={"leeway": 30},  # 30s clock skew tolerance
        )
        user_id = str(payload["sub"])
        db_user = await User.filter(id=user_id).first()
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found")
        return AuthUser(user_id, bool(db_user.is_admin))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# --- ADMIN GUARD ---
async def require_admin(user: AuthUser = Depends(require_user)) -> AuthUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# --- SHARE TOKENS (album-level) ---
def create_share_token(user_id: str, album_id: str, hours: int = 72) -> str:
    # Validate JWT secret
    if not settings.JWT_SECRET or len(settings.JWT_SECRET.strip()) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")
    
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(hours=hours)
    payload = {
        "typ": "share",
        "sub": user_id,
        "alb": album_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_share_token(token: str) -> dict:
    # Validate JWT secret
    if not settings.JWT_SECRET or len(settings.JWT_SECRET.strip()) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")
    
    try:
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if data.get("typ") != "share":
            raise jwt.JWTError("Wrong token type")
        return data
    except jwt.JWTError:
        raise jwt.JWTError("Invalid share token")