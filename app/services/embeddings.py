import numpy as np
from typing import List
from app.services.vision import to_rgb_np, preprocess_rgb, detect_faces_embeddings


from app.config import settings

_provider = getattr(settings, "EMBEDDINGS_PROVIDER", None)
_model = None

def _ensure_clip() -> bool:
    """Lazily initialize CLIP model; fallback to phash if unavailable."""
    global _model, _provider
    if _provider != "clip":
        return False
    if _model is not None:
        return True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(getattr(settings, "CLIP_MODEL", "clip-ViT-B-32"))
        return True
    except Exception:
        # Fallback when sentence_transformers/huggingface_hub mismatch or missing
        _provider = "phash"
        _model = None
        return False

def get_image_embedding(img_bytes: bytes):
    rgb = to_rgb_np(img_bytes)
    rgb = preprocess_rgb(rgb)
    faces = detect_faces_embeddings(rgb)
    return faces

# Return 512-dim float32 vector (pad/trim as needed)
def image_embedding(np_rgb: np.ndarray) -> np.ndarray:
    global _model
    if _ensure_clip():
        from PIL import Image
        vec = _model.encode(Image.fromarray(np_rgb), normalize_embeddings=True)
        return vec.astype(np.float32)
    else:
        from PIL import Image
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
    import hashlib
    h = hashlib.sha256(query.lower().encode()).digest()
    arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
    arr = (arr - arr.mean()) / (arr.std() + 1e-6)
    if arr.shape[0] < 512:
        arr = np.pad(arr, (0, 512 - arr.shape[0]))
    return arr[:512]