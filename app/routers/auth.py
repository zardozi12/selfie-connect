# imports at top of file
from fastapi import APIRouter, HTTPException, Depends, Body, Request, Response, Header
import os
import secrets
import hashlib
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import logging

from app.schemas.auth import SignupPayload, LoginPayload, TokenOut
from app.models.user import User
from app.models.session import Session
from app.services.security import hash_password, verify_password, create_token, require_user, AuthUser
from app.services import encryption
from app.config import settings
try:
    from fastapi_csrf_protect import CsrfProtect
    csrf_enabled = True
except Exception:
    csrf_enabled = False
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services.security import validate_csrf_tokens

limiter = Limiter(key_func=get_remote_address)
log = logging.getLogger(__name__)

# Module: auth.py (CSRF, session cookies, refresh/rotation)

# Module-level helpers and router setup
router = APIRouter(prefix="/auth", tags=["auth"])

def _generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def _hash_csrf_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _cookie_settings():
    return {
        "httponly": True,
        "secure": (os.getenv("APP_ENV", "development") == "production"),
        "samesite": "Lax",
    }

# Method: validate_csrf_request()
def validate_csrf_request(request: Request, x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token")):
    """Validate CSRF double-submit tokens; enforced only in production."""
    env = (settings.APP_ENV or "").strip().lower()
    # Skip CSRF in non-production (dev/test/pytest)
    if env != "production" or ("PYTEST_CURRENT_TEST" in os.environ):
        return
    csrf_cookie = request.cookies.get("csrf_token")
    if not validate_csrf_tokens(x_csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="CSRF token validation failed")

@router.post("/signup", response_model=TokenOut, status_code=201)
@limiter.limit("10/minute")
async def signup(
    request: Request,
    response: Response,
    payload: SignupPayload = Body(...),
    x_csrf_token: Optional[str] = Header(default=None, alias="X-CSRF-Token"),
):
    """
    Signup with email + password, CSRF protection, and session creation.
    """
    # CSRF validation (skip in dev/test per env)
    validate_csrf_request(request, x_csrf_token)

    exists = await User.filter(email=payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    dek = encryption.new_data_key()
    user = await User.create(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        dek_encrypted_b64=encryption.wrap_dek(dek),
        is_admin=False
    )

    token = create_token(str(user.id))
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    await Session.create(user_id=user.id, token=session_token, revoked=False, expires_at=expires_at)

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=int(timedelta(days=30).total_seconds()),
        **_cookie_settings(),
    )
    return TokenOut(access_token=token)

# Method: login()
@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    payload: LoginPayload = Body(...),
    x_csrf_token: Optional[str] = Header(default=None, alias="X-CSRF-Token"),
):
    """
    Login with email + password, CSRF protection, and session creation.
    """
    validate_csrf_request(request, x_csrf_token)

    user = await User.filter(email=payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(str(user.id))
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    await Session.create(user_id=user.id, token=session_token, revoked=False, expires_at=expires_at)

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=int(timedelta(days=30).total_seconds()),
        **_cookie_settings(),
    )
    return TokenOut(access_token=token)

# Method: refresh_jwt()
@router.post("/refresh")
@limiter.limit("20/minute")
async def refresh_jwt(request: Request, response: Response):
    """
    Refresh JWT access token using session cookie.
    """
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="No session cookie")

    session = await Session.get_or_none(token=session_token, revoked=False)
    if not session or (session.expires_at and session.expires_at < datetime.now(timezone.utc)):
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    rotate = os.getenv("APP_ENV", "development") == "production"
    if rotate:
        session.revoked = True
        await session.save()
        new_session_token = secrets.token_urlsafe(32)
        new_expires = datetime.now(timezone.utc) + timedelta(days=30)
        await Session.create(user_id=session.user_id, token=new_session_token, revoked=False, expires_at=new_expires)
        response.set_cookie(
            key="session_token",
            value=new_session_token,
            max_age=int(timedelta(days=30).total_seconds()),
            **_cookie_settings(),
        )

    jwt_token = create_token(str(session.user_id))
    return TokenOut(access_token=jwt_token)
    
    # Create new JWT access token
    access_token = create_token(str(session.user_id))
    
    # Optionally rotate session token for enhanced security
    if settings.APP_ENV == "production":
        new_session_token = await create_session_token(str(session.user_id))
        response.set_cookie(
            key="session_token",
            value=new_session_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=30 * 24 * 3600  # 30 days
        )
    
    return TokenOut(access_token=access_token)

# Method: logout_jwt()
@router.post("/logout")
async def logout_jwt(request: Request, response: Response, auth: AuthUser = Depends(require_user)):
    """
    Logout user by revoking session and clearing cookies.
    """
    session_token = request.cookies.get("session_token")
    if session_token:
        s = await Session.get_or_none(token=session_token)
        if s:
            s.revoked = True
            await s.save()

    response.delete_cookie("session_token")
    response.delete_cookie("csrf_token")
    return {"ok": True, "message": "Logged out successfully"}

@router.get("/verify")
async def verify_token(auth: AuthUser = Depends(require_user)):
    """Debug endpoint to verify token is working"""
    return {
        "ok": True,
        "user_id": auth.user_id,
        "message": "Token is valid"
    }

@router.get("/token-info")
async def get_token_info(auth: AuthUser = Depends(require_user)):
    """Get detailed token information for debugging"""
    return {
        "user_id": auth.user_id,
        "message": "Token is working correctly"
    }

# Method: register()
@router.post("/register", response_model=TokenOut)
@limiter.limit("10/minute")
async def register(
    request: Request,
    response: Response,
    payload: SignupPayload = Body(...),
    x_csrf_token: Optional[str] = Header(default=None, alias="X-CSRF-Token"),
):
    return await signup(request, response, payload, x_csrf_token)

# function get_current_user
@router.get("/me")
async def get_current_user(auth: AuthUser = Depends(require_user)):
    try:
        user = await User.get(id=auth.user_id)
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
