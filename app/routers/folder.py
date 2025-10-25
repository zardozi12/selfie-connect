from fastapi import APIRouter, Depends, HTTPException
router = APIRouter(prefix="/folders", tags=["folders"])

@router.post("/", response_model=FolderOut)
async def create_folder(payload: FolderCreate, user=Depends(get_current_user)):
    # Create folder logic
    pass

@router.get("/tree", response_model=FolderTreeOut)
async def get_folder_tree(user=Depends(get_current_user)):
    # Return user's folder tree
    pass

@router.post("/{id}/upload")
async def upload_to_folder(id: str, file: UploadFile, user=Depends(get_current_user)):
    # Upload and encrypt file, bind to FEK
    pass

@router.get("/{id}/photos", response_model=PhotoListOut)
async def get_folder_photos(id: str, user=Depends(get_current_user)):
    # Paginated list of photos in folder
    pass

from datetime import datetime, timedelta
import secrets
import hashlib
from fastapi import Query

@router.post("/{id}/share", response_model=QRShareOut)
async def share_folder(
    id: str, 
    payload: QRShareCreate, 
    user=Depends(get_current_user)
):
    folder = await Folder.get_or_none(id=id, user=user)
    if not folder:
        raise HTTPException(404, "Folder not found")

    # Generate secure random token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(seconds=payload.expires_in)

    share = await QRShare.create(
        folder=folder,
        token_hash=token_hash,
        expires_at=expires_at,
        permissions_json=payload.permissions.dict(),
        created_by=user
    )

    return {
        "share_id": str(share.id),
        "token": token,
        "expires_at": expires_at,
        "qr_url": f"/qr/{token}"
    }

@router.get("/qr/{token}")
async def access_shared_folder(token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    share = await QRShare.get_or_none(
        token_hash=token_hash,
        expires_at__gt=datetime.utcnow(),
        revoked_at=None
    )
    
    if not share:
        raise HTTPException(404, "Invalid or expired share link")

    # Get folder and decrypt FEK using master key
    folder = await share.folder
    fek = unwrap_key(folder.encrypted_fek, settings.MASTER_KEY)
    
    # Return decrypted photos or generate temporary access
    return {
        "folder_id": str(folder.id),
        "photos": [] # Implement actual photo retrieval
    }

@router.post("/shares/{share_id}/revoke")
async def revoke_share(share_id: str, user=Depends(get_current_user)):
    share = await QRShare.get_or_none(id=share_id, created_by=user)
    if not share:
        raise HTTPException(404, "Share not found")
    
    share.revoked_at = datetime.utcnow()
    await share.save()
    
    return {"status": "revoked"}

@router.get("/qr/{token}")
async def access_shared_folder(token: str):
    # Validate token, expiry, permissions, stream media
    pass


### **API Endpoint Stubs (OpenAPI style)**
```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from app.services.encryption import generate_fek, wrap_key
from app.models.folder import Folder
from app.schemas.folders import FolderCreate, FolderOut

@router.post("/", response_model=FolderOut)
async def create_folder(payload: FolderCreate, user=Depends(get_current_user)):
    # Generate FEK for the folder
    fek = generate_fek()
    encrypted_fek = wrap_key(fek, user.master_key)
    
    folder = await Folder.create(
        user=user,
        parent_id=payload.parent_id,
        name=payload.name,
        encrypted_fek=encrypted_fek
    )
    return folder

@router.get("/tree", response_model=FolderTreeOut)
async def get_folder_tree(user=Depends(get_current_user)):
    def build_tree(parent=None):
        return [
            {
                "id": str(folder.id),
                "name": folder.name,
                "children": build_tree(folder.id)
            }
            for folder in await Folder.filter(user=user, parent=parent)
        ]
    
    return {"tree": build_tree()}

@router.post("/{id}/upload")
async def upload_to_folder(id: str, file: UploadFile, user=Depends(get_current_user)):
    folder = await Folder.get_or_none(id=id, user=user)
    if not folder:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found")
    
    # Get FEK for encryption
    fek = unwrap_key(folder.encrypted_fek, user.master_key)
    
    # Process file upload with FEK
    pass

@router.get("/{id}/photos", response_model=PhotoListOut)
async def get_folder_photos(id: str, user=Depends(get_current_user)):
    # Paginated list of photos in folder
    pass

@router.post("/{id}/share", response_model=QRShareOut)
async def share_folder(id: str, payload: QRShareCreate, user=Depends(get_current_user)):
    # Create QR share token, store hash, set expiry/permissions
    pass

@router.post("/shares/{share_id}/revoke")
async def revoke_share(share_id: str, user=Depends(get_current_user)):
    # Revoke QR share, update revoked_at
    pass

@router.get("/qr/{token}")
async def access_shared_folder(token: str):
    # Validate token, expiry, permissions, stream media
    pass
```