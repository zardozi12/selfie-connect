# # from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
# # import os

# # def create_engine() -> AsyncEngine:
# #     """Create and configure the async database engine"""
# #     db_url = os.getenv("DATABASE_URL")
# #     if not db_url:
# #         raise ValueError("DATABASE_URL environment variable not set")

# #     # Ensure SQLite URL has async prefix
# #     if db_url.startswith("sqlite://"):
# #         db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

# #     return create_async_engine(
# #         db_url,
# #         connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
# #         pool_size=int(os.getenv("DB_POOL_SIZE", 5)),
# #         max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 10)),
# #         pool_pre_ping=True,
# #         pool_recycle=3600,
# #         pool_timeout=30,
# #         echo=False
# #     )

# # engine: AsyncEngine = create_engine()





# # app/core/db_engine.py
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
# from sqlalchemy import text
# import os

# def create_engine() -> AsyncEngine:
#     """Create and configure the async database engine"""
#     db_url = os.getenv("DATABASE_URL")
#     if not db_url:
#         raise ValueError("DATABASE_URL environment variable not set")

#     # Ensure SQLite URL has async prefix
#     if db_url.startswith("sqlite://"):
#         db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

#     # For SQLite, SQLAlchemy ignores some pool args; safe to keep for non-SQLite
#     return create_async_engine(
#         db_url,
#         connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
#         pool_size=int(os.getenv("DB_POOL_SIZE", 5)),
#         max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 10)),
#         pool_pre_ping=True,
#         pool_recycle=3600,
#         pool_timeout=30,
#         echo=False,
#     )

# engine: AsyncEngine = create_engine()

# # ---------- NEW: health check used by /ops/db-health ----------
# async def db_healthcheck() -> bool:
#     """Simple DB health probe."""
#     try:
#         async with engine.begin() as conn:
#             await conn.execute(text("SELECT 1"))
#         return True
#     except Exception:
#         return False




# app/core/db_engine.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text

def _to_sqla_async_url(url: str) -> str:
    """
    Convert a Tortoise-style DATABASE_URL into a SQLAlchemy async URL.
    Examples:
      sqlite://db.sqlite3           -> sqlite+aiosqlite:///db.sqlite3
      sqlite://./photovault.db      -> sqlite+aiosqlite:///photovault.db
      postgres://user:pass@host/db  -> postgresql+asyncpg://user:pass@host/db
      postgresql://...              -> postgresql+asyncpg://...
    """
    url = url.strip().strip('"').strip("'")
    if url.startswith("sqlite+aiosqlite://"):
        return url  # already OK for SQLAlchemy
    if url.startswith("sqlite://"):
        # Fix SQLite URL format for SQLAlchemy
        if url.startswith("sqlite://./"):
            # Convert sqlite://./file.db to sqlite+aiosqlite:///file.db
            return url.replace("sqlite://./", "sqlite+aiosqlite:///", 1)
        elif url.startswith("sqlite://"):
            # Convert sqlite://file.db to sqlite+aiosqlite:///file.db
            return url.replace("sqlite://", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    raise ValueError("PostgreSQL required. Set DATABASE_URL to postgres:// or postgresql://")

def create_engine() -> AsyncEngine:
    db_url = os.getenv("DATABASE_URL", "postgres://user:password@localhost:5432/photovault")
    sqla_url = _to_sqla_async_url(db_url)
    return create_async_engine(
        sqla_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_timeout=30,
        echo=False,
    )

engine: AsyncEngine = create_engine()

async def db_healthcheck() -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
