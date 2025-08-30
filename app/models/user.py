from tortoise import fields
from app.models import BaseModel


class User(BaseModel):
    email = fields.CharField(255, unique=True, index=True)
    name = fields.CharField(255, null=True)
    password_hash = fields.CharField(255)

    # per-user Data Encryption Key (DEK), encrypted with server MASTER_KEY (Fernet)
    dek_encrypted_b64 = fields.TextField(null=True)

    images: fields.ReverseRelation["Image"]
    clusters: fields.ReverseRelation["PersonCluster"]


class PersonCluster(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="clusters", on_delete=fields.CASCADE)
    label = fields.CharField(255, default="Unknown")  # user-rename-able
    note = fields.TextField(null=True)