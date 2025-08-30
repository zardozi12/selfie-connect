import uvicorn
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.config import settings
from app.db import init_db, close_db
from app.routers import api


app = FastAPI(title="PhotoVault API", version="0.1.0")


app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    await init_db()


@app.on_event("shutdown")
async def _shutdown():
    await close_db()


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


app.include_router(api)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8999, reload=True)