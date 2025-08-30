from fastapi import APIRouter, Depends, HTTPException
from app.services.security import require_user, AuthUser
from app.models.image import Image
from app.services.embeddings import text_embedding
from tortoise.transactions import in_transaction


router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(q: str, auth: AuthUser = Depends(require_user)):
    # Try pgvector similarity first; fallback to simple filename search
    emb = text_embedding(q)
    try:
        async with in_transaction() as conn:
            rows = await conn.execute_query_dict(
                """
                SELECT i.id, i.original_filename, i.location_text
                FROM image_embeddings e
                JOIN image i ON i.id = e.image_id
                WHERE i.user_id = $1
                ORDER BY e.embedding <-> $2::vector
                LIMIT 25
                """,
                [str(auth.user_id), emb]
            )
            return {"results": rows}
    except Exception:
        imgs = await Image.filter(user_id=auth.user_id, original_filename__icontains=q).values("id", "original_filename", "location_text").limit(25)
        return {"results": imgs}