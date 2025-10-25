from tortoise import fields, models

class OTP(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="otps")
    code = fields.CharField(max_length=8)
    created_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField(null=True)
    used = fields.BooleanField(default=False)