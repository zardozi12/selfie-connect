"""
Share management service for PhotoVault
Handles creation, validation, and tracking of public share links
"""

import hashlib
import uuid
import datetime as dt
from jose import jwt
from app.config import settings
from tortoise import Tortoise


def _hash_token(tok: str) -> str:
    """Hash token for secure storage"""
    return hashlib.sha256(tok.encode()).hexdigest()


def create_share_jwt(user_id: str, album_id: str, hours: int) -> str:
    """
    Create a JWT token for sharing an album.
    
    Args:
        user_id: ID of the user who owns the album
        album_id: ID of the album to share
        hours: Hours until expiration
    
    Returns:
        JWT token string
    """
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(hours=hours)
    
    payload = {
        "typ": "share",
        "sub": user_id,
        "alb": album_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp())
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_share_jwt(token: str) -> dict:
    """
    Decode and validate a share JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


async def record_share(
    album_id: str, 
    created_by: str, 
    token: str, 
    hours: int, 
    max_views: int | None = None
) -> str:
    """
    Record a share link in the database.
    
    Args:
        album_id: ID of the album being shared
        created_by: ID of the user creating the share
        token: JWT token for the share
        hours: Hours until expiration
        max_views: Maximum number of views (None for unlimited)
    
    Returns:
        Share ID
    """
    token_hash = _hash_token(token)
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=hours)
    share_id = str(uuid.uuid4())
    
    await Tortoise.get_connection("default").execute_query(
        """
        INSERT INTO public_shares (id, album_id, created_by, token_hash, scope, expires_at, max_views, view_count, revoked)
        VALUES ($1, $2, $3, $4, 'view', $5, $6, 0, false)
        """,
        [share_id, album_id, created_by, token_hash, expires_at, max_views],
    )
    
    return share_id


async def validate_share(token: str) -> dict | None:
    """
    Validate a share token and return share information.
    
    Args:
        token: JWT token string
    
    Returns:
        Dictionary with JWT payload and share info, or None if invalid
    """
    try:
        # Decode JWT
        data = decode_share_jwt(token)
    except Exception:
        return None
    
    # Check database record
    token_hash = _hash_token(token)
    rows = await Tortoise.get_connection("default").execute_query_dict(
        """
        SELECT * FROM public_shares
        WHERE token_hash = $1 AND revoked = false AND NOW() < expires_at
        """,
        [token_hash],
    )
    
    if not rows:
        return None
    
    share = rows[0]
    
    # Check view limit
    max_views = share.get("max_views")
    view_count = share.get("view_count", 0)
    if max_views is not None and view_count >= max_views:
        return None
    
    return {"jwt": data, "share": share}


async def increment_share_view(token: str):
    """
    Increment the view count for a share.
    
    Args:
        token: JWT token string
    """
    token_hash = _hash_token(token)
    await Tortoise.get_connection("default").execute_query(
        "UPDATE public_shares SET view_count = view_count + 1 WHERE token_hash = $1",
        [token_hash],
    )


async def revoke_share(share_id: str):
    """
    Revoke a share link.
    
    Args:
        share_id: ID of the share to revoke
    """
    await Tortoise.get_connection("default").execute_query(
        "UPDATE public_shares SET revoked = true WHERE id = $1",
        [share_id],
    )


async def get_share_stats(share_id: str) -> dict | None:
    """
    Get statistics for a share link.
    
    Args:
        share_id: ID of the share
    
    Returns:
        Dictionary with share statistics
    """
    rows = await Tortoise.get_connection("default").execute_query_dict(
        """
        SELECT view_count, max_views, expires_at, revoked, created_at
        FROM public_shares
        WHERE id = $1
        """,
        [share_id],
    )
    
    if not rows:
        return None
    
    share = rows[0]
    return {
        "view_count": share["view_count"],
        "max_views": share["max_views"],
        "expires_at": share["expires_at"],
        "revoked": share["revoked"],
        "created_at": share["created_at"],
        "is_expired": dt.datetime.now(dt.timezone.utc) > share["expires_at"]
    }
