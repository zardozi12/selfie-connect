from tortoise import fields
from .base import BaseModel

class Session(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="sessions", on_delete=fields.CASCADE)
    token = fields.CharField(max_length=255, unique=True)
    revoked = fields.BooleanField(default=False)
    expires_at = fields.DatetimeField(null=True)

    class Meta:
        table = "sessions"