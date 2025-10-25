from tortoise import fields
from .base import BaseModel

class PublicShare(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="shares", on_delete=fields.CASCADE)
    album = fields.ForeignKeyField("models.Album", related_name="shares", on_delete=fields.CASCADE)
    token = fields.CharField(64, unique=True, index=True)
    expires_at = fields.DatetimeField(null=False)
    revoked = fields.BooleanField(default=False)
    max_opens = fields.IntField(default=20)
    opens = fields.IntField(default=0)
    ip_lock = fields.CharField(64, null=True)
    user_agent_lock = fields.CharField(256, null=True)
    require_face = fields.BooleanField(default=True)

    class Meta:
        table = "public_shares"

class Share(BaseModel):
    image_id = fields.IntField()
    token = fields.CharField(64, unique=True, index=True)
    otp = fields.CharField(6)
    expires_at = fields.DatetimeField(null=True)
    used = fields.BooleanField(default=False)

    class Meta:
        table = "shares"