from fastapi import APIRouter, HTTPException, Depends
from tortoise.transactions import in_transaction
from app.models.share import Share
from app.services.tokens import generate_token, generate_otp
from app.services.qr import generate_qr_code
from app.services.alerts import send_security_alert
from datetime import datetime, timedelta

router = APIRouter(prefix="/shares", tags=["shares"])

@router.post("/create")
async def create_share(image_id: int, user_id: int, expires_in: int = 600):
    token = generate_token()
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    async with in_transaction():
        share = await Share.create(image_id=image_id, token=token, expires_at=expires_at, otp=otp)
    qr_bytes = generate_qr_code(token)
    send_security_alert(user_id, "share_created", f"image_id={image_id}")
    return {"token": token, "otp": otp, "qr": qr_bytes.hex()}

@router.post("/access")
async def access_share(token: str, otp: str):
    share = await Share.get_or_none(token=token, otp=otp, used=False)
    if not share or (share.expires_at and share.expires_at < datetime.utcnow()):
        raise HTTPException(status_code=403, detail="Invalid or expired share")
    share.used = True
    await share.save()
    return {"image_id": share.image_id}