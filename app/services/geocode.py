from app.config import settings
from geopy.geocoders import Nominatim


_geocoder = None
if settings.ENABLE_GEOCODER and settings.GEOCODER_EMAIL:
    _geocoder = Nominatim(user_agent=f"photovault/1 ({settings.GEOCODER_EMAIL})")


async def reverse(lat: float, lng: float) -> str | None:
    if not _geocoder:
        return None
    
    try:
        loc = _geocoder.reverse((lat, lng), language="en")
        if loc and loc.raw and "address" in loc.raw:
            a = loc.raw["address"]
            # city or town or village, plus country short
            city = a.get("city") or a.get("town") or a.get("village") or a.get("state")
            cc = a.get("country_code", "").upper()
            if city and cc:
                return f"{city}, {cc}"
            return loc.address
    except Exception:
        return None
    
    return None