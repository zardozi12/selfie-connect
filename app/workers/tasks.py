import os
import asyncio
from typing import List, Optional, Dict
from celery import Celery
from app.config import settings, TORTOISE_ORM
from tortoise import Tortoise
from app.models.image import Image
from app.models.user import User
from app.models.face import Face
from app.services.encryption import unwrap_dek, fernet_from_dek
from app.services.vision import to_rgb_np
from app.services.embeddings import image_embedding, text_embedding
from app.consolidated_services import storage, make_thumbnail
from app.services.ai_metadata_store import save_metadata

BROKER = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER)

celery_app = Celery("photovault", broker=BROKER, backend=BACKEND)

async def _ensure_db():
    if not Tortoise._inited:
        await Tortoise.init(TORTOISE_ORM)

async def _load_user_image(image_id: str, user_id: str):
    await _ensure_db()
    img = await Image.filter(id=image_id, user_id=user_id).first()
    user = await User.filter(id=user_id).first()
    return user, img

def _decrypt_bytes(enc_bytes: bytes, user: User) -> Optional[bytes]:
    try:
        dek_b64 = unwrap_dek(user.dek_encrypted_b64)
        fernet = fernet_from_dek(dek_b64)
        return fernet.decrypt(enc_bytes)
    except Exception:
        return None

@celery_app.task(name="task_generate_thumbnail")
def task_generate_thumbnail(image_id: str, user_id: str):
    async def run():
        user, img = await _load_user_image(image_id, user_id)
        if not user or not img or img.thumb_storage_key:
            return
        enc_bytes = storage.read(img.storage_key)
        plain = _decrypt_bytes(enc_bytes, user)
        if not plain:
            return
        thumb = make_thumbnail(plain)
        if not thumb:
            return
        dek_b64 = unwrap_dek(user.dek_encrypted_b64)
        fernet = fernet_from_dek(dek_b64)
        enc_thumb = fernet.encrypt(thumb)
        key = storage.save(str(user.id), f"{img.id}_thumb.jpg", enc_thumb)
        img.thumb_storage_key = key
        await img.save()
    return asyncio.run(run())

@celery_app.task(name="task_generate_embeddings")
def task_generate_embeddings(image_id: str, user_id: str):
    async def run():
        user, img = await _load_user_image(image_id, user_id)
        if not user or not img:
            return
        enc_bytes = storage.read(img.storage_key)
        plain = _decrypt_bytes(enc_bytes, user)
        if not plain:
            return
        np_rgb = await to_rgb_np(plain)
        emb = image_embedding(np_rgb)
        img.embedding_json = list(map(float, emb)) if emb is not None else None
        await img.save()
        # Upsert into pgvector if enabled
        try:
            from app.services.vector_store import upsert_image_vector
            await upsert_image_vector(str(img.id), emb)
        except Exception:
            pass
    return asyncio.run(run())

@celery_app.task(name="task_ai_tagging")
def task_ai_tagging(image_id: str, user_id: str):
    async def run():
        user, img = await _load_user_image(image_id, user_id)
        if not user or not img:
            return
        enc_bytes = storage.read(img.storage_key)
        plain = _decrypt_bytes(enc_bytes, user)
        if not plain:
            return
        # Faces count
        face_count = await Face.filter(image_id=img.id).count()
        contains_faces = face_count > 0

        # Quick category heuristics
        categories: List[str] = []
        if contains_faces:
            categories.append("people")
        try:
            avg_aspect = (img.width or 1) / (img.height or 1)
            if avg_aspect >= 1.2 and not contains_faces:
                categories.append("landscape")
        except Exception:
            pass
        if not categories:
            categories.append("objects")

        # Simple tags: use location text if present
        tags: List[str] = []
        if img.location_text:
            tags.append(img.location_text)

        # Optional semantic category via CLIP if available
        try:
            if img.embedding_json:
                cand = ["portrait", "landscape", "objects", "people"]
                q_embs = [(c, text_embedding(c)) for c in cand]
                import numpy as np
                ivec = np.array(img.embedding_json, dtype=np.float32)
                sims = [(c, float(np.dot(ivec, q) / (np.linalg.norm(ivec) * np.linalg.norm(q) + 1e-9))) for c, q in q_embs]
                best = sorted(sims, key=lambda t: t[1], reverse=True)[:1]
                for c, _ in best:
                    if c not in categories:
                        categories.append(c)
        except Exception:
            pass

        meta: Dict[str, any] = {
            "tags": tags,
            "categories": categories,
            "contains_faces": contains_faces,
            "face_count": face_count,
        }
        save_metadata(str(user.id), str(img.id), meta)
    return asyncio.run(run())