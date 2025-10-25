from fastapi import APIRouter, HTTPException, Depends, Body, UploadFile, File
from typing import Optional
from app.consolidated_services import require_user, AuthUser
from app.models.user import User
from app.models.album import Album
from app.services.shares import create_share_jwt, record_share, validate_share
from app.services.metrics import record_share_created
from app.services.faceapi import verify_face

router = APIRouter(prefix="/api/link", tags=["share"])

@router.post("/create")
async def link_create(
    album_id: str = Body(...),
    hours: int = Body(default=60),  # default 1 hour
    max_views: Optional[int] = Body(default=None),
    user: AuthUser = Depends(require_user),
):
    """
    Create a secure share link for an album.
    Returns `/share/{token}` compatible with existing public endpoints.
    """
    album = await Album.filter(id=album_id, user_id=user.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    token = create_share_jwt(user.user_id, album_id, hours)
    share_id = await record_share(album_id, user.user_id, token, hours, max_views=max_views)
    record_share_created()
    return {
        "share_id": share_id,
        "expires_in_hours": hours,
        "share_url": f"/share/{token}",
    }

@router.post("/verify")
async def link_verify(token: str = Body(...), image: UploadFile = File(...)):
    """
    Verify a share link by facial scan.
    Checks the owner's saved face against the provided image.
    """
    val = await validate_share(token)
    if not val:
        raise HTTPException(status_code=401, detail="Invalid or expired link")
    sub_user_id = val["jwt"]["sub"]

    user = await User.filter(id=sub_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    meta = user.face_embedding_json or {}
    content = await image.read()
    ok, conf = await verify_face(meta.get("face_api_id"), meta.get("vector"), content)
    if not ok:
        raise HTTPException(status_code=403, detail=f"Face verification failed (confidence={conf:.4f})")
    return {"access_granted": True, "confidence": conf, "album_id": val["jwt"]["alb"], "expires_at": val["share"]["expires_at"]}