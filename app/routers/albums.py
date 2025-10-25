from fastapi import APIRouter, HTTPException, Depends
from app.models.album import Album
from app.models.user import User
from app.services.qr import generate_qr_code
from app.models.album import Album
from app.models.album import AlbumImage
from app.models.face import Face
from app.models.user import PersonCluster
from app.consolidated_services import require_user, AuthUser
from app.services.album_service import AlbumService
from app.schemas.image import AlbumOut, AlbumGroup, PersonClusterOut, ImageOut
from app.services.ai_metadata_store import list_metadata
import io
from typing import List, Optional
from uuid import UUID
from fastapi.responses import StreamingResponse
from app.models.image import Image

router = APIRouter(prefix="/albums", tags=["albums"])

@router.get("/{album_id}/qr")
async def get_album_qr(album_id: UUID, auth: AuthUser = Depends(require_user)):
    album = await Album.filter(id=album_id, user_id=auth.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    qr_bytes = generate_qr_code(f"album:{album_id}")
    return StreamingResponse(io.BytesIO(qr_bytes), media_type="image/png")

@router.get("/", response_model=List[AlbumOut])
async def list_albums(auth: AuthUser = Depends(require_user)):
    albums = await Album.filter(user_id=auth.user_id).prefetch_related("cover_image").all()
    result: List[AlbumOut] = []
    for album in albums:
        image_count = await AlbumImage.filter(album=album).count()
        result.append(AlbumOut(
            id=album.id,
            name=album.name,
            description=album.description,
            album_type=album.album_type,
            location_text=album.location_text,
            gps_lat=album.gps_lat,
            gps_lng=album.gps_lng,
            start_date=album.start_date,
            end_date=album.end_date,
            is_auto_generated=album.is_auto_generated,
            cover_image_id=album.cover_image.id if album.cover_image else None,
            image_count=image_count,
            created_at=album.created_at,
        ))
    return result

@router.get("/{album_id}", response_model=AlbumOut)
async def get_album(album_id: str, auth: AuthUser = Depends(require_user)):
    album = await Album.filter(id=album_id, user_id=auth.user_id).prefetch_related("cover_image").first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    image_count = await AlbumImage.filter(album=album).count()
    return AlbumOut(
        id=album.id,
        name=album.name,
        description=album.description,
        album_type=album.album_type,
        location_text=album.location_text,
        gps_lat=album.gps_lat,
        gps_lng=album.gps_lng,
        start_date=album.start_date,
        end_date=album.end_date,
        is_auto_generated=album.is_auto_generated,
        cover_image_id=album.cover_image.id if album.cover_image else None,
        image_count=image_count,
        created_at=album.created_at,
    )

@router.get("/{album_id}/images", response_model=List[ImageOut])
async def get_album_images(album_id: str, auth: AuthUser = Depends(require_user)):
    album = await Album.filter(id=album_id, user_id=auth.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    album_images = await AlbumImage.filter(album=album).prefetch_related("image").all()
    return [
        ImageOut(
            id=a.image.id,
            original_filename=a.image.original_filename,
            width=a.image.width,
            height=a.image.height,
            gps_lat=a.image.gps_lat,
            gps_lng=a.image.gps_lng,
            location_text=a.image.location_text,
            created_at=a.image.created_at,
        )
        for a in album_images if a.image
    ]

@router.post("/auto-generate")
async def auto_generate_albums(auth: AuthUser = Depends(require_user)):
    try:
        results = await AlbumService.auto_generate_all_albums(str(auth.user_id))
        return {
            "message": "Albums generated successfully",
            "location_albums_created": len(results["location_albums"]),
            "date_albums_created": len(results["date_albums"]),
            "person_clusters_created": len(results["person_clusters"]),
            "person_albums_created": len(results["person_albums"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate albums: {str(e)}")

@router.post("/auto-categorize")
async def auto_categorize_albums(auth: AuthUser = Depends(require_user)):
    """Automatically organize images into category albums using AI metadata."""
    try:
        # Collect metadata per image
        meta_by_image = list_metadata(str(auth.user_id))
        if not meta_by_image:
            return {"message": "No AI metadata available yet", "created": []}

        # Map category -> image_ids
        groups: dict[str, List[str]] = {}
        for image_id, meta in meta_by_image.items():
            cats = meta.get("categories") or []
            for c in cats:
                key = c.strip().title()  # e.g., "people" -> "People"
                groups.setdefault(key, []).append(image_id)

        created_or_updated = []
        for cat_name, image_ids in groups.items():
            album, _ = await Album.get_or_create(user_id=auth.user_id, name=cat_name, defaults={"description": f"Auto {cat_name} album"})
            # Add images
            for iid in image_ids:
                img = await Image.filter(id=iid, user_id=auth.user_id).first()
                if img:
                    exists = await AlbumImage.filter(album_id=album.id, image_id=img.id).exists()
                    if not exists:
                        await AlbumImage.create(album=album, image=img)
            created_or_updated.append({"album": cat_name, "count": len(image_ids)})

        return {
            "message": "Categorized albums updated",
            "created_or_updated": created_or_updated,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to auto-categorize: {str(e)}")

@router.post("/manual", response_model=AlbumOut)
async def create_manual_album(
    name: str,
    description: Optional[str] = None,
    image_ids: Optional[List[str]] = None,
    auth: AuthUser = Depends(require_user),
):
    if not name:
        raise HTTPException(status_code=400, detail="Album name is required")

    existing = await Album.filter(user_id=auth.user_id, name=name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Album with this name already exists")

    album = await Album.create(
        user_id=auth.user_id,
        name=name,
        description=description,
        album_type="manual",
        is_auto_generated=False,
    )

    if image_ids:
        for image_id in image_ids:
            image = await Image.filter(id=image_id, user_id=auth.user_id).first()
            if image:
                await AlbumImage.create(album=album, image=image)

        first_image = await Image.filter(id=image_ids[0], user_id=auth.user_id).first()
        if first_image:
            album.cover_image = first_image
            await album.save()

    return AlbumOut(
        id=album.id,
        name=album.name,
        description=album.description,
        album_type=album.album_type,
        location_text=album.location_text,
        gps_lat=album.gps_lat,
        gps_lng=album.gps_lng,
        start_date=album.start_date,
        end_date=album.end_date,
        is_auto_generated=album.is_auto_generated,
        cover_image_id=album.cover_image.id if album.cover_image else None,
        image_count=len(image_ids) if image_ids else 0,
        created_at=album.created_at,
    )

@router.post("/{album_id}/add-images")
async def add_images_to_album(album_id: str, image_ids: List[str], auth: AuthUser = Depends(require_user)):
    album = await Album.filter(id=album_id, user_id=auth.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    added = 0
    for iid in image_ids:
        image = await Image.filter(id=iid, user_id=auth.user_id).first()
        if not image:
            continue
        exists = await AlbumImage.filter(album=album, image=image).first()
        if not exists:
            await AlbumImage.create(album=album, image=image)
            added += 1
    return {"message": f"Added {added} images to album"}

# ---------- NEW: alias so /add-image (singular) also works ----------
@router.post("/{album_id}/add-image")
async def add_image_alias(album_id: str, image_id: str, auth: AuthUser = Depends(require_user)):
    return await add_images_to_album(album_id, [image_id], auth)

@router.delete("/{album_id}/remove-images")
async def remove_images_from_album(album_id: str, image_ids: List[str], auth: AuthUser = Depends(require_user)):
    album = await Album.filter(id=album_id, user_id=auth.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    removed = 0
    for iid in image_ids:
        image = await Image.filter(id=iid, user_id=auth.user_id).first()
        if not image:
            continue
        link = await AlbumImage.filter(album=album, image=image).first()
        if link:
            await link.delete()
            removed += 1
    return {"message": f"Removed {removed} images from album"}

@router.delete("/{album_id}")
async def delete_album(album_id: str, auth: AuthUser = Depends(require_user)):
    album = await Album.filter(id=album_id, user_id=auth.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    if album.is_auto_generated:
        raise HTTPException(status_code=400, detail="Cannot delete auto-generated albums")
    await album.delete()
    return {"message": "Album deleted successfully"}
