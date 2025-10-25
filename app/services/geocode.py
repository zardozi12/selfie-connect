# Add simple TTL cache to reduce external lookups
from app.config import settings
from geopy.geocoders import Nominatim
import time

_geocoder = None
if settings.ENABLE_GEOCODER and settings.GEOCODER_EMAIL:
    _geocoder = Nominatim(user_agent=f"photovault/1 ({settings.GEOCODER_EMAIL})")


_CACHE: dict[tuple[float, float], tuple[float, str | None]] = {}
_TTL_SECONDS = 24 * 60 * 60

async def reverse(lat: float, lng: float) -> str | None:
    if not _geocoder:
        return None

    key = (round(lat, 6), round(lng, 6))
    now = time.time()
    cached = _CACHE.get(key)
    if cached and (now - cached[0]) < _TTL_SECONDS:
        return cached[1]
    
    try:
        loc = _geocoder.reverse((lat, lng), language="en")
        if loc and loc.raw and "address" in loc.raw:
            a = loc.raw["address"]
            city = a.get("city") or a.get("town") or a.get("village") or a.get("state")
            cc = a.get("country_code", "").upper()
            result = f"{city}, {cc}" if city and cc else loc.address
            _CACHE[key] = (now, result)
            return result
    except Exception:
        _CACHE[key] = (now, None)
        return None
    
    _CACHE[key] = (now, None)
    return None