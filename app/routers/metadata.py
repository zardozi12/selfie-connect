from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
from pathlib import Path
from typing import Optional
from app.consolidated_services import require_user, AuthUser
from app.services.ai_metadata_store import load_metadata
from app.config import settings

router = APIRouter(prefix="/metadata", tags=["metadata"])

@router.get("/images/{image_id}")
async def get_image_metadata(image_id: str, auth: AuthUser = Depends(require_user)):
    meta = load_metadata(str(auth.user_id), image_id)
    if not meta:
        raise HTTPException(status_code=404, detail="No metadata")
    return meta

# Method: metadata_events()
@router.get("/events")
async def metadata_events(auth: AuthUser = Depends(require_user)):
    """SSE-like stream of metadata updates for the authenticated user."""
    updates = Path(settings.STORAGE_DIR).resolve() / "metadata" / "updates.jsonl"
    async def event_stream():
        pos = 0
        while True:
            try:
                if updates.exists():
                    with updates.open("r", encoding="utf-8") as f:
                        f.seek(pos)
                        lines = f.readlines()
                        pos = f.tell()
                        for line in lines:
                            try:
                                obj = json.loads(line)
                                if obj.get("user_id") == str(auth.user_id):
                                    yield f"data: {json.dumps(obj)}\n\n"
                            except Exception:
                                continue
                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )