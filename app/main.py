# Top imports
import uvicorn
import os
import logging
import uuid
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import sentry_sdk
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.middleware import SecurityHeadersMiddleware
from app.config import settings
from app.db import init_db, close_db
from app.core.middleware import ErrorEnvelopeMiddleware
from app.services.observability import init_observability, instrument_fastapi
# module-level import guards for metrics
try:
    from app.services.metrics import metrics_middleware, metrics_endpoint
except Exception:
    # Fallbacks if prometheus_client or metrics module isn’t available
    from fastapi.responses import PlainTextResponse
    def metrics_middleware(app):
        return None
    async def metrics_endpoint():
        return PlainTextResponse("metrics disabled", media_type="text/plain")

# CSRF protection import guard
try:
    from fastapi_csrf_protect import CsrfProtect
    from fastapi_csrf_protect.exceptions import CsrfProtectError
    csrf_enabled = True
except Exception:
    csrf_enabled = False
    CsrfProtect = None
    CsrfProtectError = None

# Initialize Sentry if DSN is provided
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)

# Modern lifespan context manager
from contextlib import asynccontextmanager

# Method: lifespan()
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("Starting PhotoVault application...")
    # Secret guard for production deployments
    env = (settings.APP_ENV or "").strip().lower()
    if env == "production":
        for k in ("JWT_SECRET", "CSRF_SECRET", "MASTER_KEY"):
            v = getattr(settings, k, "")
            if not v or v in ("", "dev", "CHANGE_ME") or len(v) < 32:
                raise RuntimeError(f"Insecure {k}; set a real secret in production")
    init_observability("photovault")
    try:
        await init_db()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logging.info("Shutting down PhotoVault application...")
    try:
        await close_db()
        logging.info("Database connections closed")
    except Exception as e:
        logging.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="PhotoVault API",
    description="API for PhotoVault - A secure photo storage and management system with AI-powered features",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# CSRF Protection - Simplified for development
from app.config import settings, CsrfSettings

if csrf_enabled:
    csrf_protect = CsrfProtect()

    @CsrfProtect.load_config
    def csrf_config():
        """Load CSRF secret from settings"""
        return CsrfSettings(secret_key=settings.CSRF_SECRET)

    @app.exception_handler(CsrfProtectError)
    async def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message}
        )

# Rate limiting
app.state.limiter = Limiter(key_func=get_remote_address)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def _log_registered_routes(app):
    try:
        logging.info("Registered routes count: %s", len(app.routes))
        for r in app.routes:
            logging.info("Route %s methods=%s name=%s", getattr(r, "path", ""), getattr(r, "methods", ""), getattr(r, "name", ""))
    except Exception as e:
        logging.error("Failed to log registered routes: %s", e)

# Include routers
try:
    from app.routers import router
    app.include_router(router)
    logging.info("All routers loaded successfully")
    _log_registered_routes(app)
except Exception as e:
    logging.error(f"Failed to import routers: {e}")
    from fastapi import APIRouter
    minimal_router = APIRouter()
    @minimal_router.get("/")
    async def root():
        return {"message": "PhotoVault API - Development Mode"}
    @minimal_router.get("/health")
    async def health():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    app.include_router(minimal_router)

# Middleware setup
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(ErrorEnvelopeMiddleware)

# CORS configuration
_default_cors = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
allow_origins = settings.CORS_ORIGINS or _default_cors

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# After middleware setup
app.add_middleware(SecurityHeadersMiddleware)

# Enable Prometheus metrics if METRICS_ENABLED=1
metrics_middleware(app)

# Instrument with OpenTelemetry
instrument_fastapi(app)

# Correlation ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
    request.state.rid = rid
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    return response

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    try:
        openapi_schema = get_openapi(
            title="PhotoVault API",
            version="1.0.0",
            description="A secure, AI-powered photo storage and management system",
            routes=app.routes,
        )
    except Exception as e:
        # Log full exception and provide a minimal fallback to avoid 500s
        logging.exception("Failed to generate OpenAPI schema: %s", e)
        openapi_schema = {
            "openapi": "3.0.3",
            "info": {"title": "PhotoVault API", "version": "1.0.0"},
            "paths": {},
            "components": {},
        }
    # Ensure components/securitySchemes exist before assignment
    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Replace JSON /metrics with Prometheus metrics endpoint
@app.get("/metrics")
async def prometheus_metrics():
    return await metrics_endpoint()

# Universal health endpoint (always present)
@app.get("/health")
async def health():
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}