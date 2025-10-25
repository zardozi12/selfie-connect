import os
from pathlib import Path
from typing import BinaryIO
from slugify import slugify
from app.config import settings


BASE = Path(settings.STORAGE_DIR)
BASE.mkdir(parents=True, exist_ok=True)


class LocalStorage:
    def save(self, user_id: str, filename: str, data: bytes) -> str:
        folder = BASE / slugify(user_id)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / filename
        with open(path, "wb") as f:
            f.write(data)
        return str(path.relative_to(BASE))

    def save_in_folder(self, user_id: str, folder: str, filename: str, data: bytes) -> str:
        user_dir = BASE / slugify(user_id)
        dest_dir = user_dir / slugify(folder)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / filename
        with open(path, "wb") as f:
            f.write(data)
        return str(path.relative_to(BASE))

    def move_to_folder(self, key: str, folder: str) -> str:
        # key is a relative path like "<userSlug>/.../filename"
        src = BASE / key
        if not src.exists():
            raise FileNotFoundError(f"Source not found: {src}")

        parts = Path(key).parts
        user_slug = parts[0] if parts else "unknown"
        dest_dir = BASE / user_slug / slugify(folder)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        src.rename(dest)
        return str(dest.relative_to(BASE))

    def read(self, key: str) -> bytes:
        path = BASE / key
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return (BASE / key).exists()


storage = LocalStorage()