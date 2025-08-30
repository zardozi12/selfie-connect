from fastapi import APIRouter, HTTPException, Depends
from app.schemas.auth import SignupPayload, LoginPayload, TokenOut
from app.models.user import User
from app.services.security import hash_password, verify_password, create_token, require_user, AuthUser
from app.services import encryption
import jwt
from app.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut)
async def signup(payload: SignupPayload):
    exists = await User.filter(email=payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    dek = encryption.new_data_key()  # base64 key
    user = await User.create(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        dek_encrypted_b64=encryption.wrap_dek(dek)
    )
    token = create_token(str(user.id))
    return TokenOut(access_token=token)


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginPayload):
    user = await User.filter(email=payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(str(user.id))
    return TokenOut(access_token=token)


@router.get("/verify")
async def verify_token(auth: AuthUser = Depends(require_user)):
    """Debug endpoint to verify token is working"""
    return {
        "valid": True,
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