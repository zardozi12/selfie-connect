import os
import base64
from typing import Optional
from app.config import settings
import aiohttp
import json


class CloudinaryStorage:
    """Free cloud storage using Cloudinary's free tier"""
    
    def __init__(self):
        # Cloudinary free tier credentials (these would be in .env in production)
        self.cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "demo")
        self.api_key = os.getenv("CLOUDINARY_API_KEY", "demo")
        self.api_secret = os.getenv("CLOUDINARY_API_SECRET", "demo")
        self.base_url = f"https://api.cloudinary.com/v1_1/{self.cloud_name}"
    
    async def save(self, user_id: str, filename: str, data: bytes) -> str:
        """Save encrypted image data to Cloudinary"""
        try:
            # Encode data as base64
            encoded_data = base64.b64encode(data).decode('utf-8')
            
            # Create unique public_id for the image
            public_id = f"photovault/{user_id}/{filename}"
            
            # Prepare upload data
            upload_data = {
                'file': f'data:application/octet-stream;base64,{encoded_data}',
                'public_id': public_id,
                'resource_type': 'auto',
                'folder': f'photovault/{user_id}',
                'access_mode': 'authenticated'  # Requires authentication to access
            }
            
            # Upload to Cloudinary
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/image/upload",
                    data=upload_data,
                    auth=aiohttp.BasicAuth(self.api_key, self.api_secret)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['public_id']  # Return the public_id as storage key
                    else:
                        raise Exception(f"Cloudinary upload failed: {response.status}")
        
        except Exception as e:
            # Fallback to local storage if cloud storage fails
            from app.services.storage import storage
            return storage.save(user_id, filename, data)
    
    async def read(self, storage_key: str) -> bytes:
        """Read encrypted image data from Cloudinary"""
        try:
            # Download from Cloudinary
            download_url = f"https://res.cloudinary.com/{self.cloud_name}/image/upload/{storage_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise Exception(f"Cloudinary download failed: {response.status}")
        
        except Exception as e:
            # Fallback to local storage if cloud storage fails
            from app.services.storage import storage
            return storage.read(storage_key)
    
    async def delete(self, storage_key: str) -> bool:
        """Delete image from Cloudinary"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/image/destroy",
                    data={'public_id': storage_key},
                    auth=aiohttp.BasicAuth(self.api_key, self.api_secret)
                ) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def exists(self, storage_key: str) -> bool:
        """Check if image exists in Cloudinary"""
        try:
            download_url = f"https://res.cloudinary.com/{self.cloud_name}/image/upload/{storage_key}"
            async with aiohttp.ClientSession() as session:
                async with session.head(download_url) as response:
                    return response.status == 200
        except Exception:
            return False


# Create a hybrid storage that tries cloud first, falls back to local
class HybridStorage:
    """Hybrid storage: tries cloud first, falls back to local storage"""
    
    def __init__(self):
        self.cloud_storage = CloudinaryStorage()
        from app.services.storage import storage
        self.local_storage = storage
    
    async def save(self, user_id: str, filename: str, data: bytes) -> str:
        """Save to cloud storage, fallback to local"""
        try:
            return await self.cloud_storage.save(user_id, filename, data)
        except Exception:
            # Fallback to local storage
            return self.local_storage.save(user_id, filename, data)
    
    async def read(self, storage_key: str) -> bytes:
        """Read from cloud storage, fallback to local"""
        try:
            return await self.cloud_storage.read(storage_key)
        except Exception:
            # Fallback to local storage
            return self.local_storage.read(storage_key)
    
    async def delete(self, storage_key: str) -> bool:
        """Delete from cloud storage, fallback to local"""
        try:
            return await self.cloud_storage.delete(storage_key)
        except Exception:
            # Try local storage
            try:
                import os
                from pathlib import Path
                from app.config import settings
                BASE = Path(settings.STORAGE_DIR)
                path = BASE / storage_key
                if path.exists():
                    path.unlink()
                    return True
            except Exception:
                pass
            return False
    
    async def exists(self, storage_key: str) -> bool:
        """Check if exists in cloud storage, fallback to local"""
        try:
            return await self.cloud_storage.exists(storage_key)
        except Exception:
            # Fallback to local storage
            return self.local_storage.exists(storage_key)


# Import the new Deta-compatible storage
try:
    from app.services.deta_storage import storage
except ImportError:
    # Fallback to original hybrid storage if Deta not available
    storage = HybridStorage()
