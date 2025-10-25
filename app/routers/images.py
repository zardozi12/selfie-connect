# app/routers/images.py

import hashlib
import io
import os
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, Request, Header
from fastapi.responses import StreamingResponse
from typing import Optional
from app.schemas.image import ImageOut
from app.consolidated_services import require_user, AuthUser
from app.services import encryption, vision, embeddings
from app.services.deta_storage import storage
from app.services.upload_validate import validate_and_process_upload
from app.services.observability import trace_operation, record_upload, record_error
from app.models.image import Image
from app.models.face import Face
from app.models.user import User

router = APIRouter(prefix="/images", tags=["images"])


async def _get_user(user_id: str) -> User:
    u = await User.filter(id=user_id).first()
    if not u:
        raise HTTPException(status_code=401, detail="User not found")
    return u


# Module: app/routers/api.py — top imports and APIRouter
from __future__ import annotations


# Method: upload_image()
@router.post("/upload", response_model=ImageOut)
async def upload_image(
    request: Request,
    auth: AuthUser = Depends(require_user),
    file: UploadFile = File(...),
    x_csrf_token: Optional[str] = Header(default=None, alias="X-CSRF-Token"),
):
    # Import CSRF validation function
    # Local import to avoid circular import issues
    from app.routers.auth import validate_csrf_request
    validate_csrf_request(request, x_csrf_token)

    content = await validate_and_process_upload(file)
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    checksum = hashlib.sha256(content).hexdigest()
    existing = await Image.filter(checksum_sha256=checksum, user_id=auth.user_id).first()
    if existing:
        # Return with basic AI fields (derived) for consistency
        fc = await Face.filter(image_id=existing.id).count()
        return ImageOut(
            id=existing.id,
            original_filename=existing.original_filename,
            width=existing.width,
            height=existing.height,
            gps_lat=existing.gps_lat,
            gps_lng=existing.gps_lng,
            location_text=existing.location_text,
            created_at=existing.created_at,
            tags=None,
            categories=None,
            contains_faces=fc > 0,
            face_count=fc,
        )

    proc = await vision.analyze(content)
    rgb_np = await vision.to_rgb_np(content)
    emb = embeddings.image_embedding(rgb_np)

    loc_text = None
    if proc.lat and proc.lng:
        try:
            from app.services.geocode import reverse as geocode_reverse
            loc_text = await geocode_reverse(proc.lat, proc.lng)
        except Exception:
            loc_text = None

    user = await _get_user(auth.user_id)
    dek_b64 = encryption.unwrap_dek(user.dek_encrypted_b64)
    fernet = encryption.fernet_from_dek(dek_b64)
    encrypted_bytes = fernet.encrypt(content)

    safe_name = (file.filename or "image").replace(os.sep, "_")
    filename = f"{checksum[:8]}_{safe_name}"
    storage_key = storage.save(str(auth.user_id), filename, encrypted_bytes)

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
        embedding_json=emb.tolist() if hasattr(emb, "tolist") else emb,
    )

    # Persist faces with optional embeddings (if available)
    faces_objs = []
    for (x, y, w, h) in proc.faces:
        fobj = await Face.create(image=img, x=x, y=y, w=w, h=h)
        faces_objs.append(fobj)

    try:
        # Optional per-face embeddings (face_recognition when available)
        faces_embeddings = embeddings.get_image_embedding(content)
        if faces_embeddings and len(faces_embeddings) == len(faces_objs):
            for fobj, vec in zip(faces_objs, faces_embeddings):
                fobj.embedding_json = vec.tolist() if hasattr(vec, "tolist") else list(map(float, vec))
                await fobj.save()
    except Exception:
        pass

    # Store vector for fast search when pgvector is available
    try:
        from app.services.vector_store import upsert_image_vector
        await upsert_image_vector(str(img.id), img.embedding_json)
    except Exception:
        pass

    # Derive simple AI metadata for immediate response
    tags = []
    if loc_text:
        tags.append(loc_text)
    categories = []
    if len(proc.faces) > 0:
        categories.append("people")

    return ImageOut(
        id=img.id,
        original_filename=img.original_filename,
        width=img.width,
        height=img.height,
        gps_lat=img.gps_lat,
        gps_lng=img.gps_lng,
        location_text=img.location_text,
        created_at=img.created_at,
        tags=tags or None,
        categories=categories or None,
        contains_faces=len(proc.faces) > 0,
        face_count=len(proc.faces),
    )


@router.get("/", response_model=List[ImageOut])
async def list_images(
    response: Response,
    auth: AuthUser = Depends(require_user),
    skip: int = 0,
    limit: int = 100,
):
    query = Image.filter(user_id=auth.user_id).order_by("-created_at")
    total = await query.count()
    images = await query.offset(skip).limit(limit).all()
    response.headers["X-Total-Count"] = str(total)
    return [ImageOut.model_validate(i) for i in images]


# Method: view_image()
@router.get("/{image_id}/view")
async def view_image(image_id: str, auth: AuthUser = Depends(require_user)):
    img = await Image.filter(id=image_id, user_id=auth.user_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Not found")

    enc = storage.read(img.storage_key)

    user = await _get_user(auth.user_id)
    dek_b64 = encryption.unwrap_dek(user.dek_encrypted_b64)
    fernet = encryption.fernet_from_dek(dek_b64)
    try:
        plain = fernet.decrypt(enc)
    except (ValueError, TypeError, OSError) as e:
        import logging
        logging.error(f"Image decryption failed for image {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Decryption failed")

    return StreamingResponse(
        iter([plain]),
        media_type=img.content_type or "image/jpeg",
        headers={
            "Cache-Control": "private, max-age=3600",
            "ETag": f"\"{img.checksum_sha256}\"",
            "Last-Modified": img.created_at.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        },
    )


# Method: view_thumb()
@router.get("/{image_id}/thumb")
async def view_thumb(image_id: UUID, auth: AuthUser = Depends(require_user)):
    """View thumbnail of an image"""
    img = await Image.filter(id=image_id, user_id=auth.user_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    user = await _get_user(auth.user_id)
    dek_b64 = encryption.unwrap_dek(user.dek_encrypted_b64)
    fernet = encryption.fernet_from_dek(dek_b64)

    key = img.thumb_storage_key or img.storage_key
    enc = storage.read(key)

    try:
        plain = fernet.decrypt(enc)
    except (ValueError, TypeError, OSError) as e:
        import logging
        logging.error(f"Thumbnail decryption failed for image {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Decryption failed")

    return StreamingResponse(
        io.BytesIO(plain),
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, max-age=7200",
            "ETag": f"\"{img.checksum_sha256}-thumb\"",
            "Last-Modified": img.created_at.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        },
    )


@router.delete("/{image_id}")
async def delete_image(image_id: str, auth: AuthUser = Depends(require_user)):
    img = await Image.filter(id=image_id, user_id=auth.user_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Not found")

    storage.delete(img.storage_key)
    if img.thumb_storage_key:
        storage.delete(img.thumb_storage_key)

    await img.delete()

    return {"ok": True}
