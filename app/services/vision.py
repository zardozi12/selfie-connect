import io
import numpy as np
import cv2
from PIL import Image
from typing import List, Tuple
from app.utils.exif import extract_exif


# Minimal face detection using OpenCV Haar cascades (offline & free).
# For better results swap with mediapipe or a DNN model.
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
        faces.append((x/W, y/H, w0/W, h0/H))

    return Processed(exif, lat, lng, W, H, faces)


async def to_rgb_np(content_bytes: bytes) -> np.ndarray:
    pil = Image.open(io.BytesIO(content_bytes)).convert("RGB")
    return np.array(pil)