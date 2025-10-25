from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.consolidated_services import require_user, AuthUser, storage
from app.models.image import Image
from app.services.encryption import fernet_from_dek
from app.models.user import User
from app.routers.api import _ensure_user_dek, _hash_sha256, _image_to_out
from app.services.queue import enqueue_thumbnail, enqueue_embeddings  # optional
from app.services.cache import cache_invalidate_prefix

# Change prefix to avoid conflict with images.py
router = APIRouter(prefix="/images/bulk", tags=["images"])

@router.post("/upload")
async def bulk_upload_images(
    auth: AuthUser = Depends(require_user),
    files: List[UploadFile] = File(...)
):
    """Upload multiple images at once"""
    if len(files) > 50:  # Limit bulk uploads
        raise HTTPException(status_code=400, detail="Maximum 50 files per bulk upload")
    
    try:
        user = await User.filter(id=auth.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Ensure user has DEK
        dek_b64 = await _ensure_user_dek(user)
        fernet = fernet_from_dek(dek_b64)
        
        results = []
        
        for file in files:
            try:
                # Validate file
                if not file.content_type or not file.content_type.startswith('image/'):
                    results.append({
                        "filename": file.filename,
                        "status": "error",
                        "error": "Invalid file type"
                    })
                    continue
                
                # Read and process file
                content = await file.read()
                if len(content) > 10 * 1024 * 1024:  # 10MB limit
                    results.append({
                        "filename": file.filename,
                        "status": "error", 
                        "error": "File too large (max 10MB)"
                    })
                    continue
                
                # Create image record
                sha256 = _hash_sha256(content)
                encrypted = fernet.encrypt(content)
                storage_key = storage.save(auth.user_id, f"{sha256}.enc", encrypted)
                
                image = await Image.create(
                    user_id=auth.user_id,
                    filename=file.filename or f"upload_{sha256[:8]}.jpg",
                    storage_key=storage_key,
                    file_size=len(content),
                    sha256=sha256,
                    content_type=file.content_type
                )
                
                # Enqueue background tasks
                enqueue_thumbnail(str(image.id), auth.user_id)
                enqueue_embeddings(str(image.id), auth.user_id)
                
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "image_id": str(image.id)
                })
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })
        
        # Invalidate cache
        cache_invalidate_prefix(f"user:{auth.user_id}")
        
        return {
            "results": results,
            "total_files": len(files),
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")

@router.get("/status/{batch_id}")
async def get_bulk_upload_status(
    batch_id: str,
    auth: AuthUser = Depends(require_user)
):
    """Get status of a bulk upload batch"""
    # This would require implementing batch tracking
    # For now, return a simple response
    return {
        "batch_id": batch_id,
        "status": "completed",
        "message": "Bulk upload status tracking not implemented yet"
    }


