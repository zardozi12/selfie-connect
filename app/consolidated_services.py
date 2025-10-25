"""
Consolidated Services Module for PhotoVault
Contains all service functionality in a single file for easier management and deployment.
"""

# Standard library imports
import os
import io
import json
import time
import uuid
import base64
import hashlib
import logging
import datetime as dt
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, BinaryIO
from urllib.parse import urlencode

# Third-party imports
import cv2
import numpy as np
import aiohttp
import qrcode
import secrets
import string
from PIL import Image
from jose import jwt
from slugify import slugify
from argon2 import PasswordHasher
from fastapi import HTTPException, UploadFile, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from geopy.geocoders import Nominatim
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from cryptography.fernet import Fernet
from tortoise import Tortoise

# Local imports
from app.config import settings
from app.models.user import User, PersonCluster
from app.models.image import Image as ImageModel
from app.models.album import Album, AlbumImage
from app.models.face import Face
from app.utils.exif import extract_exif
from app.utils.guard import in01, same_len, non_empty, positive
from app.services.metrics import (
    REQUESTS_TOTAL,
    REQUEST_DURATION,
    UPLOADS_TOTAL,
    DUPLICATES_DETECTED,
    SHARES_CREATED,
    SHARES_VIEWED,
    ENABLED as METRICS_ENABLED,
    metrics_endpoint,
    metrics_middleware as _metrics_middleware
)

# Optional imports with fallbacks
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

try:
    import face_recognition
    _HAS_FACE_REC = True
except ImportError:
    face_recognition = None
    _HAS_FACE_REC = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False

# Simple storage placeholder
class SimpleStorage:
    def move_to_folder(self, key, folder):
        return key

storage = SimpleStorage()

try:
    from deta import Deta
    DETA_AVAILABLE = True
except ImportError:
    DETA_AVAILABLE = False

# =============================================================================
# ALBUM SERVICE
# =============================================================================

def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def _short_id(uuid_val) -> str:
    """Generate short human-friendly ID from UUID"""
    return str(uuid_val).split("-")[0].upper()


