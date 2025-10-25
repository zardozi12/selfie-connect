from tortoise import fields
from .base import BaseModel

class Face(BaseModel):
    image = fields.ForeignKeyField("models.Image", related_name="faces", on_delete=fields.CASCADE)
    x = fields.IntField()
    y = fields.IntField()
    w = fields.IntField()
    h = fields.IntField()
    embedding_json = fields.JSONField(null=True)
    cluster = fields.ForeignKeyField(
        "models.PersonCluster",
        related_name="faces",
        null=True,
        on_delete=fields.SET_NULL,
    )

    class Meta:
        table = "faces"
