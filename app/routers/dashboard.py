# from fastapi import APIRouter, Depends, HTTPException
# from typing import List, Dict, Any
# from app.models.image import Image
# from app.models.album import Album, AlbumImage
# from app.models.face import Face
# from app.models.user import PersonCluster
# from app.consolidated_services import require_user, AuthUser, get_audit_logs
# from app.schemas.image import ImageOut, AlbumOut, PersonClusterOut
# from tortoise.expressions import Q
# from datetime import datetime, timedelta


# router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# @router.get("/stats")
# async def get_dashboard_stats(auth: AuthUser = Depends(require_user)):
#     """Get comprehensive dashboard statistics"""
#     # Lightweight cache to reduce DB load under repeated dashboard opens
#     try:
#         from app.services.cache import cache_get_json, cache_set_json  # lazy import if redis installed
#         cache_key = f"dash:{auth.user_id}"
#         cached = None
#         if cache_get_json:
#             cached = await cache_get_json(cache_key)
#         if cached:
#             return cached
#     except Exception:
#         cached = None
    
#     # Basic counts
#     total_images = await Image.filter(user_id=auth.user_id).count()
#     total_albums = await Album.filter(user_id=auth.user_id).count()
#     total_faces = await Face.filter(image__user_id=auth.user_id).count()
#     total_persons = await PersonCluster.filter(user_id=auth.user_id).count()
    
#     # Storage usage (approximate)
#     total_size = await Image.filter(user_id=auth.user_id).aggregate(
#         total_size=Q.sum("size_bytes")
#     )
#     total_size_mb = (total_size["total_size"] or 0) / (1024 * 1024)
    
#     # Recent activity
#     last_week = datetime.now() - timedelta(days=7)
#     recent_uploads = await Image.filter(
#         user_id=auth.user_id,
#         created_at__gte=last_week
#     ).count()
    
#     # Albums by type
#     album_types = await Album.filter(user_id=auth.user_id).group_by("album_type").annotate(
#         count=Q.count("id")
#     ).values("album_type", "count")
    
#     # Location stats
#     locations_with_images = await Image.filter(
#         user_id=auth.user_id,
#         location_text__not_isnull=True
#     ).distinct().values_list("location_text", flat=True)
    
#     # Recent images
#     recent_images = await Image.filter(
#         user_id=auth.user_id
#     ).order_by("-created_at").limit(10).all()
    
#     recent_image_data = []
#     for img in recent_images:
#         recent_image_data.append(ImageOut(
#             id=img.id,
#             original_filename=img.original_filename,
#             width=img.width,
#             height=img.height,
#             gps_lat=img.gps_lat,
#             gps_lng=img.gps_lng,
#             location_text=img.location_text,
#             created_at=img.created_at
#         ))
    
#     result = {
#         "total_images": total_images,
#         "total_albums": total_albums,
#         "total_faces": total_faces,
#         "total_persons": total_persons,
#         "total_storage_mb": round(total_size_mb, 2),
#         "recent_uploads": recent_uploads,
#         "album_types": album_types,
#         "unique_locations": len(locations_with_images),
#         "recent_images": recent_image_data
#     }
#     try:
#         if cache_get_json and cache_set_json:
#             await cache_set_json(cache_key, result, ttl=60)
#     except Exception:
#         pass
#     return result


# @router.get("/recent-activity")
# async def get_recent_activity(auth: AuthUser = Depends(require_user)):
#     """Get recent activity including uploads and album changes"""
    
#     # Recent image uploads
#     recent_images = await Image.filter(
#         user_id=auth.user_id
#     ).order_by("-created_at").limit(20).all()
    
#     # Recent album changes
#     recent_albums = await Album.filter(
#         user_id=auth.user_id
#     ).order_by("-created_at").limit(10).all()
    
#     # Recent person clusters
#     recent_clusters = await PersonCluster.filter(
#         user_id=auth.user_id
#     ).order_by("-created_at").limit(5).all()
    
#     activity = []
    
#     # Add image uploads
#     for img in recent_images:
#         activity.append({
#             "type": "image_upload",
#             "timestamp": img.created_at,
#             "title": f"Uploaded {img.original_filename or 'image'}",
#             "details": {
#                 "image_id": str(img.id),
#                 "location": img.location_text,
#                 "size_mb": round((img.size_bytes or 0) / (1024 * 1024), 2)
#             }
#         })
    
