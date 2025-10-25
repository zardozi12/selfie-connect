import os
import httpx
from typing import Optional, Tuple
import numpy as np
from app.services.vision import to_rgb_np, preprocess_rgb, detect_faces_embeddings, cosine_sim

# Face++ setup via environment
FACEPP_API_ENDPOINT = os.getenv("FACEPP_API_ENDPOINT", "https://api-us.faceplusplus.com")
FACEPP_API_KEY = os.getenv("FACEPP_API_KEY")
FACEPP_API_SECRET = os.getenv("FACEPP_API_SECRET")
CONFIDENCE_THRESHOLD = float(os.getenv("FACEPP_CONFIDENCE_THRESHOLD", "98.0"))  # percent

def _facepp_available() -> bool:
    return bool(FACEPP_API_KEY and FACEPP_API_SECRET)

async def _facepp_detect_face_token(image_bytes: bytes) -> Optional[str]:
    """
    Call Face++ detect to get a face_token for the provided image.
    """
    if not _facepp_available():
        return None
    url = f"{FACEPP_API_ENDPOINT}/facepp/v3/detect"
    data = {
        "api_key": FACEPP_API_KEY,
        "api_secret": FACEPP_API_SECRET,
        "return_landmark": 0,
        "return_attributes": "none",
    }
    files = {
        "image_file": ("upload.jpg", image_bytes, "application/octet-stream")
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, data=data, files=files)
        if r.status_code != 200:
            return None
        obj = r.json()
        faces = obj.get("faces") or []
        if not faces:
            return None
        ft = faces[0].get("face_token")
        return ft

async def _facepp_compare(face_token1: str, face_token2: str) -> Tuple[bool, float]:
    """
    Call Face++ compare for two face tokens. Returns (isMatch, confidencePercent).
    """
    url = f"{FACEPP_API_ENDPOINT}/facepp/v3/compare"
    data = {
        "api_key": FACEPP_API_KEY,
        "api_secret": FACEPP_API_SECRET,
        "face_token1": face_token1,
        "face_token2": face_token2,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, data=data)
        if r.status_code != 200:
            return (False, 0.0)
        obj = r.json()
        conf = float(obj.get("confidence", 0.0))
        return (conf >= CONFIDENCE_THRESHOLD, conf)

def _local_face_vector(image_bytes: bytes) -> Optional[np.ndarray]:
    try:
        rgb = to_rgb_np(image_bytes)
        rgb = preprocess_rgb(rgb)
        vecs = detect_faces_embeddings(rgb)
        if not vecs:
            return None
        return vecs[0]
    except Exception:
        return None

def _local_verify(stored_vec: np.ndarray, new_vec: np.ndarray, threshold: float = CONFIDENCE_THRESHOLD) -> Tuple[bool, float]:
    """
    Local fallback cosine similarity. Map threshold percent to 0..1 ratio by dividing by 100.
    """
    score = cosine_sim(stored_vec, new_vec)
    ok = score >= (threshold / 100.0)
    return (ok, score * 100.0)  # keep confidence in percent for consistency

async def register_face(image_bytes: bytes) -> Tuple[Optional[str], Optional[np.ndarray]]:
    """
    Returns (facepp_face_token, local_vector). Either may be None depending on availability/detection.
    """
    face_token = None
    if _facepp_available():
        face_token = await _facepp_detect_face_token(image_bytes)
    local_vec = _local_face_vector(image_bytes)
    return (face_token, local_vec)

async def verify_face(stored_face_token: Optional[str], stored_vec_json: Optional[list], image_bytes: bytes) -> Tuple[bool, float]:
    """
    Verify against Face++ (if configured) and/or local cosine similarity as fallback.
    Returns (access_granted, confidence) where confidence is percent [0..100].
    """
    # Try Face++ if both tokens exist
    if _facepp_available() and stored_face_token:
        new_token = await _facepp_detect_face_token(image_bytes)
        if new_token:
            ok, conf = await _facepp_compare(stored_face_token, new_token)
            if ok:
                return True, conf

    # Fallback: local vector similarity
    if stored_vec_json:
        try:
            stored_vec = np.array(stored_vec_json, dtype=np.float32)
        except Exception:
            stored_vec = None
        new_vec = _local_face_vector(image_bytes)
        if stored_vec is not None and new_vec is not None:
            ok, conf_percent = _local_verify(stored_vec, new_vec)
            if ok:
                return True, conf_percent

    return False, 0.0