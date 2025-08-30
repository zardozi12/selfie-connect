# app/services/deta_storage.py
from deta import Deta
from typing import Optional
import os
from app.config import settings

# Deta auto-reads credentials from env in Space; no args needed
try:
    _deta = Deta()
    _drive = _deta.Drive("photovault")  # bucket name
    DETA_AVAILABLE = True
except Exception:
    # Fallback for local development
    _deta = None
    _drive = None
    DETA_AVAILABLE = False


class DetaDriveStorage:
    """Deta Drive storage for cloud deployment"""
    
    def save(self, user_id: str, filename: str, data: bytes) -> str:
        """Save encrypted image data to Deta Drive"""
        if not DETA_AVAILABLE or not _drive:
            raise Exception("Deta Drive not available")
        
        key = f"{user_id}/{filename}"
        _drive.put(key, data=data)   # store bytes
        return key

    def read(self, key: str) -> bytes:
        """Read encrypted image data from Deta Drive"""
        if not DETA_AVAILABLE or not _drive:
            raise Exception("Deta Drive not available")
        
        f = _drive.get(key)
        return f.read() if f else b""

    def exists(self, key: str) -> bool:
        """Check if file exists in Deta Drive"""
        if not DETA_AVAILABLE or not _drive:
            return False
        
        try:
            f = _drive.get(key)
            return f is not None
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete file from Deta Drive"""
        if not DETA_AVAILABLE or not _drive:
            return False
        
        try:
            _drive.delete(key)
            return True
        except Exception:
            return False


class HybridCloudStorage:
    """
    Hybrid storage that uses:
    1. Deta Drive for cloud deployment (Deta Space)
    2. Local storage for development
    """
    
    def __init__(self):
        if DETA_AVAILABLE and settings.APP_ENV == "prod":
            self.storage = DetaDriveStorage()
            self.storage_type = "deta_drive"
        else:
            # Use local storage for development
            from app.services.storage import storage as local_storage
            self.storage = local_storage
            self.storage_type = "local"
    
    def save(self, user_id: str, filename: str, data: bytes) -> str:
        """Save to appropriate storage backend"""
        return self.storage.save(user_id, filename, data)
    
    def read(self, key: str) -> bytes:
        """Read from appropriate storage backend"""
        return self.storage.read(key)
    
    def exists(self, key: str) -> bool:
        """Check if exists in appropriate storage backend"""
        return self.storage.exists(key)
    
    def delete(self, key: str) -> bool:
        """Delete from appropriate storage backend"""
        if hasattr(self.storage, 'delete'):
            return self.storage.delete(key)
        else:
            # Fallback for local storage
            try:
                from pathlib import Path
                from app.config import settings
                BASE = Path(settings.STORAGE_DIR)
                path = BASE / key
                if path.exists():
                    path.unlink()
                    return True
            except Exception:
                pass
            return False


# Export the hybrid storage
storage = HybridCloudStorage()
