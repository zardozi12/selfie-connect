from tortoise import fields
from app.models import BaseModel


class Face(BaseModel):
    image = fields.ForeignKeyField("models.Image", related_name="faces", on_delete=fields.CASCADE)
    # bounding box (x, y, w, h) relative [0..1]
    x = fields.FloatField()
    y = fields.FloatField()
    w = fields.FloatField()
    h = fields.FloatField()

    # cluster id if grouped, nullable until clustering
    cluster = fields.ForeignKeyField("models.PersonCluster", related_name="faces", null=True, on_delete=fields.SET_NULL)
