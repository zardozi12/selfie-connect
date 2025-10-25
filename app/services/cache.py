import os
import json
from typing import Any, Optional

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    redis = None  # type: ignore


_REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
_client = None
if redis is not None:
    try:
        _client = redis.from_url(_REDIS_URL)
    except Exception:
        _client = None


async def cache_get_json(key: str) -> Optional[Any]:
    if _client is None:
        return None
    try:
        raw = _client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set_json(key: str, value: Any, ttl: int = 60) -> None:
    if _client is None:
        return
    try:
        _client.setex(key, ttl, json.dumps(value))
    except Exception:
        return


async def cache_invalidate_prefix(prefix: str) -> int:
    if _client is None:
        return 0
    count = 0
    try:
        for k in _client.scan_iter(f"{prefix}*"):
            _client.delete(k)
            count += 1
    except Exception:
        return 0
    return count


