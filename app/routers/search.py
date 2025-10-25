from fastapi import APIRouter, Depends, HTTPException, Query
from app.consolidated_services import require_user, AuthUser, text_embedding, search_vectors
from app.models.image import Image
from app.schemas.image import ImageOut
from app.utils.math import safe_cosine


router = APIRouter(prefix="/search", tags=["search"])


def _image_to_out(img):
    """Convert Image model to ImageOut schema"""
    return ImageOut.model_validate(img.__dict__)


@router.get("")
async def search_images(
    q: str = Query(..., min_length=1),
    top_k: int = Query(20, le=100),
    auth: AuthUser = Depends(require_user),
    tags: List[str] | None = Query(None),
    category: str | None = Query(None),
    faces_only: bool = Query(False),
):
    """
    Search images using semantic similarity.
    Uses pgvector when available, falls back to Python cosine similarity.
    Supports optional filtering by faces/tags/categories when available.
    """
    query_vec = text_embedding(q)
    
    # Try pgvector first (fast and scalable)
    rows = await search_vectors(query_vec, top_k=top_k)
    if rows:
        ids = [r["image_id"] for r in rows]
        imgs = {str(m.id): m for m in await Image.filter(user_id=auth.user_id, id__in=ids).all()}
        results = []
        for r in rows:
            m = imgs.get(str(r["image_id"]))
            if not m:
                continue
            # faces-only filter (derived)
            if faces_only:
                if not await Face.filter(image_id=m.id).exists():
                    continue
            results.append({"image": _image_to_out(m), "score": float(r["score"])})
        return {"query": q, "results": results}

    # Fallback to in-Python cosine similarity
    imgs = await Image.filter(user_id=auth.user_id).all()
    scored = []
    
    for m in imgs:
        if m.embedding_json:
            score = safe_cosine(query_vec, list(map(float, m.embedding_json)))
            scored.append((score, m))
    
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:top_k]
    
    # faces-only filter (derived)
    out = []
    for s, m in top:
        if faces_only and not await Face.filter(image_id=m.id).exists():
            continue
        out.append({"image": _image_to_out(m), "score": float(s)})
    
    return {"query": q, "results": out}


@router.get("/similar/{image_id}")
async def similar_images(
    image_id: str,
    top_k: int = Query(20, le=100),
    auth: AuthUser = Depends(require_user),
):
    """
    Find images similar to the given image_id for the authenticated user.
    """
    base = await Image.filter(id=image_id, user_id=auth.user_id).first()
    if not base or not base.embedding_json:
        raise HTTPException(status_code=404, detail="Image or embedding not found")

    query_vec = list(map(float, base.embedding_json))
    rows = await search_vectors(query_vec, top_k=top_k)
    if rows:
        ids = [r["image_id"] for r in rows]
        imgs = {str(m.id): m for m in await Image.filter(user_id=auth.user_id, id__in=ids).all()}
        results = []
        for r in rows:
            m = imgs.get(str(r["image_id"]))
            if m:
                results.append({"image": _image_to_out(m), "score": float(r["score"])})
        return {"query_image_id": image_id, "results": results}

    # Fallback (Python cosine)
    imgs = await Image.filter(user_id=auth.user_id).exclude(id=image_id).all()
    scored = []
    for m in imgs:
        if m.embedding_json:
            score = safe_cosine(query_vec, list(map(float, m.embedding_json)))
            scored.append((score, m))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:top_k]
    return {"query_image_id": image_id, "results": [{"image": _image_to_out(m), "score": float(s)} for s, m in top]}