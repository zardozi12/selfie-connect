from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, BaseModel
from typing import List, Union

# Load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

class CsrfSettings(BaseModel):
    secret_key: str

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgres://user:password@localhost:5432/photovault"
    # Security
    JWT_SECRET: str = "dev-jwt-secret-change-me-very-long-32-chars-minimum"
    CSRF_SECRET: str = "dev-csrf-secret-change-me-very-long-32-chars-min"
    ACCESS_TOKEN_EXPIRES_MIN: int = 1440
    MASTER_KEY: str = "dev-master-key-change-me-very-long-32-chars-min"
    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://127.0.0.1:3000"
    # ... existing code ...    # Security
    JWT_SECRET: str = "dev-jwt-secret-change-me-very-long-32-chars-minimum"
    CSRF_SECRET: str = "dev-csrf-secret-change-me-very-long-32-chars-min"
    ACCESS_TOKEN_EXPIRES_MIN: int = 1440
    MASTER_KEY: str = "dev-master-key-change-me-very-long-32-chars-min"
    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Storage
    STORAGE_DRIVER: str = "local"
    STORAGE_DIR: str = "./storage"
    
    # AI/ML
    EMBEDDINGS_PROVIDER: str = "phash"
    CLIP_MODEL: str = "clip-ViT-B-32"
    
    # Features
    ENABLE_GEOCODER: bool = True
    GEOCODER_EMAIL: str = "photovault@example.com"
    ENABLE_PGVECTOR: bool = False
    
    # Performance
    MAX_UPLOAD_SIZE: str = "50MB"
    THUMBNAIL_SIZE: int = 300
    IMAGE_QUALITY: int = 85
    
    # Security
    SESSION_TIMEOUT: int = 1440
    MAX_LOGIN_ATTEMPTS: int = 5
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v

    # Pydantic v2 config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

TORTOISE_ORM = {
    "connections": {
        "default": settings.DATABASE_URL
    },
    "apps": {
        "models": {
            "models": [
                "app.models.user",
                "app.models.image", 
                "app.models.album",
                "app.models.face",
                "app.models.share",
                "aerich.models"
            ],
            "default_connection": "default",
        }
    },
    "use_tz": True,  # Use timezone-aware datetimes
    "timezone": "UTC",
}
