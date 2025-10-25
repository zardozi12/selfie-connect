from __future__ import annotations
import io
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import qrcode

from app.services.security import require_admin
from app.models.album import Album
from app.models.user import User
from app.services.shares import create_share_jwt, record_share, revoke_share, get_share_stats
from app.services.audit import audit, AuditActions, SubjectTypes
from app.services.metrics import record_share_created

admin_api = APIRouter(prefix="/admin", tags=["admin"])

@admin_api.get("/person-albums")
async def list_person_albums_admin(_: User = Depends(require_admin)):
    """List all person albums (admin only)"""
    albums = await Album.filter(album_type="person").order_by("-created_at").all()
    return [{"id": str(a.id), "name": a.name, "user_id": str(a.user_id)} for a in albums]

@admin_api.post("/person-albums/{album_id}/share")
async def create_share(
    album_id: UUID, 
    hours: int = Query(72, ge=1, le=24*30), 
    max_views: int | None = Query(None), 
    admin: User = Depends(require_admin)
):
    """Create a share link for a person album (admin only)"""
    album = await Album.filter(id=album_id).first()
    if not album or album.album_type != "person":
        raise HTTPException(status_code=404, detail="Person album not found")
    
    # Create JWT token
    token = create_share_jwt(str(album.user_id), str(album.id), hours)
    
    # Record in database
    share_id = await record_share(str(album.id), str(admin.id), token, hours, max_views=max_views)
    
    # Log audit event
    await audit(str(admin.id), AuditActions.CREATE_SHARE, SubjectTypes.ALBUM, str(album.id))
    
    # Record metrics
    record_share_created()
    
    url = f"/share/{token}"
    return {
        "share_id": share_id, 
        "share_url": url, 
        "expires_in_hours": hours, 
        "max_views": max_views
    }

@admin_api.post("/shares/{share_id}/revoke")
async def revoke(share_id: UUID, admin: User = Depends(require_admin)):
    """Revoke a share link (admin only)"""
    await revoke_share(str(share_id))
    
    # Log audit event
    await audit(str(admin.id), AuditActions.REVOKE_SHARE, SubjectTypes.SHARE, str(share_id))
    
    return {"revoked": True}

@admin_api.get("/shares/{share_id}/stats")
async def share_stats(share_id: UUID, _: User = Depends(require_admin)):
    """Get statistics for a share link (admin only)"""
    stats = await get_share_stats(str(share_id))
    if not stats:
        raise HTTPException(status_code=404, detail="Share not found")
    return stats

@admin_api.get("/person-albums/{album_id}/share/qr")
async def share_qr(
    album_id: UUID, 
    hours: int = Query(72, ge=1, le=24*30), 
    max_views: int | None = Query(None), 
    admin: User = Depends(require_admin)
):
    """Generate QR code for share link (admin only)"""
    album = await Album.filter(id=album_id).first()
    if not album or album.album_type != "person":
        raise HTTPException(status_code=404, detail="Person album not found")
    
    # Create JWT token and record share
    token = create_share_jwt(str(album.user_id), str(album.id), hours)
    await record_share(str(album.id), str(admin.id), token, hours, max_views=max_views)
    
    # Log audit event
    await audit(str(admin.id), AuditActions.CREATE_SHARE, SubjectTypes.ALBUM, str(album.id))
    
    # Record metrics
    record_share_created()
    
    # Generate QR code
    url = f"/share/{token}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

