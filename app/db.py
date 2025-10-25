import os
import asyncio
import logging
from tortoise import Tortoise
from app.config import settings

_logger = logging.getLogger("db")

MODELS = [
    "app.models.user",
    "app.models.image",
    "app.models.face",
    "app.models.album",
    "app.models.share",
    "app.models.session",
    "app.models.otp",
    "aerich.models",
]

def _tortoise_url_from_env() -> str:
    """Normalize database URL for Tortoise ORM and force SQLite for tests."""
    # During pytest, prefer a file-based SQLite DB to avoid per-connection
    # in-memory isolation issues that can hide writes across queries
    if "PYTEST_CURRENT_TEST" in os.environ:
        return "sqlite://./.test_db.sqlite3"

    # For local development, allow forcing SQLite to avoid stale remote schemas
    # Set FORCE_LOCAL_SQLITE=0 to disable
    force_sqlite = os.environ.get("FORCE_LOCAL_SQLITE", "1") == "1"
    try:
        app_env = settings.APP_ENV.strip().lower()
    except Exception:
        app_env = "dev"
    if force_sqlite and app_env != "prod":
        return "sqlite://./dev.db"

    url = settings.DATABASE_URL.strip().strip('"').strip("'")
    # Normalize to tortoise "postgres://" style
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgres://", 1)
    if not url.startswith("postgres://"):
        raise ValueError("PostgreSQL required. Set DATABASE_URL to postgres://...")
    return url

def _build_tortoise_config() -> dict:
    return {
        "connections": {"default": _tortoise_url_from_env()},
    "apps": {
        "models": {
                "models": MODELS,
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "UTC",
}

async def init_db(max_retries: int = 3, delay_seconds: float = 0.5) -> None:
    """Initialize database with retry logic in the current event loop.

    In local dev with SQLite file DBs, if schema conflicts arise (e.g., FK type
    mismatches from an older file), automatically reset the DB file once and retry.
    """
    config = _build_tortoise_config()
    reset_attempted = False
    for attempt in range(1, max_retries + 1):
        try:
            await Tortoise.init(config=config)
            await Tortoise.generate_schemas(safe=True)
            _logger.info("Database initialized successfully")
            return
        except Exception as exc:
            # If using a local SQLite file and we hit a schema error, delete file once
            conn = config.get("connections", {}).get("default", "")
            is_sqlite_file = conn.startswith("sqlite://") and not conn.endswith(":memory:")
            if is_sqlite_file and not reset_attempted:
                # Extract path after sqlite://
                db_path = conn.replace("sqlite://", "", 1)
                db_path = db_path.lstrip("/")
                try:
                    if os.path.exists(db_path):
                        os.remove(db_path)
                        reset_attempted = True
                        _logger.warning("Removed stale SQLite DB '%s' due to schema conflict: %s", db_path, exc)
                        # small delay before retry
                        await asyncio.sleep(0.1)
                        continue
                except Exception:
                    pass
            if attempt == max_retries:
                _logger.warning(
                    "Database unavailable after %s attempts. Error: %s",
                    attempt,
                    exc,
                )
                return
            _logger.info(
                "DB init failed (attempt %s/%s): %s; retrying in %.1fs",
                attempt,
                max_retries,
                exc,
                delay_seconds,
            )
            await asyncio.sleep(delay_seconds)

async def close_db() -> None:
    """Close database connections in the current event loop."""
    try:
        await Tortoise.close_connections()
    except Exception:
        pass
