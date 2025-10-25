# SecurityHeadersMiddleware, ErrorEnvelopeMiddleware
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        # Add HSTS in production
        if (settings.APP_ENV or "").strip().lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        
        # Allow Swagger UI/ReDoc to load assets from jsDelivr
        if "/docs" in str(request.url) or "/redoc" in str(request.url):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data: https:; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "script-src-elem 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src-elem 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "font-src 'self' data:; "
                "frame-src 'self'; "
                "connect-src 'self';"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data: blob: https:; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' https://yourdomain.com http://localhost:3000; "
                "object-src 'none'; "
                "frame-ancestors 'none'; "
                "base-uri 'self';"
            )
        return response

class ErrorEnvelopeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        start = time.time()
        request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={"error": str(exc), "path": str(request.url)}
            )
        response.headers.setdefault("x-request-id", request_id)
        response.headers.setdefault("x-content-type-options", "nosniff")
        response.headers.setdefault("x-frame-options", "DENY")
        response.headers.setdefault("referrer-policy", "same-origin")
        response.headers.setdefault("cross-origin-opener-policy", "same-origin")
        response.headers["server-timing"] = f"total;dur={(time.time() - start) * 1000:.2f}"
        return response