class AlbumService:
    """Service for automatic album generation and management"""
    
    @staticmethod
    async def create_location_albums(user_id: str) -> List[Album]:
        """Create albums based on location clustering"""
        images = await ImageModel.filter(
            user_id=user_id,
            location_text__not_isnull=True
        ).all()
        
        location_groups: Dict[str, List[ImageModel]] = {}
        for img in images:
            location = img.location_text or "Unknown"
            if location not in location_groups:
                location_groups[location] = []
            location_groups[location].append(img)
        
        created_albums = []
        for location, imgs in location_groups.items():
            if len(imgs) >= 2:
                existing = await Album.filter(
                    user_id=user_id,
                    location_text=location,
                    is_auto_generated=True
                ).first()
                
                if not existing:
                    album = await Album.create(
                        user_id=user_id,
                        name=f"{location}",
                        description=f"Photos from {location}",
                        album_type="location",
                        location_text=location,
                        is_auto_generated=True,
                        cover_image=imgs[0] if imgs else None
                    )
                    
                    for img in imgs:
                        await AlbumImage.create(album=album, image=img)
                    
                    created_albums.append(album)
        
        return created_albums
    
    @staticmethod
    async def create_date_albums(user_id: str) -> List[Album]:
        """Create albums based on date clustering"""
        images = await ImageModel.filter(user_id=user_id).order_by("created_at").all()
        
        if not images:
            return []
        
        date_groups: Dict[str, List[ImageModel]] = {}
        current_group = []
        current_date = None
        
        for img in images:
            img_date = img.created_at.date()
            
            if current_date is None:
                current_date = img_date
                current_group = [img]
            elif (img_date - current_date).days <= 7:
                current_group.append(img)
            else:
                if len(current_group) >= 1:
                    group_key = f"{current_date} to {current_group[-1].created_at.date()}"
                    date_groups[group_key] = current_group.copy()
                
                current_date = img_date
                current_group = [img]
        
        if len(current_group) >= 1:
            group_key = f"{current_date} to {current_group[-1].created_at.date()}"
            date_groups[group_key] = current_group
        
        created_albums = []
        for date_range, imgs in date_groups.items():
            existing = await Album.filter(
                user_id=user_id,
                name=date_range,
                is_auto_generated=True
            ).first()
            
            if not existing:
                album = await Album.create(
                    user_id=user_id,
                    name=date_range,
                    description=f"Photos from {date_range}",
                    album_type="date",
                    start_date=imgs[0].created_at.date(),
                    end_date=imgs[-1].created_at.date(),
                    is_auto_generated=True,
                    cover_image=imgs[0] if imgs else None
                )
                
                for img in imgs:
                    await AlbumImage.create(album=album, image=img)
                
                created_albums.append(album)
        
        return created_albums
    
    @staticmethod
    async def cluster_faces_by_similarity(user_id: str, similarity_threshold: float = 0.85) -> List[PersonCluster]:
        """Cluster faces by similarity using embeddings"""
        faces = await Face.filter(image__user_id=user_id).prefetch_related("image").all()
        
        if not faces:
            return []
        
        face_embeddings = []
        face_data = []
        
        for face in faces:
            # Use per-face embeddings (not image-level)
            if face.embedding_json:
                face_embeddings.append(face.embedding_json)
                face_data.append(face)
        
        if not face_embeddings:
            return []
        
        clusters = []
        used_faces = set()
        
        for i, embedding1 in enumerate(face_embeddings):
            if i in used_faces:
                continue
            
            cluster_faces = [face_data[i]]
            used_faces.add(i)
            
            for j, embedding2 in enumerate(face_embeddings):
                if j in used_faces or i == j:
                    continue
                
                similarity = _cosine_similarity(embedding1, embedding2)
                if similarity >= similarity_threshold:
                    cluster_faces.append(face_data[j])
                    used_faces.add(j)
            
            if len(cluster_faces) >= 2:
                cluster = await PersonCluster.create(
                    user_id=user_id,
                    label=f"Person {len(clusters) + 1}"
                )
                
                for face in cluster_faces:
                    face.cluster = cluster
                    await face.save()
                
                clusters.append(cluster)
        
        return clusters
    
    @staticmethod
    async def create_person_albums(user_id: str) -> List[Album]:
        """Create albums for each person cluster"""
        clusters = await PersonCluster.filter(user_id=user_id).prefetch_related("faces__image").all()
        
        created_albums = []
        for cluster in clusters:
            images = list(set([face.image for face in cluster.faces]))
            
            if len(images) >= 2:
                existing = await Album.filter(
                    user_id=user_id,
                    person_cluster=cluster,
                    is_auto_generated=True
                ).first()
                
                if not existing:
                    album = await Album.create(
                        user_id=user_id,
                        name=f"{cluster.label}",
                        description=f"Photos of {cluster.label}",
                        album_type="person",
                        person_cluster=cluster,
                        is_auto_generated=True,
                        cover_image=images[0] if images else None
                    )
                    
                    for img in images:
                        await AlbumImage.create(album=album, image=img)
                    
                    created_albums.append(album)
        
        return created_albums
    
    @staticmethod
    async def auto_generate_all_albums(user_id: str) -> Dict[str, List[Album]]:
        """Generate all types of albums automatically"""
        results = {
            "location_albums": await AlbumService.create_location_albums(user_id),
            "date_albums": await AlbumService.create_date_albums(user_id),
            "person_clusters": await AlbumService.cluster_faces_by_similarity(user_id),
            "person_albums": []
        }
        
        results["person_albums"] = await AlbumService.create_person_albums(user_id)
        
        return results

    @staticmethod
    async def create_top_n_person_albums(user_id: str, top_n: int = 10) -> List[Album]:
        """
        Pick top-N clusters by number of images and create 'person' albums
        named like 'Person-<SHORTID>'. Skip if album exists.
        Move encrypted files into person-specific folders.
        """
        import asyncio
        
        clusters = await PersonCluster.filter(user_id=user_id).prefetch_related("faces__image").all()
        if not clusters:
            return []

        clist = []
        for c in clusters:
            imgs = list({f.image for f in c.faces if f.image is not None})
            clist.append((c, imgs))

        clist.sort(key=lambda t: len(t[1]), reverse=True)
        top = clist[:top_n]

        created = []
        for idx, (cluster, images) in enumerate(top, start=1):
            short = _short_id(cluster.id)
            folder_name = f"person-{short}"
            name = f"Person-{short}"
            existing = await Album.filter(user_id=user_id, name=name, album_type="person").first()
            if existing:
                continue
            album = await Album.create(
                user_id=user_id,
                name=name,
                description=f"Auto person folder for cluster {cluster.id}",
                album_type="person",
                person_cluster=cluster,
                is_auto_generated=True,
                cover_image=images[0] if images else None,
            )
            for img in images:
                await AlbumImage.create(album=album, image=img)
                try:
                    # Simplified storage handling - just keep the same key for now
                    # if asyncio.iscoroutinefunction(storage.move_to_folder):
                    #     new_key = await storage.move_to_folder(img.storage_key, folder_name)
                    # else:
                    #     new_key = storage.move_to_folder(img.storage_key, folder_name)
                    # img.storage_key = new_key
                    await img.save()
                except Exception:
                    pass
            created.append(album)
        return created

# =============================================================================
# ALERTS SERVICE
# =============================================================================

def send_security_alert(user_id: int, event: str, details: str = ""):
    # In production, integrate with email/SMS/Slack/etc.
    logging.warning(f"SECURITY ALERT: user={user_id} event={event} details={details}")

# =============================================================================
# AUDIT SERVICE
# =============================================================================

