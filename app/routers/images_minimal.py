# Minimal images router for testing
from fastapi import APIRouter, Depends, HTTPException
from app.services.security import require_user, AuthUser
from app.models.image import Image
from app.schemas.image import ImageOut
from typing import List

router = APIRouter(prefix="/images", tags=["images"])

@router.get("/list", response_model=List[ImageOut])
async def list_images(auth: AuthUser = Depends(require_user)):
    """Simple list images endpoint"""
    try:
        images = await Image.filter(user_id=auth.user_id).order_by("-created_at").all()
        return [ImageOut.model_validate(i.__dict__) for i in images]
    except Exception as e:
        print(f"Error in list_images: {e}")
        raise HTTPException(status_code=500, detail=str(e))
