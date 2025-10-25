"""
Background task system using RQ (Redis Queue)
Handles async processing for embeddings, thumbnails, and other heavy operations
"""

import os
from rq import Queue
from redis import Redis
from app.consolidated_services import (
    image_embedding,
    upsert_image_vector,
    analyze,
    to_rgb_np,
    make_thumbnail,
    storage,
    unwrap_dek,
    fernet_from_dek,
)
from app.models.image import Image
from app.models.user import User

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis = Redis.from_url(REDIS_URL)
queue = Queue("photovault", connection=_redis)


def enqueue(func_name: str, **kwargs):
    """Enqueue a background task"""
    queue.enqueue(func_name, **kwargs)


# ---- Worker functions (imported by RQ worker) ----

async def generate_embedding_and_vector(image_id: str):
    """
    Generate embedding and store in pgvector (background task)
    """
    try:
        img = await Image.filter(id=image_id).first()
        if not img:
            print(f"Image {image_id} not found")
            return
        
        # Load user and decrypt image
        user = await User.filter(id=img.user_id).first()
        if not user:
            print(f"User {img.user_id} not found")
            return
            
        dek_b64 = unwrap_dek(user.dek_encrypted_b64)
        fernet = fernet_from_dek(dek_b64)
        
        # Read and decrypt image
        enc = storage.read(img.storage_key)
        plain = fernet.decrypt(enc)
        
        # Convert to RGB numpy array
        np_rgb = await to_rgb_np(plain)
        
        # Generate embedding
        emb = image_embedding(np_rgb)
        
        # Save JSON embedding for fallback
        img.embedding_json = emb
        await img.save()
        
        # Store in pgvector
        await upsert_image_vector(str(img.id), emb)
        
        print(f"Generated embedding for image {image_id}")
        
    except Exception as e:
        print(f"Failed to generate embedding for {image_id}: {e}")


async def ensure_thumbnail(image_id: str):
    """
    Generate and store thumbnail (background task)
    """
    try:
        img = await Image.filter(id=image_id).first()
        if not img or img.thumb_storage_key:
            return  # Already has thumbnail
        
        # Load user and decrypt image
        user = await User.filter(id=img.user_id).first()
        if not user:
            print(f"User {img.user_id} not found")
            return
            
        dek_b64 = unwrap_dek(user.dek_encrypted_b64)
        fernet = fernet_from_dek(dek_b64)
        
        # Read and decrypt original image
        enc = storage.read(img.storage_key)
        plain = fernet.decrypt(enc)
        
        # Generate thumbnail
        thumb = make_thumbnail(plain)
        if not thumb:
            print(f"Failed to generate thumbnail for {image_id}")
            return
        
        # Encrypt thumbnail
        enc_thumb = fernet.encrypt(thumb)
        
        # Save thumbnail
        thumb_key = storage.save(
            str(user.id), 
            f"{img.id}_thumb.jpg", 
            enc_thumb
        )
        
        # Update image record
        img.thumb_storage_key = thumb_key
        await img.save()
        
        print(f"Generated thumbnail for image {image_id}")
        
    except Exception as e:
        print(f"Failed to generate thumbnail for {image_id}: {e}")


async def cleanup_expired_shares():
    """
    Clean up expired share links (background task)
    """
    try:
        from tortoise import Tortoise
        
        # Delete expired shares
        result = await Tortoise.get_connection("default").execute_query(
            "DELETE FROM public_shares WHERE expires_at < NOW() AND revoked = false"
        )
        
        print(f"Cleaned up {result[1]} expired shares")
        
    except Exception as e:
        print(f"Failed to cleanup expired shares: {e}")


# Helper function to start worker (for development)
def start_worker():
    """Start RQ worker (for development)"""
    from rq import Worker
    
    worker = Worker([queue], connection=_redis)
    print("Starting RQ worker...")
    worker.work()
