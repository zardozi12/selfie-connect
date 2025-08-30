# app/routers/images.py

import hashlib
import os
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from tortoise.transactions import in_transaction

from app.schemas.image import ImageOut
from app.services.security import require_user, AuthUser
from app.services import encryption, vision, embeddings
from app.services.cloud_storage import storage

from app.models.image import Image
from app.models.face import Face
from app.models.user import User  # for fetching user's DEK


router = APIRouter(prefix="/images", tags=["images"])


async def _get_user(user_id: str) -> User:
    u = await User.filter(id=user_id).first()
    if not u:
        raise HTTPException(status_code=401, detail="User not found")
    return u


@router.post("/upload", response_model=ImageOut)
async def upload_image(
    auth: AuthUser = Depends(require_user),
    file: UploadFile = File(...),
):
    """
    Upload an image for the authenticated user:
    - Extract EXIF/GPS
    - Create embeddings
    - Encrypt bytes with user's DEK and store
    - Record faces (bounding boxes)
    - Upsert embedding into pgvector table if present
    """
    # ---- read & checksum (dedupe) ----
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    checksum = hashlib.sha256(content).hexdigest()
    existing = await Image.filter(checksum_sha256=checksum, user_id=auth.user_id).first()
    if existing:
        # already stored; return existing metadata
        return ImageOut.model_validate(existing.__dict__)

    # ---- analyze ----
    proc = await vision.analyze(content)

    # ---- embeddings (CPU/CLIP or phash) ----
    rgb_np = await vision.to_rgb_np(content)
    emb = embeddings.image_embedding(rgb_np)

    # ---- geocode (optional) ----
    loc_text = None
    if proc.lat and proc.lng:
        try:
            from app.services.geocode import reverse as geocode_reverse
            loc_text = await geocode_reverse(proc.lat, proc.lng)
        except Exception:
            loc_text = None

    # ---- encrypt before save (FIX) ----
    user = await _get_user(auth.user_id)
    dek_b64 = encryption.unwrap_dek(user.dek_encrypted_b64)
    fernet = encryption.fernet_from_dek(dek_b64)
    encrypted_bytes = fernet.encrypt(content)

    # ---- persist encrypted blob ----
    safe_name = (file.filename or "image").replace(os.sep, "_")
    filename = f"{checksum[:8]}_{safe_name}"
    storage_key = await storage.save(str(auth.user_id), filename, encrypted_bytes)

    # ---- create DB row ----
    img = await Image.create(
        user_id=auth.user_id,
        original_filename=file.filename,
        content_type=file.content_type or "image/jpeg",
        size_bytes=len(content),
        width=proc.width,
        height=proc.height,
        gps_lat=proc.lat,
        gps_lng=proc.lng,
        location_text=loc_text,
        storage_key=storage_key,
        checksum_sha256=checksum,
        embedding_json=emb,
    )

    # ---- faces ----
    for (x, y, w, h) in proc.faces:
        await Face.create(image=img, x=x, y=y, w=w, h=h)

    # ---- optional: pgvector upsert (skip silently if not available) ----
    try:
        async with in_transaction() as conn:
            await conn.execute_query(
                """
                INSERT INTO image_embeddings (image_id, embedding)
                VALUES ($1, $2::vector)
                ON CONFLICT (image_id) DO UPDATE SET embedding = EXCLUDED.embedding
                """,
                [str(img.id), emb],
            )
    except Exception:
        # No pgvector table/extension? That's fine for the demo.
        pass

    # ---- auto-generate albums in background (non-blocking) ----
    try:
        from app.services.album_service import AlbumService
        # This will run in background and won't block the response
        import asyncio
        asyncio.create_task(AlbumService.auto_generate_all_albums(str(auth.user_id)))
    except Exception:
        # Album generation failed, but don't fail the upload
        pass

    return ImageOut.model_validate(img.__dict__)


@router.get("/list", response_model=List[ImageOut])
async def list_images(auth: AuthUser = Depends(require_user)):
    images = await Image.filter(user_id=auth.user_id).order_by("-created_at").all()
    return [ImageOut.model_validate(i.__dict__) for i in images]


@router.get("/{image_id}/view")
async def view_image(image_id: str, auth: AuthUser = Depends(require_user)):
    img = await Image.filter(id=image_id, user_id=auth.user_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Not found")

    enc = await storage.read(img.storage_key)

    # decrypt with user's DEK
    user = await _get_user(auth.user_id)
    dek_b64 = encryption.unwrap_dek(user.dek_encrypted_b64)
    fernet = encryption.fernet_from_dek(dek_b64)
    try:
        plain = fernet.decrypt(enc)
    except Exception:
        raise HTTPException(status_code=500, detail="Decryption failed")

    return StreamingResponse(iter([plain]), media_type=img.content_type or "image/jpeg")
