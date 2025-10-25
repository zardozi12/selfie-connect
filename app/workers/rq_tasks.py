import asyncio
from app.models.image import Image
from app.models.user import User
from app.models.face import Face
from app.services.encryption import unwrap_dek, fernet_from_dek
from app.services.vision import to_rgb_np
from app.services.embeddings import image_embedding, text_embedding
from app.consolidated_services import storage, make_thumbnail
from app.services.ai_metadata_store import save_metadata

async def _load(image_id: str, user_id: str):
    img = await Image.filter(id=image_id, user_id=user_id).first()
    user = await User.filter(id=user_id).first()
    return user, img

def generate_thumbnail(image_id: str, user_id: str):
    async def run():
        user, img = await _load(image_id, user_id)
        if not user or not img or img.thumb_storage_key:
            return
        enc = storage.read(img.storage_key)
        dek = unwrap_dek(user.dek_encrypted_b64)
        f = fernet_from_dek(dek)
        plain = f.decrypt(enc)
        thumb = make_thumbnail(plain)
        if not thumb:
            return
        enc_thumb = f.encrypt(thumb)
        key = storage.save(str(user.id), f"{img.id}_thumb.jpg", enc_thumb)
        img.thumb_storage_key = key
        await img.save()
    return asyncio.run(run())

def generate_embeddings(image_id: str, user_id: str):
    async def run():
        user, img = await _load(image_id, user_id)
        if not user or not img:
            return
        enc = storage.read(img.storage_key)
        dek = unwrap_dek(user.dek_encrypted_b64)
        f = fernet_from_dek(dek)
        plain = f.decrypt(enc)
        np_rgb = await to_rgb_np(plain)
        emb = image_embedding(np_rgb)
        img.embedding_json = list(map(float, emb)) if emb is not None else None
        await img.save()
        try:
            from app.services.vector_store import upsert_image_vector
            await upsert_image_vector(str(img.id), emb)
        except Exception:
            pass
    return asyncio.run(run())

def ai_tagging(image_id: str, user_id: str):
    async def run():
        user, img = await _load(image_id, user_id)
        if not user or not img:
            return
        face_count = await Face.filter(image_id=img.id).count()
        contains_faces = face_count > 0
        categories = ["people"] if contains_faces else ["objects"]
        if (img.width or 1) / (img.height or 1) >= 1.2 and not contains_faces:
            categories.append("landscape")
        tags = [img.location_text] if img.location_text else []
        try:
            if img.embedding_json:
                import numpy as np
                ivec = np.array(img.embedding_json, dtype=np.float32)
                cand = ["portrait", "landscape", "objects", "people"]
                sims = [(c, float(np.dot(ivec, text_embedding(c)) / (np.linalg.norm(ivec) * np.linalg.norm(text_embedding(c)) + 1e-9))) for c in cand]
                best = sorted(sims, key=lambda t: t[1], reverse=True)[:1]
                for c, _ in best:
                    if c not in categories:
                        categories.append(c)
        except Exception:
            pass
        save_metadata(str(user.id), str(img.id), {
            "tags": tags,
            "categories": categories,
            "contains_faces": contains_faces,
            "face_count": face_count,
        })
    return asyncio.run(run())