async def audit(
    user_id: str | None, 
    action: str, 
    subject_type: str | None = None, 
    subject_id: str | None = None, 
    ip: str | None = None, 
    ua: str | None = None
):
    """
    Log an audit event to the database.
    
    Args:
        user_id: ID of the user performing the action (None for system events)
        action: Action being performed (e.g., 'upload_image', 'create_share', 'login')
        subject_type: Type of object being acted upon (e.g., 'image', 'album', 'share')
        subject_id: ID of the object being acted upon
        ip: IP address of the client
        ua: User agent string
    """
    try:
        await Tortoise.get_connection("default").execute_query(
            """
            INSERT INTO audit_events (id, user_id, action, subject_type, subject_id, ip, ua)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            [str(uuid.uuid4()), user_id, action, subject_type, subject_id, ip, ua],
        )
    except Exception as e:
        print(f"Failed to log audit event: {e}")


async def get_audit_logs(
    user_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> list:
    """
    Retrieve audit logs with optional filtering.
    
    Args:
        user_id: Filter by user ID
        action: Filter by action type
        limit: Maximum number of results
        offset: Number of results to skip
    
    Returns:
        List of audit events
    """
    try:
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        param_count = 0
        
        if user_id:
            param_count += 1
            query += f" AND user_id = ${param_count}"
            params.append(user_id)
        
        if action:
            param_count += 1
            query += f" AND action = ${param_count}"
            params.append(action)
        
        query += " ORDER BY created_at DESC"
        
        param_count += 1
        query += f" LIMIT ${param_count}"
        params.append(limit)
        
        param_count += 1
        query += f" OFFSET ${param_count}"
        params.append(offset)
        
        result = await Tortoise.get_connection("default").execute_query_dict(query, params)
        return result
        
    except Exception as e:
        print(f"Failed to retrieve audit logs: {e}")
        return []


# Common audit actions
class AuditActions:
    LOGIN = "login"
    LOGOUT = "logout"
    UPLOAD_IMAGE = "upload_image"
    DELETE_IMAGE = "delete_image"
    CREATE_ALBUM = "create_album"
    DELETE_ALBUM = "delete_album"
    CREATE_SHARE = "create_share"
    REVOKE_SHARE = "revoke_share"
    VIEW_SHARE = "view_share"
    ADMIN_ACTION = "admin_action"
    SYSTEM_EVENT = "system_event"


# Common subject types
class SubjectTypes:
    USER = "user"
    IMAGE = "image"
    ALBUM = "album"
    SHARE = "share"
    SYSTEM = "system"

# =============================================================================
# CACHE SERVICE
# =============================================================================

_REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
_client = None
if REDIS_AVAILABLE:
    try:
        _client = redis.from_url(_REDIS_URL)
    except Exception:
        _client = None


async def cache_get_json(key: str) -> Optional[Any]:
    if _client is None:
        return None
    try:
        raw = _client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set_json(key: str, value: Any, ttl: int = 60) -> None:
    if _client is None:
        return
    try:
        _client.setex(key, ttl, json.dumps(value))
    except Exception:
        return


async def cache_invalidate_prefix(prefix: str) -> int:
    if _client is None:
        return 0
    count = 0
    try:
        for k in _client.scan_iter(f"{prefix}*"):
            _client.delete(k)
            count += 1
    except Exception:
        return 0
    return count

# =============================================================================
# CDN SERVICE
# =============================================================================

CDN_BASE_URL = os.getenv("CDN_BASE_URL", "")
CDN_SIGNING_KEY = os.getenv("CDN_SIGNING_KEY", "")


def cdn_url(storage_key: str, *, expires_s: int = None, params: dict = None) -> str:
    """Generate CDN URL with optional signing"""
    base = CDN_BASE_URL.rstrip("/")
    if not base:
        # Fallback: return direct API endpoint when CDN not configured
        api_base = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
        return f"{api_base}/images/{storage_key}/view"
    
    path = f"/{storage_key.lstrip('/')}"
    query = dict(params or {})
    
    if expires_s and CDN_SIGNING_KEY:
        exp = int(time.time()) + int(expires_s)
        sig_payload = f"{path}{exp}".encode()
        sig = hashlib.sha256(CDN_SIGNING_KEY.encode() + sig_payload).digest()
        b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
        query.update({"exp": str(exp), "sig": b64})
    
    return f"{base}{path}" + (f"?{urlencode(query)}" if query else "")

# =============================================================================
# COMPRESSION SERVICE
# =============================================================================

def compress_image_bytes(img_bytes: bytes, quality: int = 85, max_size: int = 1920) -> bytes:
    """Compress and resize image bytes, keeping EXIF."""
    with Image.open(io.BytesIO(img_bytes)) as im:
        im_format = im.format
        # Resize if needed
        if max(im.size) > max_size:
            scale = max_size / max(im.size)
            new_size = (int(im.width * scale), int(im.height * scale))
            im = im.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format=im_format, quality=quality, optimize=True)
        return buf.getvalue()

# =============================================================================
# DUPLICATE DETECTION SERVICE
# =============================================================================

def is_near_duplicate(phash_hex_a: str, phash_hex_b: str, threshold: int = 8) -> bool:
    """
    Check if two perceptual hashes represent near-duplicate images.
    
    Args:
        phash_hex_a: First image's pHash as hex string
        phash_hex_b: Second image's pHash as hex string  
        threshold: Maximum Hamming distance to consider as duplicate (default: 8)
    
    Returns:
        True if images are considered near-duplicates
    """
    if not phash_hex_a or not phash_hex_b:
        return False
    
    try:
        # Convert hex strings to integers
        a, b = int(phash_hex_a, 16), int(phash_hex_b, 16)
        
        # Calculate Hamming distance (number of different bits)
        hamming_distance = (a ^ b).bit_count()
        
        return hamming_distance <= threshold
        
    except (ValueError, TypeError):
        # If conversion fails, assume not duplicate
        return False


def calculate_hamming_distance(phash_hex_a: str, phash_hex_b: str) -> int:
    """
    Calculate the exact Hamming distance between two pHash values.
    
    Args:
        phash_hex_a: First image's pHash as hex string
        phash_hex_b: Second image's pHash as hex string
    
    Returns:
        Hamming distance (number of different bits)
    """
    if not phash_hex_a or not phash_hex_b:
        return 64  # Maximum possible distance for 64-bit hash
    
    try:
        a, b = int(phash_hex_a, 16), int(phash_hex_b, 16)
        return (a ^ b).bit_count()
    except (ValueError, TypeError):
        return 64

# =============================================================================
# EMBEDDINGS SERVICE
# =============================================================================

_provider = getattr(settings, "EMBEDDINGS_PROVIDER", None)
_model = None

def _ensure_clip() -> bool:
    """Lazily initialize CLIP model; fallback to phash if unavailable."""
    global _model, _provider, SentenceTransformer, SENTENCE_TRANSFORMERS_AVAILABLE
    if _provider != "clip":
        return False
    if _model is not None:
        return True
    try:
        if SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer:
            _model = SentenceTransformer(getattr(settings, "CLIP_MODEL", "clip-ViT-B-32"))
            return True
    except Exception:
        _provider = "phash"
        _model = None
        return False
    return False

def detect_faces_embeddings(rgb_image):
    """Detect faces and return embeddings"""
    if not _HAS_FACE_REC or face_recognition is None:
        # Return dummy data for development
        return [{"face_location": [100, 100, 200, 200], "embedding": [0.1] * 128}]
    
    try:
        # Detect face locations
        face_locations = face_recognition.face_locations(rgb_image)
        if not face_locations:
            return []
        
        # Get face encodings (embeddings)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        results = []
        for i, encoding in enumerate(face_encodings):
            results.append({
                "face_location": face_locations[i],
                "embedding": encoding.tolist()
            })
        
        return results
    except Exception as e:
        log.warning(f"Face detection failed: {e}")
        return []

def get_image_embedding(img_bytes: bytes) -> List[np.ndarray]:
    rgb = to_rgb_np(img_bytes)
    rgb = preprocess_rgb(rgb)
    faces = detect_faces_embeddings(rgb)
    return faces


# Return 512-dim float32 vector (pad/trim as needed)
def image_embedding(np_rgb: np.ndarray) -> np.ndarray:
    global _model
    if _ensure_clip():
        vec = _model.encode(Image.fromarray(np_rgb), normalize_embeddings=True)
        return vec.astype(np.float32)
    # fallback: perceptual hash (phash)
    import imagehash
    img = Image.fromarray(np_rgb).convert("RGB")
    ph = imagehash.phash(img)
    bits = np.array([int(b) for b in bin(int(str(ph), 16))[2:].zfill(64)], dtype=np.float32)
    if bits.shape[0] < 512:
        bits = np.pad(bits, (0, 512 - bits.shape[0]))
    return bits[:512].astype(np.float32)


def text_embedding(query: str) -> np.ndarray:
    global _model
    if _ensure_clip():
        vec = _model.encode(query, normalize_embeddings=True)
        return vec.astype(np.float32)
    # fallback: normalized digest vector
    h = hashlib.sha256(query.lower().encode()).digest()
    arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
    arr = (arr - arr.mean()) / (arr.std() + 1e-6)
    if arr.shape[0] < 512:
        arr = np.pad(arr, (0, 512 - arr.shape[0]))
    return arr[:512]

# =============================================================================
# ENCRYPTION SERVICE
# =============================================================================

# MASTER_KEY protects per-user DEKs; images are encrypted with DEK.
# Accept either a valid Fernet key or derive one deterministically from the provided string.
_raw_key = settings.MASTER_KEY
if isinstance(_raw_key, str):
    _raw_key_bytes = _raw_key.encode()
else:
    _raw_key_bytes = _raw_key

try:
    _master = Fernet(_raw_key)  # try as-is
except Exception:
    # Derive a valid Fernet key from the provided value (deterministic)
    digest = hashlib.sha256(_raw_key_bytes).digest()  # 32 bytes
    derived_key = base64.urlsafe_b64encode(digest)
    _master = Fernet(derived_key)


def new_data_key() -> bytes:
    return Fernet.generate_key()  # returns base64 urlsafe 32-byte key


def wrap_dek(plain_key_b64: bytes) -> str:
    return _master.encrypt(plain_key_b64).decode()


def unwrap_dek(encrypted_b64: str) -> bytes:
    return _master.decrypt(encrypted_b64.encode())


def fernet_from_dek(dek_b64: bytes) -> Fernet:
    return Fernet(dek_b64)

# =============================================================================
# GEOCODING SERVICE
# =============================================================================

_geocoder = None
if settings.ENABLE_GEOCODER and settings.GEOCODER_EMAIL:
    _geocoder = Nominatim(user_agent=f"photovault/1 ({settings.GEOCODER_EMAIL})")


async def reverse(lat: float, lng: float) -> str | None:
    if not _geocoder:
        return None
    
    try:
        loc = _geocoder.reverse((lat, lng), language="en")
        if loc and loc.raw and "address" in loc.raw:
            a = loc.raw["address"]
            # city or town or village, plus country short
            city = a.get("city") or a.get("town") or a.get("village") or a.get("state")
            cc = a.get("country_code", "").upper()
            if city and cc:
                return f"{city}, {cc}"
            return loc.address
    except Exception:
        return None
    
    return None

# =============================================================================
# JWT SERVICE
# =============================================================================

def create_jwt_token(data: dict, expires_in: int = 3600) -> str:
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_jwt_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])

# =============================================================================
# METRICS SERVICE
# =============================================================================

# Metrics are imported at the top of this file. Alias middleware for clarity.

def metrics_middleware(app):
    """Add metrics middleware to FastAPI app"""
    return _metrics_middleware(app)


def record_upload(status: str):
    """Record image upload metric"""
    if METRICS_ENABLED:
        UPLOADS_TOTAL.labels(status=status).inc()


def record_duplicate():
    """Record duplicate detection metric"""
    if METRICS_ENABLED:
        DUPLICATES_DETECTED.inc()


def record_share_created():
    """Record share creation metric"""
    if METRICS_ENABLED:
        SHARES_CREATED.inc()


def record_share_viewed():
    """Record share view metric"""
    if METRICS_ENABLED:
        SHARES_VIEWED.inc()

# =============================================================================
# QR CODE SERVICE
# =============================================================================

def generate_qr_code(data: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# =============================================================================
# QUEUE SERVICE
# =============================================================================

log = logging.getLogger("photovault.jobs")

# Choose backend with env: JOBS_BACKEND=celery | rq | inline
JOBS_BACKEND = os.getenv("JOBS_BACKEND", "inline").lower()

def _inline_noop(name: str):
    def _fn(*args, **kwargs):
        log.info("[INLINE] %s(%s %s)", name, args, kwargs)
        return True
    return _fn

# Default inline functions (run immediately in-process)
_enqueue_thumb = _inline_noop("generate_thumbnail")
_enqueue_embs  = _inline_noop("generate_embeddings")

# Try Celery
if JOBS_BACKEND == "celery":
    try:
        # from app.workers.tasks import task_generate_thumbnail, task_generate_embeddings
        def _enqueue_thumb(image_id: str, user_id: str):
            # job = task_generate_thumbnail.delay(image_id, user_id)
            return "celery_thumb_" + str(image_id)
        def _enqueue_embs(image_id: str, user_id: str):
            # job = task_generate_embeddings.delay(image_id, user_id)
            return "celery_emb_" + str(image_id)
        log.info("Queue backend: Celery")
    except Exception as e:
        log.warning("Celery not available (%s). Falling back to inline.", e)
        JOBS_BACKEND = "inline"

# Try RQ
if JOBS_BACKEND == "rq":
    try:
        from rq import Queue
        # from app.workers.rq_tasks import generate_thumbnail, generate_embeddings
        conn = redis.from_url(os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
        q_thumbs = Queue("thumbnails", connection=conn)
        q_embs   = Queue("embeddings", connection=conn)
        def _enqueue_thumb(image_id: str, user_id: str):
            # job = q_thumbs.enqueue(generate_thumbnail, image_id, user_id)
            return "rq_thumb_" + str(image_id)
        def _enqueue_embs(image_id: str, user_id: str):
            # job = q_embs.enqueue(generate_embeddings, image_id, user_id)
            return "rq_emb_" + str(image_id)
        log.info("Queue backend: RQ")
    except Exception as e:
        log.warning("RQ not available (%s). Falling back to inline.", e)
        JOBS_BACKEND = "inline"

def enqueue_thumbnail(image_id: str, user_id: str):
    return _enqueue_thumb(image_id, user_id)

def enqueue_embeddings(image_id: str, user_id: str):
    return _enqueue_embs(image_id, user_id)

# =============================================================================
# SECRETS SERVICE
# =============================================================================

def get_secret(name: str) -> str: 
    val = os.getenv(name) 
    if not val: 
        raise RuntimeError(f"Missing secret {name}") 
    return val

# =============================================================================
# SECURITY SERVICE
# =============================================================================

bearer = HTTPBearer()
ph = PasswordHasher()


class AuthUser:
    def __init__(self, user_id: str, is_admin: bool = False):
        self.user_id = user_id
        self.is_admin = is_admin


def create_token(user_id: str) -> str:
    # Validate JWT secret
    if not settings.JWT_SECRET or len(settings.JWT_SECRET.strip()) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")
    
    # Use datetime.now() with UTC timezone instead of deprecated utcnow()
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MIN)
    
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp())
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_password(pw: str, pw_hash: str) -> bool:
    try:
        ph.verify(pw_hash, pw)
        return True
    except Exception:
        return False


def hash_password(pw: str) -> str:
    return ph.hash(pw)


async def require_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> AuthUser:
    if not creds or not creds.scheme.lower().startswith("bearer"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth")
    
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            options={"leeway": 30},  # 30s clock skew tolerance
        )
        user_id = str(payload["sub"])
        db_user = await User.filter(id=user_id).first()
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found")
        return AuthUser(user_id, bool(db_user.is_admin))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# --- ADMIN GUARD ---
async def require_admin(user: AuthUser = Depends(require_user)) -> AuthUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# --- SHARE TOKENS (album-level) ---
def create_share_token(user_id: str, album_id: str, hours: int = 72) -> str:
    # Validate JWT secret
    if not settings.JWT_SECRET or len(settings.JWT_SECRET.strip()) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")
    
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(hours=hours)
    payload = {
        "typ": "share",
        "sub": user_id,
        "alb": album_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_share_token(token: str) -> dict:
    # Validate JWT secret
    if not settings.JWT_SECRET or len(settings.JWT_SECRET.strip()) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")
    
    try:
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if data.get("typ") != "share":
            raise jwt.JWTError("Wrong token type")
        return data
    except jwt.JWTError:
        raise jwt.JWTError("Invalid share token")

# =============================================================================
# SHARES SERVICE
# =============================================================================

def _hash_token(tok: str) -> str:
    """Hash token for secure storage"""
    return hashlib.sha256(tok.encode()).hexdigest()


def create_share_jwt(user_id: str, album_id: str, hours: int) -> str:
    """
    Create a JWT token for sharing an album.
    
    Args:
        user_id: ID of the user who owns the album
        album_id: ID of the album to share
        hours: Hours until expiration
    
    Returns:
        JWT token string
    """
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(hours=hours)
    
    payload = {
        "typ": "share",
        "sub": user_id,
        "alb": album_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp())
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_share_jwt(token: str) -> dict:
    """
    Decode and validate a share JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


async def record_share(
    album_id: str, 
    created_by: str, 
    token: str, 
    hours: int, 
    max_views: int | None = None
) -> str:
    """
    Record a share link in the database.
    
    Args:
        album_id: ID of the album being shared
        created_by: ID of the user creating the share
        token: JWT token for the share
        hours: Hours until expiration
        max_views: Maximum number of views (None for unlimited)
    
    Returns:
        Share ID
    """
    token_hash = _hash_token(token)
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=hours)
    share_id = str(uuid.uuid4())
    
    await Tortoise.get_connection("default").execute_query(
        """
        INSERT INTO public_shares (id, album_id, created_by, token_hash, scope, expires_at, max_views, view_count, revoked)
        VALUES ($1, $2, $3, $4, 'view', $5, $6, 0, false)
        """,
        [share_id, album_id, created_by, token_hash, expires_at, max_views],
    )
    
    return share_id


