# app/routers/api.py
from __future__ import annotations

import hashlib
import io
import asyncio
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
    Query,
    Body,
)
from fastapi.responses import StreamingResponse, HTMLResponse

# Tortoise ORM
from tortoise.functions import Count

# Schemas
from app.schemas.auth import SignupPayload, LoginPayload, TokenOut
from app.schemas.image import (
    ImageOut,
    FaceOut,
    AlbumOut,
    AlbumImageOut,
    PersonClusterOut,
)
# Models
from app.models.user import User, PersonCluster
from app.models.image import Image
from app.models.face import Face
from app.models.album import Album, AlbumImage

# Services / utils
from app.services.security import (
    create_token,
    hash_password,
    verify_password,
)
from app.consolidated_services import (
    require_user,
    AuthUser,
    new_data_key,
    wrap_dek,
    unwrap_dek,
    fernet_from_dek,
    analyze,
    to_rgb_np,
    image_embedding,
    text_embedding,
    storage,
    AlbumService,
    reverse as geocode_reverse,
    cdn_url,
    make_thumbnail,
)
from app.config import settings
from app.services.queue import enqueue_embeddings, enqueue_ai_tagging

api = APIRouter(tags=["api"])


# ------------------------------
# Helpers
# ------------------------------
async def _ensure_user_dek(user: User) -> bytes:
    if not user.dek_encrypted_b64:
        dek_b64 = new_data_key()
        user.dek_encrypted_b64 = wrap_dek(dek_b64)
        await user.save()
    return unwrap_dek(user.dek_encrypted_b64)

def _hash_sha256(data: bytes) -> str:
    h = hashlib.sha256(); h.update(data); return h.hexdigest()

def _image_to_out(m: Image) -> ImageOut:
    return ImageOut(
        id=m.id,
        original_filename=m.original_filename,
        width=m.width,
        height=m.height,
        gps_lat=m.gps_lat,
        gps_lng=m.gps_lng,
        location_text=m.location_text,
        created_at=m.created_at,
    )

def _album_to_out(m: Album, image_count: int = 0) -> AlbumOut:
    return AlbumOut(
        id=m.id,
        name=m.name,
        description=m.description,
        album_type=m.album_type,
        location_text=m.location_text,
        gps_lat=m.gps_lat,
        gps_lng=m.gps_lng,
        start_date=m.start_date,
        end_date=m.end_date,
        is_auto_generated=m.is_auto_generated,
        cover_image_id=m.cover_image_id,
        image_count=image_count,
        created_at=m.created_at,
    )

def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b): return 0.0
    dot=n1=n2=0.0
    for x,y in zip(a,b):
        dot+=x*y; n1+=x*x; n2+=y*y
    if n1==0 or n2==0: return 0.0
    return dot/((n1**0.5)*(n2**0.5))

def _short_id(uuid_val: UUID) -> str:
    # short human-friendly ID (8 hex)
    return str(uuid_val).split("-")[0].upper()


# Auth endpoints moved to auth.py router