#     # Add album creations
#     for album in recent_albums:
#         activity.append({
#             "type": "album_created",
#             "timestamp": album.created_at,
#             "title": f"Created album '{album.name}'",
#             "details": {
#                 "album_id": str(album.id),
#                 "album_type": album.album_type,
#                 "is_auto_generated": album.is_auto_generated
#             }
#         })
    
#     # Add person clusters
#     for cluster in recent_clusters:
#         activity.append({
#             "type": "person_clustered",
#             "timestamp": cluster.created_at,
#             "title": f"Identified person '{cluster.label}'",
#             "details": {
#                 "cluster_id": str(cluster.id),
#                 "face_count": await Face.filter(cluster=cluster).count()
#             }
#         })
    
#     # Sort by timestamp
#     activity.sort(key=lambda x: x["timestamp"], reverse=True)
    
#     return {
#         "activity": activity[:30]  # Return top 30 activities
#     }


# @router.get("/search-suggestions")
# async def get_search_suggestions(auth: AuthUser = Depends(require_user)):
#     """Get search suggestions based on user's data"""
    
#     # Location suggestions
#     locations = await Image.filter(
#         user_id=auth.user_id,
#         location_text__not_isnull=True
#     ).distinct().values_list("location_text", flat=True)
    
#     # Person suggestions
#     persons = await PersonCluster.filter(user_id=auth.user_id).values_list("label", flat=True)
    
#     # Album suggestions
#     albums = await Album.filter(user_id=auth.user_id).values_list("name", flat=True)
    
#     # Date suggestions (months/years)
#     images_with_dates = await Image.filter(
#         user_id=auth.user_id,
#         created_at__not_isnull=True
#     ).order_by("-created_at").all()
    
#     date_suggestions = []
#     for img in images_with_dates:
#         if img.created_at:
#             month_year = img.created_at.strftime("%B %Y")
#             if month_year not in date_suggestions:
#                 date_suggestions.append(month_year)
    
#     return {
#         "locations": list(locations),
#         "persons": list(persons),
#         "albums": list(albums),
#         "dates": date_suggestions[:12]  # Last 12 months
#     }


# @router.get("/storage-analysis")
# async def get_storage_analysis(auth: AuthUser = Depends(require_user)):
#     """Get detailed storage analysis"""
    
#     # Storage by month
#     images = await Image.filter(user_id=auth.user_id).order_by("created_at").all()
    
#     monthly_storage = {}
#     for img in images:
#         if img.created_at and img.size_bytes:
#             month_key = img.created_at.strftime("%Y-%m")
#             if month_key not in monthly_storage:
#                 monthly_storage[month_key] = {
#                     "size_bytes": 0,
#                     "count": 0
#                 }
#             monthly_storage[month_key]["size_bytes"] += img.size_bytes
#             monthly_storage[month_key]["count"] += 1
    
#     # Convert to MB and format
#     monthly_data = []
#     for month, data in monthly_storage.items():
#         monthly_data.append({
#             "month": month,
#             "size_mb": round(data["size_bytes"] / (1024 * 1024), 2),
#             "count": data["count"]
#         })
    
#     # Storage by location
#     location_storage = {}
#     for img in images:
#         if img.size_bytes:
#             location = img.location_text or "Unknown"
#             if location not in location_storage:
#                 location_storage[location] = {
#                     "size_bytes": 0,
#                     "count": 0
#                 }
#             location_storage[location]["size_bytes"] += img.size_bytes
#             location_storage[location]["count"] += 1
    
#     location_data = []
#     for location, data in location_storage.items():
#         location_data.append({
#             "location": location,
#             "size_mb": round(data["size_bytes"] / (1024 * 1024), 2),
#             "count": data["count"]
#         })
    
#     # Sort by size
#     location_data.sort(key=lambda x: x["size_mb"], reverse=True)
    
#     return {
#         "monthly_storage": monthly_data,
#         "location_storage": location_data[:10],  # Top 10 locations
#         "total_storage_mb": round(sum(data["size_bytes"] for data in monthly_storage.values()) / (1024 * 1024), 2)
#     }


# @router.get("/person-analysis")
# async def get_person_analysis(auth: AuthUser = Depends(require_user)):
#     """Get analysis of people in photos"""
    
#     # Get all person clusters with their faces
#     clusters = await PersonCluster.filter(user_id=auth.user_id).prefetch_related("faces__image").all()
    
#     person_data = []
#     for cluster in clusters:
#         # Get unique images for this person
#         images = list(set([face.image for face in cluster.faces]))
        
