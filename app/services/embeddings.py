from app.config import settings
import numpy as np


_provider = settings.EMBEDDINGS_PROVIDER

_model = None
if _provider == "clip":
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer(settings.CLIP_MODEL)


# Return 512-dim float32 vector (pad/trim as needed)
def image_embedding(np_rgb: np.ndarray) -> list[float]:
    global _model
    if _provider == "clip" and _model is not None:
        # sentence-transformers accepts PIL or file path; we'll use numpy via PIL
        from PIL import Image
        vec = _model.encode(Image.fromarray(np_rgb), normalize_embeddings=True)
        return vec.astype(np.float32).tolist()
    else:
        # fallback: perceptual hash (64 bits -> 64 floats)
        from PIL import Image
        import imagehash
        img = Image.fromarray(np_rgb).convert("RGB")
        ph = imagehash.phash(img)  # 64-bit
        bits = np.array([int(b) for b in bin(int(str(ph), 16))[2:].zfill(64)], dtype=np.float32)
        # pad to 512 dims
        if bits.shape[0] < 512:
            bits = np.pad(bits, (0, 512 - bits.shape[0]))
        return bits[:512].astype(np.float32).tolist()


def text_embedding(query: str) -> list[float]:
    global _model
    if _provider == "clip" and _model is not None:
        vec = _model.encode(query, normalize_embeddings=True)
        return vec.astype(np.float32).tolist()
    
    # simple bag-of-words hash as fallback
    import hashlib
    import math
    h = hashlib.sha256(query.lower().encode()).digest()
    arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
    arr = (arr - arr.mean()) / (arr.std() + 1e-6)
    if arr.shape[0] < 512:
        arr = np.pad(arr, (0, 512 - arr.shape[0]))
    return arr[:512].tolist()