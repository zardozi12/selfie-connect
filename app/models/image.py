from tortoise import fields
from .base import BaseModel

class Image(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="images", on_delete=fields.CASCADE)
    original_filename = fields.CharField(max_length=512, null=True)
    content_type = fields.CharField(max_length=100, null=True)
    size_bytes = fields.BigIntField(null=True)
    width = fields.IntField(null=True)
    height = fields.IntField(null=True)
    gps_lat = fields.FloatField(null=True)
    gps_lng = fields.FloatField(null=True)
    location_text = fields.CharField(max_length=512, null=True)
    storage_key = fields.CharField(max_length=1024)
    thumb_storage_key = fields.CharField(max_length=1024, null=True)
    checksum_sha256 = fields.CharField(max_length=64, index=True)
    phash_hex = fields.CharField(max_length=16, null=True)
    embedding_json = fields.JSONField(null=True)

    class Meta:
        table = "images"
        unique_together = ("user", "checksum_sha256")
