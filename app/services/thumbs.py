"""
Thumbnail generation service for PhotoVault
Generates compressed JPEG thumbnails from uploaded images
"""

from io import BytesIO
from PIL import Image


def make_thumbnail(jpeg_or_png_bytes: bytes, max_side: int = 512, quality: int = 85) -> bytes:
    """
    Generate a thumbnail from image bytes.
    
    Args:
        jpeg_or_png_bytes: Raw image bytes (JPEG, PNG, etc.)
        max_side: Maximum width or height for thumbnail
        quality: JPEG quality (1-100)
    
    Returns:
        Compressed JPEG thumbnail bytes
    """
    try:
        # Open and convert to RGB
        im = Image.open(BytesIO(jpeg_or_png_bytes)).convert("RGB")
        w, h = im.size
        
        # Resize if needed
        if max(w, h) > max_side:
            im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        
        # Save as compressed JPEG
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
        
    except Exception as e:
        # If thumbnail generation fails, return None
        # The system will fall back to using the original image
        print(f"Thumbnail generation failed: {e}")
        return None
