from tortoise import fields
from app.models import BaseModel


class Album(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="albums", on_delete=fields.CASCADE)
    
    name = fields.CharField(255)  # e.g., "Paris Trip", "Family Photos"
    description = fields.TextField(null=True)
    
    # Album type/category
    album_type = fields.CharField(50, default="manual")  # manual, location, date, person
    
    # For location-based albums
    location_text = fields.CharField(512, null=True)
    gps_lat = fields.FloatField(null=True)
    gps_lng = fields.FloatField(null=True)
    
    # For date-based albums
    start_date = fields.DateField(null=True)
    end_date = fields.DateField(null=True)
    
    # For person-based albums
    person_cluster = fields.ForeignKeyField("models.PersonCluster", related_name="albums", null=True, on_delete=fields.SET_NULL)
    
    # Cover image
    cover_image = fields.ForeignKeyField("models.Image", related_name="cover_for_albums", null=True, on_delete=fields.SET_NULL)
    
    # Auto-generated albums have this flag
    is_auto_generated = fields.BooleanField(default=False)
    
    class Meta:
        unique_together = (("user", "name"),)


class AlbumImage(BaseModel):
    """Many-to-many relationship between albums and images"""
    album = fields.ForeignKeyField("models.Album", related_name="album_images", on_delete=fields.CASCADE)
    image = fields.ForeignKeyField("models.Image", related_name="image_albums", on_delete=fields.CASCADE)
    added_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        unique_together = (("album", "image"),)
