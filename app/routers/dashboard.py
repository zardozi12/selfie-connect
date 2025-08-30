from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.models.image import Image
from app.models.album import Album, AlbumImage
from app.models.face import Face
from app.models.user import PersonCluster
from app.services.security import require_user, AuthUser
from app.schemas.image import ImageOut, AlbumOut, PersonClusterOut
from tortoise.expressions import Q
from datetime import datetime, timedelta


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(auth: AuthUser = Depends(require_user)):
    """Get comprehensive dashboard statistics"""
    
    # Basic counts
    total_images = await Image.filter(user_id=auth.user_id).count()
    total_albums = await Album.filter(user_id=auth.user_id).count()
    total_faces = await Face.filter(image__user_id=auth.user_id).count()
    total_persons = await PersonCluster.filter(user_id=auth.user_id).count()
    
    # Storage usage (approximate)
    total_size = await Image.filter(user_id=auth.user_id).aggregate(
        total_size=Q.sum("size_bytes")
    )
    total_size_mb = (total_size["total_size"] or 0) / (1024 * 1024)
    
    # Recent activity
    last_week = datetime.now() - timedelta(days=7)
    recent_uploads = await Image.filter(
        user_id=auth.user_id,
        created_at__gte=last_week
    ).count()
    
    # Albums by type
    album_types = await Album.filter(user_id=auth.user_id).group_by("album_type").annotate(
        count=Q.count("id")
    ).values("album_type", "count")
    
    # Location stats
    locations_with_images = await Image.filter(
        user_id=auth.user_id,
        location_text__not_isnull=True
    ).distinct().values_list("location_text", flat=True)
    
    # Recent images
    recent_images = await Image.filter(
        user_id=auth.user_id
    ).order_by("-created_at").limit(10).all()
    
    recent_image_data = []
    for img in recent_images:
        recent_image_data.append(ImageOut(
            id=img.id,
            original_filename=img.original_filename,
            width=img.width,
            height=img.height,
            gps_lat=img.gps_lat,
            gps_lng=img.gps_lng,
            location_text=img.location_text,
            created_at=img.created_at
        ))
    
    return {
        "total_images": total_images,
        "total_albums": total_albums,
        "total_faces": total_faces,
        "total_persons": total_persons,
        "total_storage_mb": round(total_size_mb, 2),
        "recent_uploads": recent_uploads,
        "album_types": album_types,
        "unique_locations": len(locations_with_images),
        "recent_images": recent_image_data
    }


@router.get("/recent-activity")
async def get_recent_activity(auth: AuthUser = Depends(require_user)):
    """Get recent activity including uploads and album changes"""
    
    # Recent image uploads
    recent_images = await Image.filter(
        user_id=auth.user_id
    ).order_by("-created_at").limit(20).all()
    
    # Recent album changes
    recent_albums = await Album.filter(
        user_id=auth.user_id
    ).order_by("-created_at").limit(10).all()
    
    # Recent person clusters
    recent_clusters = await PersonCluster.filter(
        user_id=auth.user_id
    ).order_by("-created_at").limit(5).all()
    
    activity = []
    
    # Add image uploads
    for img in recent_images:
        activity.append({
            "type": "image_upload",
            "timestamp": img.created_at,
            "title": f"Uploaded {img.original_filename or 'image'}",
            "details": {
                "image_id": str(img.id),
                "location": img.location_text,
                "size_mb": round((img.size_bytes or 0) / (1024 * 1024), 2)
            }
        })
    
    # Add album creations
    for album in recent_albums:
        activity.append({
            "type": "album_created",
            "timestamp": album.created_at,
            "title": f"Created album '{album.name}'",
            "details": {
                "album_id": str(album.id),
                "album_type": album.album_type,
                "is_auto_generated": album.is_auto_generated
            }
        })
    
    # Add person clusters
    for cluster in recent_clusters:
        activity.append({
            "type": "person_clustered",
            "timestamp": cluster.created_at,
            "title": f"Identified person '{cluster.label}'",
            "details": {
                "cluster_id": str(cluster.id),
                "face_count": await Face.filter(cluster=cluster).count()
            }
        })
    
    # Sort by timestamp
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "activity": activity[:30]  # Return top 30 activities
    }


@router.get("/search-suggestions")
async def get_search_suggestions(auth: AuthUser = Depends(require_user)):
    """Get search suggestions based on user's data"""
    
    # Location suggestions
    locations = await Image.filter(
        user_id=auth.user_id,
        location_text__not_isnull=True
    ).distinct().values_list("location_text", flat=True)
    
    # Person suggestions
    persons = await PersonCluster.filter(user_id=auth.user_id).values_list("label", flat=True)
    
    # Album suggestions
    albums = await Album.filter(user_id=auth.user_id).values_list("name", flat=True)
    
    # Date suggestions (months/years)
    images_with_dates = await Image.filter(
        user_id=auth.user_id,
        created_at__not_isnull=True
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
        "dates": date_suggestions[:12]  # Last 12 months
    }


