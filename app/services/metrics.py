"""
Prometheus metrics service for PhotoVault
Provides monitoring and observability for the application
"""

import time
import os
from fastapi import Request
from fastapi.responses import Response

# Guarded imports with fallbacks
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    _PROM_AVAILABLE = True
except Exception:
    _PROM_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain"
    def generate_latest():
        return b""
    class _NoopMetric:
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
    Counter = Histogram = _NoopMetric

# Metrics definitions - with duplicate check
try:
    REQUESTS_TOTAL = Counter(
        "photovault_http_requests_total", 
        "Total HTTP requests", 
        ["method", "path", "status"]
    )
except Exception:
    try:
        from prometheus_client import REGISTRY
        REQUESTS_TOTAL = REGISTRY._names_to_collectors.get("photovault_http_requests_total") or Counter()
    except Exception:
        REQUESTS_TOTAL = Counter()

try:
    REQUEST_DURATION = Histogram(
        "photovault_http_request_seconds", 
        "Request duration in seconds", 
        ["method", "path"]
    )
except Exception:
    try:
        from prometheus_client import REGISTRY
        REQUEST_DURATION = REGISTRY._names_to_collectors.get("photovault_http_request_seconds") or Histogram()
    except Exception:
        REQUEST_DURATION = Histogram()

try:
    UPLOADS_TOTAL = Counter(
        "photovault_uploads_total",
        "Total image uploads",
        ["status"]
    )
except Exception:
    try:
        from prometheus_client import REGISTRY
        UPLOADS_TOTAL = REGISTRY._names_to_collectors.get("photovault_uploads_total") or Counter()
    except Exception:
        UPLOADS_TOTAL = Counter()

try:
    DUPLICATES_DETECTED = Counter(
        "photovault_duplicates_detected_total",
        "Total duplicate images detected"
    )
except Exception:
    try:
        from prometheus_client import REGISTRY
        DUPLICATES_DETECTED = REGISTRY._names_to_collectors.get("photovault_duplicates_detected_total") or Counter()
    except Exception:
        DUPLICATES_DETECTED = Counter()

try:
    SHARES_CREATED = Counter(
        "photovault_shares_created_total",
        "Total share links created"
    )
except Exception:
    try:
        from prometheus_client import REGISTRY
        SHARES_CREATED = REGISTRY._names_to_collectors.get("photovault_shares_created_total") or Counter()
    except Exception:
        SHARES_CREATED = Counter()

try:
    SHARES_VIEWED = Counter(
        "photovault_shares_viewed_total", 
        "Total share link views"
    )
except Exception:
    try:
        from prometheus_client import REGISTRY
        SHARES_VIEWED = REGISTRY._names_to_collectors.get("photovault_shares_viewed_total") or Counter()
    except Exception:
        SHARES_VIEWED = Counter()

# Check if metrics are enabled and available
ENABLED = os.getenv("METRICS_ENABLED") == "1" and _PROM_AVAILABLE

async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    if not ENABLED:
        return Response(b"metrics disabled", media_type="text/plain")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

def metrics_middleware(app):
    """Add metrics middleware to FastAPI app"""
    if not ENABLED:
        return
    
    @app.middleware("http")
    async def _metrics(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        
        # Record metrics
        path = request.url.path
        REQUESTS_TOTAL.labels(
            method=request.method, 
            path=path, 
            status=str(response.status_code)
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method, 
            path=path
        ).observe(time.time() - start)
        
        return response

def record_upload(status: str):
    """Record image upload metric"""
    if ENABLED:
        UPLOADS_TOTAL.labels(status=status).inc()

def record_duplicate():
    """Record duplicate detection metric"""
    if ENABLED:
        DUPLICATES_DETECTED.inc()

def record_share_created():
    """Record share creation metric"""
    if ENABLED:
        SHARES_CREATED.inc()

def record_share_viewed():
    """Record share view metric"""
    if ENABLED:
        SHARES_VIEWED.inc()
