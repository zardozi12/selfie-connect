# app/services/cloudinary_storage.py
import cloudinary
import cloudinary.uploader
import cloudinary.api
from io import BytesIO
import os
from typing import Optional
import requests


# Configure Cloudinary with environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


class CloudinaryStorage:
    """Cloudinary-based storage for production deployment"""
    
    def save(self, user_id: str, filename: str, data: bytes) -> str:
        """Save encrypted image data to Cloudinary"""
        try:
            # Create unique public_id for the image
            public_id = f"photovault/{user_id}/{filename}"
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                BytesIO(data),
                public_id=public_id,
                resource_type="auto",  # auto-detect file type
                overwrite=True,
                folder=f"photovault/{user_id}",
                access_mode="token"  # Requires signed URL for access
            )
            
            # Return the secure URL as storage key
            return result["secure_url"]
            
        except Exception as e:
            # Fallback to local storage if Cloudinary fails
            from app.services.storage import storage as local_storage
            return local_storage.save(user_id, filename, data)
    
    def read(self, storage_key: str) -> bytes:
        """Read encrypted image data from Cloudinary URL"""
        try:
            # storage_key is the Cloudinary secure URL
            response = requests.get(storage_key, timeout=30)
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            # Try fallback to local storage
            try:
                from app.services.storage import storage as local_storage
                return local_storage.read(storage_key)
            except Exception:
                raise Exception(f"Failed to read from Cloudinary: {e}")
    
    def exists(self, storage_key: str) -> bool:
        """Check if image exists at Cloudinary URL"""
        try:
            # For Cloudinary URLs, do a HEAD request
            if storage_key.startswith("https://res.cloudinary.com"):
                response = requests.head(storage_key, timeout=10)
                return response.status_code == 200
            else:
                # Fallback to local storage check
                from app.services.storage import storage as local_storage
                return local_storage.exists(storage_key)
                
        except Exception:
            return False
    
    def delete(self, storage_key: str) -> bool:
        """Delete image from Cloudinary"""
        try:
            # Extract public_id from secure URL
            if "photovault/" in storage_key:
                # Parse public_id from URL
                # URL format: https://res.cloudinary.com/cloud/image/upload/v123/photovault/user/file
                parts = storage_key.split("/")
                if "photovault" in parts:
                    idx = parts.index("photovault")
                    public_id = "/".join(parts[idx:]).split(".")[0]  # Remove extension
                    
                    result = cloudinary.uploader.destroy(public_id)
                    return result.get("result") == "ok"
            
            return False
            
        except Exception:
            return False


class HybridCloudStorage:
    """
    Hybrid storage for production:
    - Cloudinary for production
    - Local storage for development/fallback
    """
    
    def __init__(self):
        # Check if Cloudinary is configured
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        
        if cloud_name and api_key and os.getenv("APP_ENV") == "prod":
            self.storage = CloudinaryStorage()
            self.storage_type = "cloudinary"
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
        return False


# Export the hybrid storage
storage = HybridCloudStorage()
