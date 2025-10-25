from PIL import Image as PILImage, ExifTags
from typing import Tuple, Dict, Any



def extract_exif(path_or_bytes) -> tuple[dict | None, float | None, float | None, int | None, int | None]:
    try:
        if isinstance(path_or_bytes, (bytes, bytearray)):
            from io import BytesIO
            im = PILImage.open(BytesIO(path_or_bytes))
        else:
            im = PILImage.open(path_or_bytes)
        
        width, height = im.size
        exif = im._getexif() or {}
        exif_readable: Dict[str, Any] = {}
        
        for k, v in exif.items():
            tag = ExifTags.TAGS.get(k, str(k))
            exif_readable[tag] = v
        
        gps = exif_readable.get("GPSInfo")
        lat = lng = None
        
        if gps:
            def _convert(ref, coord):
                d = coord[0][0] / coord[0][1]
                m = coord[1][0] / coord[1][1]
                s = coord[2][0] / coord[2][1]
                sign = 1 if ref in ["N", "E"] else -1
                return sign * (d + m/60 + s/3600)
            
            lat = _convert(gps.get(1), gps.get(2)) if gps.get(1) and gps.get(2) else None
            lng = _convert(gps.get(3), gps.get(4)) if gps.get(3) and gps.get(4) else None
        
        return exif_readable, lat, lng, width, height
    except Exception:
        return None, None, None, None, None