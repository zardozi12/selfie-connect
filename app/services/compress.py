import io
from PIL import Image

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