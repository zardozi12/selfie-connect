from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime


class ImageOut(BaseModel):
    id: UUID
    original_filename: str | None = None
    width: int | None = None
    height: int | None = None
    gps_lat: float | None = None
    gps_lng: float | None = None
    location_text: str | None = None
    created_at: datetime | None = None


class AlbumGroup(BaseModel):
    key: str
    count: int
    image_ids: List[UUID]


class PersonClusterOut(BaseModel):
    id: UUID
    label: str
    faces: int


class AlbumOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    album_type: str
    location_text: str | None = None
    gps_lat: float | None = None
    gps_lng: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_auto_generated: bool
    cover_image_id: UUID | None = None
    image_count: int = 0
    created_at: datetime


class AlbumImageOut(BaseModel):
    id: UUID
    album_id: UUID
    image_id: UUID
    added_at: datetime


class FaceOut(BaseModel):
    id: UUID
    image_id: UUID
    x: float
    y: float
    w: float
    h: float
    cluster_id: UUID | None = None