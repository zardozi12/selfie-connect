from tortoise import fields
from app.models import BaseModel


class Image(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="images", on_delete=fields.CASCADE)

    original_filename = fields.CharField(512, null=True)
    content_type = fields.CharField(100, null=True)
    size_bytes = fields.IntField(null=True)

    width = fields.IntField(null=True)
    height = fields.IntField(null=True)

    checksum_sha256 = fields.CharField(64, index=True, null=True)

    storage_key = fields.CharField(1024)  # where encrypted blob lives (local path key)

    exif_json = fields.JSONField(null=True)
    gps_lat = fields.FloatField(null=True)
    gps_lng = fields.FloatField(null=True)
    location_text = fields.CharField(512, null=True)

    # lightweight, DB-agnostic embedding for fallback (JSON); true pgvector lives in image_embeddings table
    embedding_json = fields.JSONField(null=True)