#         # Calculate total size
#         total_size = sum(img.size_bytes or 0 for img in images)
        
#         # Get locations where this person appears
#         locations = list(set([img.location_text for img in images if img.location_text]))
        
#         person_data.append({
#             "cluster_id": str(cluster.id),
#             "label": cluster.label,
#             "face_count": len(cluster.faces),
#             "image_count": len(images),
#             "total_size_mb": round(total_size / (1024 * 1024), 2),
#             "locations": locations,
#             "first_seen": min([img.created_at for img in images]) if images else None,
#             "last_seen": max([img.created_at for img in images]) if images else None
#         })
    
#     # Sort by face count
#     person_data.sort(key=lambda x: x["face_count"], reverse=True)
    
#     return {
#         "persons": person_data,
#         "total_persons": len(person_data),
#         "total_faces": sum(p["face_count"] for p in person_data)
#     }


# @router.get("/location-analysis")
# async def get_location_analysis(auth: AuthUser = Depends(require_user)):
#     """Get analysis of photo locations"""
    
#     # Get all images with location data
#     images = await Image.filter(
#         user_id=auth.user_id,
#         location_text__not_isnull=True
#     ).all()
    
#     location_data = {}
#     for img in images:
#         location = img.location_text
#         if location not in location_data:
#             location_data[location] = {
#                 "count": 0,
#                 "size_bytes": 0,
#                 "first_visit": img.created_at,
#                 "last_visit": img.created_at,
#                 "gps_coordinates": []
#             }
        
#         location_data[location]["count"] += 1
#         location_data[location]["size_bytes"] += img.size_bytes or 0
        
#         if img.created_at < location_data[location]["first_visit"]:
#             location_data[location]["first_visit"] = img.created_at
        
#         if img.created_at > location_data[location]["last_visit"]:
#             location_data[location]["last_visit"] = img.created_at
        
#         if img.gps_lat and img.gps_lng:
#             location_data[location]["gps_coordinates"].append({
#                 "lat": img.gps_lat,
#                 "lng": img.gps_lng
#             })
    
#     # Convert to list and format
#     locations = []
#     for location, data in location_data.items():
#         locations.append({
#             "location": location,
#             "count": data["count"],
#             "size_mb": round(data["size_bytes"] / (1024 * 1024), 2),
#             "first_visit": data["first_visit"],
#             "last_visit": data["last_visit"],
#             "visit_span_days": (data["last_visit"] - data["first_visit"]).days if data["last_visit"] != data["first_visit"] else 0,
#             "gps_coordinates": data["gps_coordinates"]
#         })
    
#     # Sort by count
#     locations.sort(key=lambda x: x["count"], reverse=True)
    
#     return {
#         "locations": locations,
#         "total_locations": len(locations),
#         "total_photos_with_location": len(images)
#     }


# app/routers/dashboard.py
from fastapi import APIRouter, Depends
from typing import List
from datetime import datetime, timedelta

from tortoise.expressions import Q
from tortoise.functions import Sum, Count

