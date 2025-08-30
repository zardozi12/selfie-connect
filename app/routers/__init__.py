from fastapi import APIRouter
from . import auth, images, albums, search, persons, dashboard


api = APIRouter()
api.include_router(auth.router)
api.include_router(images.router)
api.include_router(albums.router)
api.include_router(search.router)
api.include_router(persons.router)
api.include_router(dashboard.router)