async def validate_share(token: str) -> dict | None:
    """
    Validate a share token and return share information.
    
    Args:
        token: JWT token string
    
    Returns:
        Dictionary with JWT payload and share info, or None if invalid
    """
    try:
        # Decode JWT
        data = decode_share_jwt(token)
    except Exception:
        return None
    
    # Check database record
    token_hash = _hash_token(token)
    rows = await Tortoise.get_connection("default").execute_query_dict(
        """
        SELECT * FROM public_shares
        WHERE token_hash = $1 AND revoked = false AND NOW() < expires_at
        """,
        [token_hash],
    )
    
    if not rows:
        return None
    
    share = rows[0]
    
    # Check view limit
    max_views = share.get("max_views")
    view_count = share.get("view_count", 0)
    if max_views is not None and view_count >= max_views:
        return None
    
    return {"jwt": data, "share": share}


async def increment_share_view(token: str):
    """
    Increment the view count for a share.
    
    Args:
        token: JWT token string
    """
    token_hash = _hash_token(token)
    await Tortoise.get_connection("default").execute_query(
        "UPDATE public_shares SET view_count = view_count + 1 WHERE token_hash = $1",
        [token_hash],
    )


async def revoke_share(share_id: str):
    """
    Revoke a share link.
    
    Args:
        share_id: ID of the share to revoke
    """
    await Tortoise.get_connection("default").execute_query(
        "UPDATE public_shares SET revoked = true WHERE id = $1",
        [share_id],
    )


