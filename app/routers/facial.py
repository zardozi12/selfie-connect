from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.consolidated_services import require_user, AuthUser
from app.models.user import User
from app.services.faceapi import register_face, verify_face

router = APIRouter(prefix="/api/facial", tags=["facial"])

@router.post("/register")
async def facial_register(image: UploadFile = File(...), user: AuthUser = Depends(require_user)):
    """
    Register user's face: store Azure face_id (if available) and local face vector.
    Saved into User.face_embedding_json as: {"face_api_id": str|None, "vector": list|None}
    """
    content = await image.read()
    face_id, vec = await register_face(content)
    db_user = await User.filter(id=user.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.face_embedding_json = {
        "face_api_id": face_id,
        "vector": (vec.tolist() if vec is not None else None),
    }
    await db_user.save()
    return {"registered": bool(face_id or vec is not None), "face_api_id": face_id, "has_vector": vec is not None}

@router.post("/verify")
async def facial_verify(image: UploadFile = File(...), user: AuthUser = Depends(require_user)):
    """
    Verify logged-in user's face using Azure Face API or local vector fallback.
    """
    content = await image.read()
    db_user = await User.filter(id=user.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    meta = db_user.face_embedding_json or {}
    ok, conf = await verify_face(meta.get("face_api_id"), meta.get("vector"), content)
    if not ok:
        raise HTTPException(status_code=403, detail=f"Face verification failed (confidence={conf:.4f})")
    return {"access_granted": True, "confidence": conf}