@router.get("/storage-analysis")
async def get_storage_analysis(auth: AuthUser = Depends(require_user)):
    """Get detailed storage analysis"""
    
    # Storage by month
    images = await Image.filter(user_id=auth.user_id).order_by("created_at").all()
    
    monthly_storage = {}
    for img in images:
        if img.created_at and img.size_bytes:
            month_key = img.created_at.strftime("%Y-%m")
            if month_key not in monthly_storage:
                monthly_storage[month_key] = {
                    "size_bytes": 0,
                    "count": 0
                }
            monthly_storage[month_key]["size_bytes"] += img.size_bytes
            monthly_storage[month_key]["count"] += 1
    
    # Convert to MB and format
    monthly_data = []
    for month, data in monthly_storage.items():
        monthly_data.append({
            "month": month,
            "size_mb": round(data["size_bytes"] / (1024 * 1024), 2),
            "count": data["count"]
        })
    
    # Storage by location
    location_storage = {}
    for img in images:
        if img.size_bytes:
            location = img.location_text or "Unknown"
            if location not in location_storage:
                location_storage[location] = {
                    "size_bytes": 0,
                    "count": 0
                }
            location_storage[location]["size_bytes"] += img.size_bytes
            location_storage[location]["count"] += 1
    
    location_data = []
    for location, data in location_storage.items():
        location_data.append({
            "location": location,
            "size_mb": round(data["size_bytes"] / (1024 * 1024), 2),
            "count": data["count"]
        })
    
    # Sort by size
    location_data.sort(key=lambda x: x["size_mb"], reverse=True)
    
    return {
        "monthly_storage": monthly_data,
        "location_storage": location_data[:10],  # Top 10 locations
        "total_storage_mb": round(sum(data["size_bytes"] for data in monthly_storage.values()) / (1024 * 1024), 2)
    }


@router.get("/person-analysis")
async def get_person_analysis(auth: AuthUser = Depends(require_user)):
    """Get analysis of people in photos"""
    
    # Get all person clusters with their faces
    clusters = await PersonCluster.filter(user_id=auth.user_id).prefetch_related("faces__image").all()
    
    person_data = []
    for cluster in clusters:
        # Get unique images for this person
        images = list(set([face.image for face in cluster.faces]))
        
        # Calculate total size
        total_size = sum(img.size_bytes or 0 for img in images)
        
        # Get locations where this person appears
        locations = list(set([img.location_text for img in images if img.location_text]))
        
        person_data.append({
            "cluster_id": str(cluster.id),
            "label": cluster.label,
            "face_count": len(cluster.faces),
            "image_count": len(images),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "locations": locations,
            "first_seen": min([img.created_at for img in images]) if images else None,
            "last_seen": max([img.created_at for img in images]) if images else None
        })
    
    # Sort by face count
    person_data.sort(key=lambda x: x["face_count"], reverse=True)
    
    return {
        "persons": person_data,
        "total_persons": len(person_data),
        "total_faces": sum(p["face_count"] for p in person_data)
    }


@router.get("/location-analysis")
async def get_location_analysis(auth: AuthUser = Depends(require_user)):
    """Get analysis of photo locations"""
    
    # Get all images with location data
    images = await Image.filter(
        user_id=auth.user_id,
        location_text__not_isnull=True
    ).all()
    
    location_data = {}
    for img in images:
        location = img.location_text
        if location not in location_data:
            location_data[location] = {
                "count": 0,
                "size_bytes": 0,
                "first_visit": img.created_at,
                "last_visit": img.created_at,
                "gps_coordinates": []
            }
        
        location_data[location]["count"] += 1
        location_data[location]["size_bytes"] += img.size_bytes or 0
        
        if img.created_at < location_data[location]["first_visit"]:
            location_data[location]["first_visit"] = img.created_at
        
        if img.created_at > location_data[location]["last_visit"]:
            location_data[location]["last_visit"] = img.created_at
        
        if img.gps_lat and img.gps_lng:
            location_data[location]["gps_coordinates"].append({
                "lat": img.gps_lat,
                "lng": img.gps_lng
            })
    
    # Convert to list and format
    locations = []
    for location, data in location_data.items():
        locations.append({
            "location": location,
            "count": data["count"],
            "size_mb": round(data["size_bytes"] / (1024 * 1024), 2),
            "first_visit": data["first_visit"],
            "last_visit": data["last_visit"],
            "visit_span_days": (data["last_visit"] - data["first_visit"]).days if data["last_visit"] != data["first_visit"] else 0,
            "gps_coordinates": data["gps_coordinates"]
        })
    
    # Sort by count
    locations.sort(key=lambda x: x["count"], reverse=True)
    
    return {
        "locations": locations,
        "total_locations": len(locations),
        "total_photos_with_location": len(images)
    }
