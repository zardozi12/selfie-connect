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

    def read(self, key: str) -> bytes:
        path = BASE / key
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return (BASE / key).exists()


storage = LocalStorage()