import io
import cv2
import numpy as np
from typing import Tuple, List
from PIL import Image
from app.utils.exif import extract_exif
from app.utils.guard import in01

# Optional: if using face_recognition (HOG/CNN)
try:
    import face_recognition
    _HAS_FACE_REC = True
except Exception:
    _HAS_FACE_REC = False

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
    denoised = cv2.fastNlMeansDenoisingColored(rgb, None, 3, 3, 7, 21)
    gamma = 1.2
    invGamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** invGamma * 255 for i in np.arange(0, 256)]).astype("uint8")
    out = cv2.LUT(denoised, table)
    return out

def detect_faces_embeddings(rgb: np.ndarray) -> List[np.ndarray]:
    if not _HAS_FACE_REC:
        return []
    boxes = face_recognition.face_locations(rgb, model="hog")
    if not boxes:
        return []
    enc = face_recognition.face_encodings(rgb, boxes, num_jitters=1, model="small")
    return [np.array(e, dtype=np.float32) for e in enc]

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-9
    return float(np.dot(a, b) / denom)