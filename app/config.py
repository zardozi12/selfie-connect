import os
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from pydantic import AnyHttpUrl, field_validator
from typing import List, Union, Tuple

# Robust .env loader: try multiple encodings without modifying the file
try:
    from dotenv import dotenv_values
    env_path = ".env"
    if os.path.exists(env_path):
        for enc in ("utf-8", "utf-8-sig", "utf-16", "cp1252"):
            try:
                values = dotenv_values(env_path, encoding=enc)
                if values:
                    for k, v in values.items():
                        if k and v is not None and k not in os.environ:
                            os.environ[k] = str(v)
                    break
            except Exception:
                continue
except Exception:
    pass


class Settings(BaseSettings):
    DATABASE_URL: str
    APP_ENV: str = "dev"

    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRES_MIN: int = 1440  # 24 hours for development
    CORS_ORIGINS: Union[str, List[str]] = ""

    STORAGE_DRIVER: str = "local"
    STORAGE_DIR: str = "./storage"

    MASTER_KEY: str

    EMBEDDINGS_PROVIDER: str = "phash"
    CLIP_MODEL: str = "clip-ViT-B-32"

    ENABLE_GEOCODER: bool = False  # Disabled for free deployment
    GEOCODER_EMAIL: str | None = None

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v == "":
                return []
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Do not let pydantic auto-load .env; rely on env and our manual loader
    model_config = SettingsConfigDict(extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Exclude dotenv_settings to prevent UnicodeDecodeError
        return (
            init_settings,  # kwargs passed to Settings()
            env_settings,   # os.environ (includes our manual loader)
            # file_secret_settings could be added back if needed
        )


settings = Settings()