from app.models.image import Image
from app.models.album import Album
from app.models.face import Face
from app.models.user import PersonCluster
# Fix import - use consolidated_services
from app.consolidated_services import require_user, AuthUser
from app.schemas.image import ImageOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(auth: AuthUser = Depends(require_user)):
    """Get comprehensive dashboard statistics (cached if Redis layer is present)."""
    # Lightweight cache
    try:
        from app.services.cache import cache_get_json, cache_set_json
        cache_key = f"dash:{auth.user_id}"
        cached = await cache_get_json(cache_key) if cache_get_json else None
        if cached:
            return cached
    except ImportError:
        # Cache service not available
        cached = None
    except (ImportError, ConnectionError, TimeoutError) as e:
        # Log cache error but continue
        import logging
        logging.warning(f"Cache error in dashboard stats: {e}")
        cached = None

    # Basic counts
    total_images = await Image.filter(user_id=auth.user_id).count()
    total_albums = await Album.filter(user_id=auth.user_id).count()
    total_faces = await Face.filter(image__user_id=auth.user_id).count()
    total_persons = await PersonCluster.filter(user_id=auth.user_id).count()

    # Storage usage (approximate)
    total_size = await Image.filter(user_id=auth.user_id).aggregate(total_size=Sum("size_bytes"))
    total_size_mb = (total_size["total_size"] or 0) / (1024 * 1024)

    # Recent activity
    last_week = datetime.now() - timedelta(days=7)
    recent_uploads = await Image.filter(user_id=auth.user_id, created_at__gte=last_week).count()

    # Albums by type
    album_types = await (
        Album.filter(user_id=auth.user_id)
        .group_by("album_type")
        .annotate(count=Count("id"))
        .values("album_type", "count")
    )

    # Location stats (unique locations count)
    locations_with_images = await Image.filter(
        user_id=auth.user_id, location_text__not_isnull=True
    ).distinct().values_list("location_text", flat=True)

    # Recent images
    recent_images = await Image.filter(user_id=auth.user_id).order_by("-created_at").limit(10).all()
    recent_image_data: List[ImageOut] = [
        ImageOut(
            id=img.id,
            original_filename=img.original_filename,
            width=img.width,
            height=img.height,
            gps_lat=img.gps_lat,
            gps_lng=img.gps_lng,
            location_text=img.location_text,
            created_at=img.created_at,
        )
        for img in recent_images
    ]

    # Calculate this month's stats
    this_month = datetime.now().replace(day=1)
    images_this_month = await Image.filter(user_id=auth.user_id, created_at__gte=this_month).count()
    albums_this_month = await Album.filter(user_id=auth.user_id, created_at__gte=this_month).count()
    
    # Calculate average images per album
    avg_images_per_album = round(total_images / total_albums, 1) if total_albums > 0 else 0
    
    # Get most common location
    most_common_location = None
    if locations_with_images:
        location_counts = {}
        for img in await Image.filter(user_id=auth.user_id, location_text__not_isnull=True).all():
            location_counts[img.location_text] = location_counts.get(img.location_text, 0) + 1
        if location_counts:
            most_common_location = max(location_counts, key=location_counts.get)
    
    result = {
        "total_images": total_images,
        "total_albums": total_albums,
        "person_clusters": total_persons,
        "storage_used_mb": round(total_size_mb, 2),
        "images_this_month": images_this_month,
        "albums_this_month": albums_this_month,
        "most_common_location": most_common_location,
        "average_images_per_album": avg_images_per_album,
        "recent_uploads": recent_uploads,
        "album_types": album_types,
        "unique_locations": len(locations_with_images),
        "recent_images": recent_image_data,
    }

    try:
        if cache_get_json and cache_set_json:
            await cache_set_json(cache_key, result, ttl=60)
    except (ConnectionError, TimeoutError, ValueError) as e:
        # Log cache set error but don't fail the request
        import logging
        logging.warning(f"Failed to cache dashboard stats: {e}")
        pass

    return result


@router.get("/recent-activity")
async def get_recent_activity(auth: AuthUser = Depends(require_user)):
    """Get recent activity including uploads and album changes"""
    recent_images = await Image.filter(user_id=auth.user_id).order_by("-created_at").limit(20).all()
    recent_albums = await Album.filter(user_id=auth.user_id).order_by("-created_at").limit(10).all()
    recent_clusters = await PersonCluster.filter(user_id=auth.user_id).order_by("-created_at").limit(5).all()

    activity = []

    for img in recent_images:
        activity.append({
            "id": str(img.id),
            "type": "upload",
            "description": f"Uploaded {img.original_filename or 'image'}",
            "created_at": img.created_at.isoformat(),
        })

    for album in recent_albums:
        activity.append({
            "id": str(album.id),
            "type": "album_created",
            "description": f"Created album '{album.name}'",
            "created_at": album.created_at.isoformat(),
        })

    for cluster in recent_clusters:
        activity.append({
            "id": str(cluster.id),
            "type": "person_renamed",
            "description": f"Identified person '{cluster.label}'",
            "created_at": cluster.created_at.isoformat(),
        })

    activity.sort(key=lambda x: x["created_at"], reverse=True)
    return activity[:30]


@router.get("/search-suggestions")
async def get_search_suggestions(auth: AuthUser = Depends(require_user)):
    """Get search suggestions based on user's data"""
    locations = await Image.filter(
        user_id=auth.user_id, location_text__not_isnull=True
    ).distinct().values_list("location_text", flat=True)

    persons = await PersonCluster.filter(user_id=auth.user_id).values_list("label", flat=True)
    albums = await Album.filter(user_id=auth.user_id).values_list("name", flat=True)

    images_with_dates = await Image.filter(
        user_id=auth.user_id, created_at__not_isnull=True
    ).order_by("-created_at").all()

    date_suggestions = []
    for img in images_with_dates:
        if img.created_at:
            month_year = img.created_at.strftime("%B %Y")
            if month_year not in date_suggestions:
                date_suggestions.append(month_year)

    return {
        "locations": list(locations),
        "persons": list(persons),
        "albums": list(albums),
        "dates": date_suggestions[:12],
    }


