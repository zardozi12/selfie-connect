from jose import jwt
import time
from typing import Any, Dict
from app.config import settings

def create_jwt_token(data: dict, expires_in: int = 3600) -> str:
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_jwt_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])