from tortoise import Tortoise
from app.config import settings
import asyncio, logging

MODELS = [
    "app.models.user",
    "app.models.image",
    "app.models.face",
    "app.models.album",
    "aerich.models",   # <-- REQUIRED for Aerich
]

_logger = logging.getLogger("db")

def _dsn():
    d = settings.DATABASE_URL
    # Handle Neon PostgreSQL URLs with SSL parameters
    if "neon.tech" in d:
        # Remove sslmode and channel_binding for Tortoise ORM compatibility
        d = d.split("?")[0]  # Remove query parameters
    return d.replace("postgresql://", "postgres://", 1) if d.startswith("postgresql://") else d

async def init_db(max_retries: int = 10, delay_seconds: float = 1.5) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            await Tortoise.init(db_url=_dsn(), modules={"models": MODELS})
            await Tortoise.generate_schemas()
            _logger.info("Database initialized successfully")
            return
        except Exception as exc:
            if attempt == max_retries:
                _logger.warning(
                    "Database not available after %s attempts; starting app without DB (errors will occur on DB access). Error: %s",
                    attempt, exc,
                )
                return
            _logger.info("DB init failed (attempt %s/%s): %s; retrying in %.1fs",
                         attempt, max_retries, exc, delay_seconds)
            await asyncio.sleep(delay_seconds)

async def close_db():
    try:
        await Tortoise.close_connections()
    except Exception:
        pass

# ---------- Aerich config (DSN-driven; works for Postgres or SQLite) ----------
TORTOISE_ORM = {
    "connections": {"default": _dsn()},   # <- use your .env DSN
    "apps": {
        "models": {
            "models": MODELS,
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "UTC",
}
