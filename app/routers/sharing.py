from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

from app.utils.qr_utils import generate_qr_for_link

pip install -r requirements.txt# Module: router declaration — standardize tag to `share`
router = APIRouter(prefix="/share", tags=["share"])

@router.get("/{album_id}/qr")
async def get_album_qr(album_id: str):
    """
    Returns QR code PNG for an album's public share link
    """
    # Validate album_id to prevent path traversal
    import re
    if not album_id or not re.match(r'^[a-zA-Z0-9_-]+$', album_id) or len(album_id) > 50:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid album ID")
    
    # Album ka public link banao
    album_link = f"https://photovault.com/share/{album_id}"

    # QR image path set karo (sanitized)
    qr_path = f"qrcodes/{album_id}.png"

    # Agar QR already exist nahi karta to generate karo
    if not os.path.exists(qr_path):
        generate_qr_for_link(album_link, qr_path)

    return FileResponse(qr_path, media_type="image/png")