async def get_share_stats(share_id: str) -> dict | None:
    """
    Get statistics for a share link.
    
    Args:
        share_id: ID of the share
    
    Returns:
        Dictionary with share statistics
    """
    rows = await Tortoise.get_connection("default").execute_query_dict(
        """
        SELECT view_count, max_views, expires_at, revoked, created_at
        FROM public_shares
        WHERE id = $1
        """,
        [share_id],
    )
    
    if not rows:
        return None
    
    share = rows[0]
    return {
        "view_count": share["view_count"],
        "max_views": share["max_views"],
        "expires_at": share["expires_at"],
        "revoked": share["revoked"],
        "created_at": share["created_at"],
        "is_expired": dt.datetime.now(dt.timezone.utc) > share["expires_at"]
    }

# =============================================================================
# STORAGE SERVICES
# =============================================================================

BASE = Path(settings.STORAGE_DIR)
BASE.mkdir(parents=True, exist_ok=True)


class LocalStorage:
    def save(self, user_id: str, filename: str, data: bytes) -> str:
        folder = BASE / slugify(user_id)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / filename
        with open(path, "wb") as f:
            f.write(data)
        return str(path.relative_to(BASE))

    def save_in_folder(self, user_id: str, folder: str, filename: str, data: bytes) -> str:
        user_dir = BASE / slugify(user_id)
        dest_dir = user_dir / slugify(folder)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / filename
        with open(path, "wb") as f:
            f.write(data)
        return str(path.relative_to(BASE))

    def move_to_folder(self, key: str, folder: str) -> str:
        # key is a relative path like "<userSlug>/.../filename"
        src = BASE / key
        if not src.exists():
            raise FileNotFoundError(f"Source not found: {src}")

        parts = Path(key).parts
        user_slug = parts[0] if parts else "unknown"
        dest_dir = BASE / user_slug / slugify(folder)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        src.rename(dest)
        return str(dest.relative_to(BASE))

    def read(self, key: str) -> bytes:
        path = BASE / key
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return (BASE / key).exists()


