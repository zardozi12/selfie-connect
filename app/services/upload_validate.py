from fastapi import HTTPException, UploadFile

async def validate_and_process_upload(file: UploadFile):
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "File too large")

    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type {file.content_type}")

    # Signature check
    if not (content.startswith(b'\xff\xd8') or content.startswith(b'\x89PNG')):
        raise HTTPException(400, "File signature mismatch")

    file.file.seek(0)
    return content