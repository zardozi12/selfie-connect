from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import datetime
import math
from tortoise.expressions import Q

from app.consolidated_services import require_user, AuthUser
from app.models.image import Image

# Change prefix to avoid conflict with search.py
router = APIRouter(prefix="/search/advanced", tags=["search"])

@router.get("/")
async def advanced_search(
    auth: AuthUser = Depends(require_user),
    q: Optional[str] = Query(None, description="Search query"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    has_faces: Optional[bool] = Query(None, description="Filter by presence of faces"),
    location: Optional[str] = Query(None, description="Location filter"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Advanced search with multiple filters"""
    try:
        query = Image.filter(user_id=auth.user_id)
        
        # Apply filters
        if start_date:
            query = query.filter(created_at__gte=start_date)
        if end_date:
            query = query.filter(created_at__lte=end_date)
        if has_faces is not None:
            if has_faces:
                query = query.filter(faces__isnull=False)
            else:
                query = query.filter(faces__isnull=True)
        if location:
            query = query.filter(
                Q(location_text__icontains=location) |
                Q(city__icontains=location) |
                Q(country__icontains=location)
            )
        if q:
            # Simple text search in filename and location
            query = query.filter(
                Q(filename__icontains=q) |
                Q(location_text__icontains=q)
            )
        
        # Get total count
        total = await query.count()
        
        # Get paginated results
        images = await query.order_by("-created_at").offset(offset).limit(limit).all()
        
        return {
            "images": [
                {
                    "id": str(img.id),
                    "filename": img.filename,
                    "created_at": img.created_at,
                    "location_text": img.location_text,
                    "city": img.city,
                    "country": img.country,
                    "has_faces": bool(await img.faces.all())
                }
                for img in images
            ],
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/suggestions")
async def search_suggestions(
    auth: AuthUser = Depends(require_user),
    q: str = Query(..., min_length=1, description="Partial search query")
):
    """Get search suggestions based on existing data"""
    try:
        # Get location suggestions
        locations = await Image.filter(
            user_id=auth.user_id,
            location_text__icontains=q
        ).values_list("location_text", flat=True).distinct().limit(5)
        
        # Get filename suggestions
        filenames = await Image.filter(
            user_id=auth.user_id,
            filename__icontains=q
        ).values_list("filename", flat=True).distinct().limit(5)
        
        return {
            "locations": [loc for loc in locations if loc],
            "filenames": [name for name in filenames if name]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


