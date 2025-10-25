from tortoise import fields
from .base import BaseModel

class Album(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="albums", on_delete=fields.CASCADE)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    album_type = fields.CharField(max_length=32, default="manual")
    location_text = fields.CharField(max_length=512, null=True)
    gps_lat = fields.FloatField(null=True)
    gps_lng = fields.FloatField(null=True)
    start_date = fields.DateField(null=True)
    end_date = fields.DateField(null=True)
    is_auto_generated = fields.BooleanField(default=False)
    cover_image = fields.ForeignKeyField(
        "models.Image",
        related_name="cover_for_albums",
        null=True,
        on_delete=fields.SET_NULL,
    )
    person_cluster = fields.ForeignKeyField(
        "models.PersonCluster",
        related_name="albums",
        null=True,
        on_delete=fields.SET_NULL,
    )
    # Ensure M2M uses the correct through model and key names
    images = fields.ManyToManyField(
        model_name="models.Image",
        related_name="albums",
        through="models.AlbumImage",
        forward_key="album_id",
        backward_key="image_id",
    )

    class Meta:
        table = "albums"
        unique_together = ("user", "name")

class AlbumImage(BaseModel):
    album = fields.ForeignKeyField("models.Album", on_delete=fields.CASCADE)
    image = fields.ForeignKeyField("models.Image", on_delete=fields.CASCADE)
    added_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "album_images"
        unique_together = ("album", "image")
