from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.models.image import Image
from app.models.album import Album, AlbumImage
from app.models.face import Face
from app.models.user import PersonCluster
from app.services.security import require_user, AuthUser
from app.services.album_service import AlbumService
from app.schemas.image import AlbumOut, AlbumGroup, PersonClusterOut, ImageOut
from tortoise.expressions import Q


router = APIRouter(prefix="/albums", tags=["albums"])


@router.get("/", response_model=List[AlbumOut])
async def list_albums(auth: AuthUser = Depends(require_user)):
    """Get all albums for the user"""
    albums = await Album.filter(user_id=auth.user_id).prefetch_related("cover_image").all()
    
    result = []
    for album in albums:
        # Get image count
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
            created_at=album.created_at
        ))
    
    return result


@router.get("/{album_id}", response_model=AlbumOut)
async def get_album(album_id: str, auth: AuthUser = Depends(require_user)):
    """Get a specific album with its images"""
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
        created_at=album.created_at
    )


@router.get("/{album_id}/images", response_model=List[ImageOut])
async def get_album_images(album_id: str, auth: AuthUser = Depends(require_user)):
    """Get all images in an album"""
    # Verify album belongs to user
    album = await Album.filter(id=album_id, user_id=auth.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Get album images
    album_images = await AlbumImage.filter(album=album).prefetch_related("image").all()
    
    result = []
    for album_img in album_images:
        img = album_img.image
        result.append(ImageOut(
            id=img.id,
            original_filename=img.original_filename,
            width=img.width,
            height=img.height,
            gps_lat=img.gps_lat,
            gps_lng=img.gps_lng,
            location_text=img.location_text,
            created_at=img.created_at
        ))
    
    return result


@router.post("/auto-generate")
async def auto_generate_albums(auth: AuthUser = Depends(require_user)):
    """Automatically generate albums based on location, date, and person clustering"""
    try:
        results = await AlbumService.auto_generate_all_albums(str(auth.user_id))
        
        return {
            "message": "Albums generated successfully",
            "location_albums_created": len(results["location_albums"]),
            "date_albums_created": len(results["date_albums"]),
            "person_clusters_created": len(results["person_clusters"]),
            "person_albums_created": len(results["person_albums"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate albums: {str(e)}")


@router.get("/by-location", response_model=List[AlbumGroup])
async def albums_by_location(auth: AuthUser = Depends(require_user)):
    """Get images grouped by location"""
    images = await Image.filter(user_id=auth.user_id).all()
    groups = {}
    for i in images:
        key = i.location_text or (f"{i.gps_lat:.5f},{i.gps_lng:.5f}" if i.gps_lat and i.gps_lng else "Unknown")
        groups.setdefault(key, []).append(str(i.id))
    
    out = [AlbumGroup(key=k, count=len(v), image_ids=v) for k, v in groups.items()]
    out.sort(key=lambda g: g.count, reverse=True)
    return out


@router.get("/by-date", response_model=List[AlbumGroup])
async def albums_by_date(auth: AuthUser = Depends(require_user)):
    """Get images grouped by date (month/year)"""
    images = await Image.filter(user_id=auth.user_id).order_by("-created_at").all()
    groups = {}
    for i in images:
        if i.created_at:
            key = i.created_at.strftime("%B %Y")  # e.g., "January 2024"
            groups.setdefault(key, []).append(str(i.id))
    
    out = [AlbumGroup(key=k, count=len(v), image_ids=v) for k, v in groups.items()]
    out.sort(key=lambda g: g.count, reverse=True)
    return out


@router.get("/persons", response_model=List[PersonClusterOut])
async def get_person_clusters(auth: AuthUser = Depends(require_user)):
    """Get all person clusters for the user"""
    clusters = await PersonCluster.filter(user_id=auth.user_id).prefetch_related("faces").all()
    
    result = []
    for cluster in clusters:
        result.append(PersonClusterOut(
            id=cluster.id,
            label=cluster.label,
            faces=len(cluster.faces)
        ))
    
    return result


@router.post("/manual", response_model=AlbumOut)
async def create_manual_album(
    name: str,
    description: str = None,
    image_ids: List[str] = None,
    auth: AuthUser = Depends(require_user)
):
    """Create a manual album"""
    if not name:
        raise HTTPException(status_code=400, detail="Album name is required")
    
    # Check if album name already exists
    existing = await Album.filter(user_id=auth.user_id, name=name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Album with this name already exists")
    
    # Create album
    album = await Album.create(
        user_id=auth.user_id,
        name=name,
        description=description,
        album_type="manual",
        is_auto_generated=False
    )
    
    # Add images if provided
    if image_ids:
        for image_id in image_ids:
            # Verify image belongs to user
            image = await Image.filter(id=image_id, user_id=auth.user_id).first()
            if image:
                await AlbumImage.create(album=album, image=image)
    
    # Set cover image if images were added
    if image_ids:
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
        created_at=album.created_at
    )


@router.post("/{album_id}/add-images")
async def add_images_to_album(
    album_id: str,
    image_ids: List[str],
    auth: AuthUser = Depends(require_user)
):
    """Add images to an existing album"""
    # Verify album belongs to user
    album = await Album.filter(id=album_id, user_id=auth.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    added_count = 0
    for image_id in image_ids:
        # Verify image belongs to user
        image = await Image.filter(id=image_id, user_id=auth.user_id).first()
        if image:
            # Check if already in album
            existing = await AlbumImage.filter(album=album, image=image).first()
            if not existing:
                await AlbumImage.create(album=album, image=image)
                added_count += 1
    
    return {"message": f"Added {added_count} images to album"}


@router.delete("/{album_id}/remove-images")
async def remove_images_from_album(
    album_id: str,
    image_ids: List[str],
    auth: AuthUser = Depends(require_user)
):
    """Remove images from an album"""
    # Verify album belongs to user
    album = await Album.filter(id=album_id, user_id=auth.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    removed_count = 0
    for image_id in image_ids:
        image = await Image.filter(id=image_id, user_id=auth.user_id).first()
        if image:
            album_image = await AlbumImage.filter(album=album, image=image).first()
            if album_image:
                await album_image.delete()
                removed_count += 1
    
    return {"message": f"Removed {removed_count} images from album"}


@router.delete("/{album_id}")
async def delete_album(album_id: str, auth: AuthUser = Depends(require_user)):
    """Delete an album (only manual albums can be deleted)"""
    album = await Album.filter(id=album_id, user_id=auth.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    if album.is_auto_generated:
        raise HTTPException(status_code=400, detail="Cannot delete auto-generated albums")
    
    # Delete album (AlbumImage relationships will be deleted automatically due to CASCADE)
    await album.delete()
    
    return {"message": "Album deleted successfully"}