# ------------------------------
# Camera page (webcam capture → upload)
# ------------------------------
@api.get("/camera", response_class=HTMLResponse)
async def camera_page():
    # Minimal HTML+JS page: login, open camera, capture, upload, choose manual/auto
    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>PhotoVault Camera</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto;max-width:720px;margin:20px auto;padding:0 12px}
    .card{border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:12px 0}
    button{padding:10px 14px;border-radius:10px;border:1px solid #e5e7eb;background:#111;color:#fff;cursor:pointer}
    button.secondary{background:#fff;color:#111}
    input,select{padding:10px;border-radius:10px;border:1px solid #e5e7eb;width:100%}
    .row{display:flex;gap:8px;flex-wrap:wrap}
    .row>*{flex:1}
    #status{font-size:14px;color:#374151}
    video,canvas{width:100%;border-radius:12px;background:#000}
    small{color:#6b7280}
  </style>
</head>
<body>
  <h1>PhotoVault Camera</h1>

  <div class="card">
    <h3>Login</h3>
    <div class="row">
      <input id="email" placeholder="email@example.com" />
      <input id="password" type="password" placeholder="password" />
    </div>
    <div style="margin-top:8px">
      <button id="btnLogin">Login</button>
      <small id="who"></small>
    </div>
  </div>

  <div class="card">
    <h3>Camera</h3>
    <video id="video" autoplay playsinline></video>
    <canvas id="canvas" style="display:none"></canvas>
    <div class="row" style="margin-top:8px">
      <button id="btnStart">Start Camera</button>
      <button id="btnSnap" class="secondary">Capture</button>
    </div>
  </div>

  <div class="card">
    <h3>Upload</h3>
    <div class="row">
      <select id="mode">
        <option value="manual">Manual</option>
        <option value="auto">Auto (up to 10 person folders)</option>
      </select>
      <input id="albumName" placeholder="Album name (manual mode)" />
    </div>
    <div style="margin-top:8px">
      <button id="btnUpload">Upload Photo</button>
      <div id="status"></div>
    </div>
  </div>

<script>
let token = null, stream = null, lastBlob = null;
const $ = (id)=>document.getElementById(id);

async function login(){
  const email=$('email').value.trim(), password=$('password').value;
  const res=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({email,password})});
  if(!res.ok){$('status').innerText='Login failed'; return;}
  const data=await res.json(); token=data.access_token; $('who').innerText='Logged in'; $('status').innerText='';
}

async function startCam(){
  stream = await navigator.mediaDevices.getUserMedia({video:true,audio:false});
  $('video').srcObject = stream;
}

function capture(){
  const v=$('video'), c=$('canvas');
  c.width=v.videoWidth; c.height=v.videoHeight;
  const ctx=c.getContext('2d'); ctx.drawImage(v,0,0);
  c.toBlob(b=>{ lastBlob=b; $('status').innerText='Captured. Ready to upload.'; }, 'image/jpeg', 0.92);
}

async function upload(){
  if(!token){$('status').innerText='Please login first.'; return;}
  if(!lastBlob){$('status').innerText='Capture a photo first.'; return;}

  const fd=new FormData(); fd.append('file', lastBlob, 'webcam.jpg');
  $('status').innerText='Uploading...';
  const up=await fetch('/images/upload',{method:'POST',headers:{'Authorization':'Bearer '+token}, body:fd});
  if(!up.ok){$('status').innerText='Upload failed'; return;}
  const img=await up.json();

  const mode=$('mode').value;
  if(mode==='manual'){
    let name=$('albumName').value.trim(); if(!name) name='My Manual Album';
    const mk=await fetch('/albums/manual',{method:'POST',headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'},
      body:JSON.stringify({name, description:'Manual album from camera'})});
    const alb=await mk.json();
    await fetch(`/albums/${alb.id}/add-image`,{method:'POST',headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'},
      body:JSON.stringify({image_id: img.id})});
    $('status').innerText='Uploaded to manual album: '+name;
  }else{
    // Auto: create up to 10 person folders
    const auto=await fetch('/albums/person-folders/init?limit=10',{method:'POST',headers:{'Authorization':'Bearer '+token}});
    const res=await auto.json();
    $('status').innerText='Uploaded. Auto folders created: '+res.created_albums.length;
  }
}

$('btnLogin').onclick=login;
$('btnStart').onclick=startCam;
$('btnSnap').onclick=capture;
$('btnUpload').onclick=upload;
</script>
</body>
</html>"""


# ------------------------------
# Images
# ------------------------------
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB

@api.post("/images/upload", response_model=ImageOut, status_code=201)
async def upload_image(file: UploadFile = File(...), user: AuthUser = Depends(require_user)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    db_user = await User.filter(id=user.user_id).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    dek_b64 = await _ensure_user_dek(db_user)
    fernet = fernet_from_dek(dek_b64)

    try:
        proc = await analyze(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to process image: {e}")

    location_text: Optional[str] = None
    if settings.ENABLE_GEOCODER and proc.lat is not None and proc.lng is not None:
        try:
            location_text = await geocode_reverse(proc.lat, proc.lng)
        except Exception:
            location_text = None

    try:
        np_rgb = await to_rgb_np(content)
        emb = image_embedding(np_rgb)
    except Exception:
        emb = None

    encrypted = fernet.encrypt(content)
    original_name = file.filename or "upload"
    if hasattr(storage, 'save') and callable(getattr(storage, 'save')):
        if asyncio.iscoroutinefunction(storage.save):
            storage_key = await storage.save(user_id=str(db_user.id), filename=original_name, data=encrypted)
        else:
            storage_key = storage.save(user_id=str(db_user.id), filename=original_name, data=encrypted)
    else:
        raise HTTPException(status_code=500, detail="Storage service unavailable")
    
    # Generate thumbnail
    thumb_storage_key = None
    try:
        thumb_bytes = make_thumbnail(content, max_side=512, quality=85)
        if thumb_bytes:
            thumb_encrypted = fernet.encrypt(thumb_bytes)
            thumb_filename = f"thumb_{original_name}"
            if asyncio.iscoroutinefunction(storage.save):
                thumb_storage_key = await storage.save(user_id=str(db_user.id), filename=thumb_filename, data=thumb_encrypted)
            else:
                thumb_storage_key = storage.save(user_id=str(db_user.id), filename=thumb_filename, data=thumb_encrypted)
    except Exception:
        pass  # Thumbnail generation failed, continue without

    img = await Image.create(
        user_id=db_user.id,
        original_filename=original_name,
        content_type=file.content_type or "image/jpeg",
        size_bytes=len(content),
        width=proc.width,
        height=proc.height,
        checksum_sha256=_hash_sha256(content),
        storage_key=storage_key,
        thumb_storage_key=thumb_storage_key,
        exif_json=proc.exif or None,
        gps_lat=proc.lat,
        gps_lng=proc.lng,
        location_text=location_text,
        embedding_json=emb,
    )
    # Background AI tasks: embeddings (pgvector) and tagging/categories
    try:
        enqueue_embeddings(str(img.id), str(db_user.id))
        enqueue_ai_tagging(str(img.id), str(db_user.id))
    except Exception:
        pass

    for (x,y,w,h) in proc.faces:
        await Face.create(image_id=img.id, x=x, y=y, w=w, h=h)

    return _image_to_out(img)

@api.get("/images/list", response_model=List[ImageOut])
async def list_images(skip: int = 0, limit: int = Query(50, le=200), user: AuthUser = Depends(require_user)):
    imgs = await Image.filter(user_id=user.user_id).offset(skip).limit(limit).order_by("-created_at")
    return [_image_to_out(m) for m in imgs]




@api.get("/images/{image_id}/url")
async def image_url(image_id: UUID, user: AuthUser = Depends(require_user)):
    img = await Image.filter(id=image_id, user_id=user.user_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"url": cdn_url(img.storage_key, expires_s=3600)}


@api.get("/images/{image_id}/thumb-url")
async def image_thumb_url(image_id: UUID, user: AuthUser = Depends(require_user)):
    img = await Image.filter(id=image_id, user_id=user.user_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    if not img.thumb_storage_key:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return {"url": cdn_url(img.thumb_storage_key, expires_s=3600)}

@api.get("/images/{image_id}/thumb")
async def view_thumbnail(image_id: UUID, user: AuthUser = Depends(require_user)):
    img = await Image.filter(id=image_id, user_id=user.user_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    
    db_user = await User.filter(id=user.user_id).first()
    dek_b64 = await _ensure_user_dek(db_user)
    fernet = fernet_from_dek(dek_b64)
    
    try:
        # Try thumbnail first, fallback to original
        storage_key = img.thumb_storage_key or img.storage_key
        
        if asyncio.iscoroutinefunction(storage.read):
            enc_bytes = await storage.read(storage_key)
        else:
            enc_bytes = storage.read(storage_key)
        
        image_bytes = fernet.decrypt(enc_bytes)
        media_type = "image/jpeg" if img.thumb_storage_key else (img.content_type or "image/jpeg")
        
        return StreamingResponse(
            io.BytesIO(image_bytes), 
            media_type=media_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load image: {str(e)}")

@api.get("/images/{image_id}/view")
async def view_image(image_id: UUID, user: AuthUser = Depends(require_user)):
    img = await Image.filter(id=image_id, user_id=user.user_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    
    db_user = await User.filter(id=user.user_id).first()
    dek_b64 = await _ensure_user_dek(db_user)
    fernet = fernet_from_dek(dek_b64)
    
    try:
        if asyncio.iscoroutinefunction(storage.read):
            enc_bytes = await storage.read(img.storage_key)
        else:
            enc_bytes = storage.read(img.storage_key)
        
        plain = fernet.decrypt(enc_bytes)
        return StreamingResponse(
            io.BytesIO(plain), 
            media_type=img.content_type or "image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load image: {str(e)}")


# ------------------------------
# Albums (manual + list + images)
# ------------------------------
@api.post("/albums/manual", response_model=AlbumOut, status_code=201)
async def create_manual_album(
    name: str = Body(..., embed=True),
    description: Optional[str] = Body(None, embed=True),
    user: AuthUser = Depends(require_user),
):
    # prevent duplicates per user
    existing = await Album.filter(user_id=user.user_id, name=name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Album name already exists")
    album = await Album.create(
        user_id=user.user_id,
        name=name,
        description=description,
        album_type="manual",
    )
    return _album_to_out(album, 0)

@api.post("/albums/{album_id}/add-image")
async def add_image_to_album(
    album_id: UUID,
    image_id: UUID = Body(..., embed=True),
    user: AuthUser = Depends(require_user),
):
    album = await Album.filter(id=album_id, user_id=user.user_id).first()
    if not album: raise HTTPException(status_code=404, detail="Album not found")
    img = await Image.filter(id=image_id, user_id=user.user_id).first()
    if not img: raise HTTPException(status_code=404, detail="Image not found")
    existing = await AlbumImage.filter(album_id=album.id, image_id=img.id).first()
    if existing: return {"ok": True, "added": False}
    await AlbumImage.create(album=album, image=img)
    return {"ok": True, "added": True}

@api.get("/albums/", response_model=List[AlbumOut])
async def list_albums(user: AuthUser = Depends(require_user)):
    albums = await Album.filter(user_id=user.user_id)
    out: List[AlbumOut] = []
    for a in albums:
        cnt = await AlbumImage.filter(album_id=a.id).count()
        out.append(_album_to_out(a, cnt))
    return out

@api.get("/albums/{album_id}/images", response_model=List[ImageOut])
async def album_images(album_id: UUID, user: AuthUser = Depends(require_user)):
    album = await Album.filter(id=album_id, user_id=user.user_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    joins = await AlbumImage.filter(album_id=album.id).order_by("added_at").prefetch_related("image")
    images = [j.image for j in joins if j.image is not None]
    return [_image_to_out(m) for m in images]


# ------------------------------
# Auto person folders (up to 10, unique IDs)
# ------------------------------
@api.post("/albums/person-folders/init")
async def init_person_folders(limit: int = Query(10, ge=1, le=20), user: AuthUser = Depends(require_user)):
    """
    Cluster faces, pick top-N persons by image count, and create N 'person' albums.
    Each album name includes a short unique ID derived from the cluster UUID.
    """
    results = await AlbumService.auto_generate_all_albums(user.user_id)
    # make sure we have person albums; then cap to top N with unique IDs in names
    created = await AlbumService.create_top_n_person_albums(user.user_id, top_n=limit)
    return {
        "clusters_found": len(results.get("person_clusters", [])),
        "created_albums": [
            {"album_id": str(a.id), "name": a.name}
            for a in created
        ],
    }

@api.get("/albums/persons", response_model=List[PersonClusterOut])
async def list_person_clusters(user: AuthUser = Depends(require_user)):
    clusters = await PersonCluster.filter(user_id=user.user_id).prefetch_related("faces")
    out: List[PersonClusterOut] = []
    for c in clusters:
        faces_count = await Face.filter(cluster_id=c.id).count()
        out.append(PersonClusterOut(id=c.id, label=c.label, faces=faces_count))
    return out


# ------------------------------
# Search
# ------------------------------
@api.get("/search")
async def search_images(
    q: str = Query(..., min_length=1),
    top_k: int = Query(20, le=100),
    faces_only: bool = Query(False),
    tags: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    user: AuthUser = Depends(require_user),
):
    query_vec = text_embedding(q)
    imgs = await Image.filter(user_id=user.user_id).all()
    scored: List[Tuple[float, Image]] = []
    for m in imgs:
        if m.embedding_json:
            score = _cosine(query_vec, list(map(float, m.embedding_json)))
            scored.append((score, m))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:top_k]

    # Optional filters
    if faces_only:
        # Only evaluate faces for top results to limit DB calls
        filtered = []
        for score, m in top:
            if await Face.filter(image_id=m.id).exists():
                filtered.append((score, m))
        top = filtered

    if tags or category:
        from app.services.ai_metadata_store import load_metadata
        tag_set = {t.strip().lower() for t in (tags or "").split(",") if t and t.strip()} if tags else set()
        cat = (category or "").strip().lower() if category else None
        filtered = []
        for score, m in top:
            meta = load_metadata(str(user.user_id), str(m.id)) or {}
            mtags = {t.lower() for t in (meta.get("tags") or [])}
            mcats = {c.lower() for c in (meta.get("categories") or [])}
            ok = True
            if tag_set:
                ok = ok and tag_set.issubset(mtags)
            if cat:
                ok = ok and (cat in mcats)
            if ok:
                filtered.append((score, m))
        top = filtered

    return {
        "query": q,
        "results": [{"image": _image_to_out(m), "score": float(score)} for score, m in top],
    }