"""
Public share endpoints for PhotoVault
Handles token-based access to shared albums without authentication
"""

from __future__ import annotations
from uuid import UUID
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services.shares import validate_share, increment_share_view
from app.models.album import AlbumImage, Album
from app.models.image import Image
from app.models.user import User
from app.services.deta_storage import storage
from app.services.encryption import unwrap_dek, fernet_from_dek
from app.services.metrics import record_share_viewed

public_api = APIRouter(tags=["share"])

@public_api.get("/share/{token}")
async def share_list(token: str):
    """List images in a shared album (no login required)"""
    val = await validate_share(token)
    if not val:
        raise HTTPException(status_code=401, detail="Invalid or expired link")
    
    album_id = val["jwt"]["alb"]
    
    # Get album and images
    album = await Album.filter(id=album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    joins = await AlbumImage.filter(album_id=album_id).prefetch_related("image").order_by("added_at")
    images = [j.image for j in joins if j.image is not None]
    
    # Increment view count
    await increment_share_view(token)
    record_share_viewed()
    
    return {
        "album": {"id": str(album_id), "name": album.name},
        "images": [
            {
                "id": str(img.id), 
                "view_url": f"/share/{token}/image/{img.id}", 
                "w": img.width, 
                "h": img.height,
                "filename": img.original_filename
            }
            for img in images
        ],
    }

@public_api.get("/share/{token}/image/{image_id}")
async def share_image(token: str, image_id: UUID):
    """View a single image from shared album (no login required)"""
    val = await validate_share(token)
    if not val:
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    album_id = val["jwt"]["alb"]
    sub_user_id = val["jwt"]["sub"]
    
    # Confirm image is in the shared album
    if not await AlbumImage.filter(album_id=album_id, image_id=image_id).first():
        raise HTTPException(status_code=404, detail="Image not in shared album")

    # Load user and image
    user = await User.filter(id=sub_user_id).first()
    img = await Image.filter(id=image_id).first()
    if not user or not img:
        raise HTTPException(status_code=404, detail="Not found")

    # Decrypt and stream image
    dek_b64 = unwrap_dek(user.dek_encrypted_b64)
    fernet = fernet_from_dek(dek_b64)
    
    enc = storage.read(img.storage_key)
    try:
        plain = fernet.decrypt(enc)
    except Exception:
        raise HTTPException(status_code=500, detail="Decryption failed")
    
    # Increment view count
    await increment_share_view(token)
    record_share_viewed()
    
    return StreamingResponse(
        io.BytesIO(plain), 
        media_type=img.content_type or "image/jpeg"
    )
