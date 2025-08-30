from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.models.face import Face
from app.models.user import PersonCluster
from app.services.security import require_user, AuthUser
from app.schemas.image import PersonClusterOut


router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("/clusters", response_model=list[PersonClusterOut])
async def list_clusters(auth: AuthUser = Depends(require_user)):
    clusters = await PersonCluster.filter(user_id=auth.user_id).all()
    out: list[PersonClusterOut] = []
    for c in clusters:
        faces = await Face.filter(cluster_id=c.id).count()
        out.append(PersonClusterOut(id=c.id, label=c.label, faces=faces))
    return out


@router.post("/clusters/{cluster_id}/rename")
async def rename_cluster(cluster_id: UUID, label: str, auth: AuthUser = Depends(require_user)):
    c = await PersonCluster.filter(id=cluster_id, user_id=auth.user_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    
    c.label = label
    await c.save()
    return {"ok": True}