@router.get("/storage-analysis")
async def get_storage_analysis(auth: AuthUser = Depends(require_user)):
    """Get detailed storage analysis"""
    images = await Image.filter(user_id=auth.user_id).order_by("created_at").all()

    monthly_storage = {}
    for img in images:
        if img.created_at and img.size_bytes:
            month_key = img.created_at.strftime("%Y-%m")
            monthly_storage.setdefault(month_key, {"size_bytes": 0, "count": 0})
            monthly_storage[month_key]["size_bytes"] += img.size_bytes
            monthly_storage[month_key]["count"] += 1

    monthly_data = [
        {
            "month": month,
            "size_mb": round(data["size_bytes"] / (1024 * 1024), 2),
            "count": data["count"],
        }
        for month, data in monthly_storage.items()
    ]

    location_storage = {}
    for img in images:
        if img.size_bytes:
            location = img.location_text or "Unknown"
            location_storage.setdefault(location, {"size_bytes": 0, "count": 0})
            location_storage[location]["size_bytes"] += img.size_bytes
            location_storage[location]["count"] += 1

    location_data = [
        {
            "location": location,
            "size_mb": round(data["size_bytes"] / (1024 * 1024), 2),
            "count": data["count"],
        }
        for location, data in location_storage.items()
    ]
    location_data.sort(key=lambda x: x["size_mb"], reverse=True)

    return {
        "monthly_storage": monthly_data,
        "location_storage": location_data[:10],
        "total_storage_mb": round(
            sum(d["size_bytes"] for d in monthly_storage.values()) / (1024 * 1024), 2
        ),
    }


@router.get("/person-analysis")
async def get_person_analysis(auth: AuthUser = Depends(require_user)):
    """Get analysis of people in photos"""
    clusters = await PersonCluster.filter(user_id=auth.user_id).prefetch_related("faces__image").all()

    person_data = []
    for cluster in clusters:
        images = list({face.image for face in cluster.faces})
        total_size = sum(img.size_bytes or 0 for img in images)
        locations = list({img.location_text for img in images if img.location_text})

        person_data.append({
            "cluster_id": str(cluster.id),
            "label": cluster.label,
            "face_count": len(cluster.faces),
            "image_count": len(images),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "locations": locations,
            "first_seen": min([img.created_at for img in images]) if images else None,
            "last_seen": max([img.created_at for img in images]) if images else None,
        })

    person_data.sort(key=lambda x: x["face_count"], reverse=True)
    return {
        "persons": person_data,
        "total_persons": len(person_data),
        "total_faces": sum(p["face_count"] for p in person_data),
    }


@router.get("/location-analysis")
async def get_location_analysis(auth: AuthUser = Depends(require_user)):
    """Get analysis of photo locations"""
    images = await Image.filter(user_id=auth.user_id, location_text__not_isnull=True).all()

    location_data = {}
    for img in images:
        location_data.setdefault(img.location_text, {
            "count": 0,
            "size_bytes": 0,
            "first_visit": img.created_at,
            "last_visit": img.created_at,
            "gps_coordinates": [],
        })
        data = location_data[img.location_text]
        data["count"] += 1
        data["size_bytes"] += img.size_bytes or 0
        if img.created_at < data["first_visit"]:
            data["first_visit"] = img.created_at
        if img.created_at > data["last_visit"]:
            data["last_visit"] = img.created_at
        if img.gps_lat and img.gps_lng:
            data["gps_coordinates"].append({"lat": img.gps_lat, "lng": img.gps_lng})

    locations = [
        {
            "location": loc,
            "count": d["count"],
            "size_mb": round(d["size_bytes"] / (1024 * 1024), 2),
            "first_visit": d["first_visit"],
            "last_visit": d["last_visit"],
            "visit_span_days": (d["last_visit"] - d["first_visit"]).days
                if d["last_visit"] != d["first_visit"] else 0,
            "gps_coordinates": d["gps_coordinates"],
        }
        for loc, d in location_data.items()
    ]
    locations.sort(key=lambda x: x["count"], reverse=True)

    return {
        "locations": locations,
        "total_locations": len(locations),
        "total_photos_with_location": len(images),
    }