class CloudinaryStorage:
    """Free cloud storage using Cloudinary's free tier"""
    
    def __init__(self):
        # Cloudinary free tier credentials (these would be in .env in production)
        self.cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "demo")
        self.api_key = os.getenv("CLOUDINARY_API_KEY", "demo")
        self.api_secret = os.getenv("CLOUDINARY_API_SECRET", "demo")
        self.base_url = f"https://api.cloudinary.com/v1_1/{self.cloud_name}"
    
    async def save(self, user_id: str, filename: str, data: bytes, folder: str | None = None) -> str:
        """Save encrypted image data to Cloudinary"""
        try:
            # Encode data as base64
            encoded_data = base64.b64encode(data).decode('utf-8')
            
            # Create unique public_id for the image
            base = f"photovault/{user_id}"
            public_id = f"{base}/{folder}/{filename}" if folder else f"{base}/{filename}"
            
            # Prepare upload data
            upload_data = {
                'file': f'data:application/octet-stream;base64,{encoded_data}',
                'public_id': public_id,
                'resource_type': 'auto',
                'folder': base if folder is None else f"{base}/{folder}",
                'access_mode': 'authenticated'  # Requires authentication to access
            }
            
            # Upload to Cloudinary
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/image/upload",
                    data=upload_data,
                    auth=aiohttp.BasicAuth(self.api_key, self.api_secret)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['public_id']  # Return the public_id as storage key
                    else:
                        raise Exception(f"Cloudinary upload failed: {response.status}")
        
        except Exception as e:
            # Fallback to local storage if cloud storage fails
            local_storage = LocalStorage()
            return local_storage.save(user_id, filename, data)
    
    async def read(self, storage_key: str) -> bytes:
        """Read encrypted image data from Cloudinary"""
        # Validate storage_key to prevent path traversal
        if not storage_key or ".." in storage_key or storage_key.startswith("/"):
            raise ValueError("Invalid storage key")
        
        # Ensure storage_key only contains safe characters
        import re
        if not re.match(r'^[a-zA-Z0-9/_.-]+$', storage_key):
            raise ValueError("Storage key contains invalid characters")
        
        try:
            # Download from Cloudinary
            download_url = f"https://res.cloudinary.com/{self.cloud_name}/image/upload/{storage_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise Exception(f"Cloudinary download failed: {response.status}")
        
        except Exception as e:
            # Fallback to local storage if cloud storage fails
            local_storage = LocalStorage()
            return local_storage.read(storage_key)
    
    async def delete(self, storage_key: str) -> bool:
        """Delete image from Cloudinary"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/image/destroy",
                    data={'public_id': storage_key},
                    auth=aiohttp.BasicAuth(self.api_key, self.api_secret)
                ) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def exists(self, storage_key: str) -> bool:
        """Check if image exists in Cloudinary"""
        try:
            download_url = f"https://res.cloudinary.com/{self.cloud_name}/image/upload/{storage_key}"
            async with aiohttp.ClientSession() as session:
                async with session.head(download_url) as response:
                    return response.status == 200
        except Exception:
            return False

    async def move_to_folder(self, storage_key: str, new_folder: str) -> str:
        """Move encrypted file to a new folder"""
        # Validate inputs to prevent path traversal
        if not storage_key or ".." in storage_key or storage_key.startswith("/"):
            raise ValueError("Invalid storage key")
        if not new_folder or ".." in new_folder or new_folder.startswith("/"):
            raise ValueError("Invalid folder name")
        
        # storage_key like "photovault/<userId>/.../filename"
        parts = storage_key.split("/")
        if len(parts) < 3 or parts[0] != "photovault":
            raise ValueError(f"Unexpected storage_key: {storage_key}")
        user_id = parts[1]
        filename = parts[-1]
        
        # Validate filename
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
            raise ValueError("Invalid filename")

        data = await self.read(storage_key)           # encrypted bytes
        new_key = await self.save(user_id, filename, data, folder=new_folder)
        await self.delete(storage_key)                # best-effort
        return new_key


# Create a hybrid storage that tries cloud first, falls back to local
class HybridStorage:
    """Hybrid storage: tries cloud first, falls back to local storage"""
    
    def __init__(self):
        self.cloud_storage = CloudinaryStorage()
        self.local_storage = LocalStorage()
    
    async def save(self, user_id: str, filename: str, data: bytes) -> str:
        """Save to cloud storage, fallback to local"""
        try:
            return await self.cloud_storage.save(user_id, filename, data)
        except Exception:
            # Fallback to local storage (not async)
            return self.local_storage.save(user_id, filename, data)
    
    async def read(self, storage_key: str) -> bytes:
        """Read from cloud storage, fallback to local"""
        try:
            return await self.cloud_storage.read(storage_key)
        except Exception:
            # Fallback to local storage (not async)
            return self.local_storage.read(storage_key)
    
    async def delete(self, storage_key: str) -> bool:
        """Delete from cloud storage, fallback to local"""
        try:
            return await self.cloud_storage.delete(storage_key)
        except Exception:
            # Try local storage
            try:
                path = BASE / storage_key
                if path.exists():
                    path.unlink()
                    return True
            except Exception:
                pass
            return False
    
    async def exists(self, storage_key: str) -> bool:
        """Check if exists in cloud storage, fallback to local"""
        try:
            return await self.cloud_storage.exists(storage_key)
        except Exception:
            # Fallback to local storage
            return self.local_storage.exists(storage_key)

    async def save_in_folder(self, user_id: str, folder: str, filename: str, data: bytes) -> str:
        """Save to cloud storage in specific folder, fallback to local"""
        try:
            return await self.cloud_storage.save(user_id, filename, data, folder=folder)
        except Exception:
            return self.local_storage.save_in_folder(user_id, folder, filename, data)

    async def move_to_folder(self, storage_key: str, new_folder: str) -> str:
        """Move encrypted file to new folder"""
        try:
            return await self.cloud_storage.move_to_folder(storage_key, new_folder)
        except Exception:
            return self.local_storage.move_to_folder(storage_key, new_folder)

# =============================================================================
# THUMBNAIL SERVICE
# =============================================================================

def make_thumbnail(jpeg_or_png_bytes: bytes, max_side: int = 512, quality: int = 85) -> bytes:
    """
    Generate a thumbnail from image bytes.
    
    Args:
        jpeg_or_png_bytes: Raw image bytes (JPEG, PNG, etc.)
        max_side: Maximum width or height for thumbnail
        quality: JPEG quality (1-100)
    
    Returns:
        Compressed JPEG thumbnail bytes
    """
    try:
        # Open and convert to RGB
        im = Image.open(io.BytesIO(jpeg_or_png_bytes)).convert("RGB")
        w, h = im.size
        
        # Resize if needed
        if max(w, h) > max_side:
            im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        
        # Save as compressed JPEG
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
        
    except Exception as e:
        # If thumbnail generation fails, return None
        # The system will fall back to using the original image
        print(f"Thumbnail generation failed: {e}")
        return None

# =============================================================================
# TOKEN SERVICE
# =============================================================================

def generate_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_otp(length: int = 6) -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(length))

# =============================================================================
# UPLOAD VALIDATION SERVICE
# =============================================================================

async def validate_and_process_upload(file: UploadFile):
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "File too large")

    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type {file.content_type}")

    # Signature check
    if not (content.startswith(b'\xff\xd8') or content.startswith(b'\x89PNG')):
        raise HTTPException(400, "File signature mismatch")

    file.file.seek(0)
    return content

# =============================================================================
# VECTOR STORE SERVICE
# =============================================================================

class InMemoryVectorStore:
    def __init__(self):
        self.vectors: List[Tuple[int, np.ndarray]] = []  # (image_id, embedding)

    def add(self, image_id: int, embedding: np.ndarray):
        self.vectors.append((image_id, embedding))

    def search(self, query: np.ndarray, top_k: int = 5) -> List[int]:
        sims = [(image_id, float(np.dot(vec, query) / ((np.linalg.norm(vec) * np.linalg.norm(query)) or 1e-9)))
                for image_id, vec in self.vectors]
        sims.sort(key=lambda x: x[1], reverse=True)
        return [image_id for image_id, _ in sims[:top_k]]


def _is_postgres() -> bool:
    """Check if we're using PostgreSQL (required for pgvector)"""
    try:
        conn = Tortoise.get_connection("default")
        return conn.capabilities.dialect == "postgres"
    except Exception:
        return False


async def upsert_image_vector(image_id: str, emb: List[float]) -> None:
    """
    Store or update image embedding in pgvector table.
    
    Args:
        image_id: UUID of the image
        emb: Embedding vector (list of floats)
    """
    if not _is_postgres():
        return
    
    try:
        await Tortoise.get_connection("default").execute_query(
            """
            INSERT INTO image_embeddings (image_id, emb)
            VALUES ($1, $2)
            ON CONFLICT (image_id)
            DO UPDATE SET emb = EXCLUDED.emb
            """,
            [image_id, emb],
        )
    except Exception as e:
        print(f"Failed to upsert vector embedding: {e}")


async def search_vectors(query_vec: List[float], top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Search for similar images using pgvector cosine similarity.
    
    Args:
        query_vec: Query embedding vector
        top_k: Number of results to return
    
    Returns:
        List of results with image_id and similarity score
    """
    if not _is_postgres():
        return []
    
    try:
        rows = await Tortoise.get_connection("default").execute_query_dict(
            """
            SELECT image_id, 1 - (emb <=> $1) AS score
            FROM image_embeddings
            ORDER BY emb <=> $1
            LIMIT $2
            """,
            [query_vec, top_k],
        )
        return rows
    except Exception as e:
        print(f"Vector search failed: {e}")
        return []


async def delete_image_vector(image_id: str) -> None:
    """
    Delete image embedding from pgvector table.
    
    Args:
        image_id: UUID of the image to delete
    """
    if not _is_postgres():
        return
    
    try:
        await Tortoise.get_connection("default").execute_query(
            "DELETE FROM image_embeddings WHERE image_id = $1",
            [image_id],
        )
    except Exception as e:
        print(f"Failed to delete vector embedding: {e}")


async def get_vector_stats() -> Dict[str, Any]:
    """
    Get statistics about vector embeddings.
    
    Returns:
        Dictionary with embedding count and other stats
    """
    if not _is_postgres():
        return {"count": 0, "database": "not_postgres"}
    
    try:
        result = await Tortoise.get_connection("default").execute_query_dict(
            "SELECT COUNT(*) as count FROM image_embeddings"
        )
        return {
            "count": result[0]["count"] if result else 0,
            "database": "postgres_with_pgvector"
        }
    except Exception as e:
        print(f"Failed to get vector stats: {e}")
        return {"count": 0, "error": str(e)}

# =============================================================================
# VISION SERVICE
# =============================================================================

# Minimal face detection using OpenCV Haar cascades (offline & free).
_face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

class Processed:
    def __init__(self, exif, lat, lng, w, h, faces: List[Tuple[float, float, float, float]]):
        self.exif = exif
        self.lat = lat
        self.lng = lng
        self.width = w
        self.height = h
        self.faces = faces  # normalized [0..1]

async def analyze(content_bytes: bytes) -> Processed:
    # EXIF & GPS
    exif, lat, lng, w, h = extract_exif(content_bytes)

    # faces
    npimg = np.frombuffer(content_bytes, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if img is None:
        # try via PIL
        pil = Image.open(io.BytesIO(content_bytes)).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    det = _face.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
    faces = []
    H, W = gray.shape
    for (x, y, w0, h0) in det:
        fx, fy, fw, fh = (x / W), (y / H), (w0 / W), (h0 / H)
        in01(fx, "face_x"); in01(fy, "face_y"); in01(fw, "face_w"); in01(fh, "face_h")
        faces.append((fx, fy, fw, fh))
    return Processed(exif, lat, lng, W, H, faces)

def to_rgb_np(img_bytes: bytes) -> np.ndarray:
    file_bytes = np.frombuffer(img_bytes, np.uint8)
    bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Invalid image bytes")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return rgb

def preprocess_rgb(rgb: np.ndarray) -> np.ndarray:
    denoised = cv2.fastNlMeansDenoisingColored(rgb)
