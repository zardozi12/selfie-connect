from tortoise import fields
from .base import BaseModel

class User(BaseModel):
    email = fields.CharField(max_length=255, unique=True, index=True)
    name = fields.CharField(max_length=255, null=True)
    password_hash = fields.CharField(max_length=255)
    dek_encrypted_b64 = fields.TextField()
    face_embedding_json = fields.JSONField(null=True)
    is_admin = fields.BooleanField(default=False)  # Add missing is_admin field

    class Meta:
        table = "users"

class PersonCluster(BaseModel):
    user = fields.ForeignKeyField("models.User", related_name="person_clusters")
    name = fields.CharField(max_length=255)
    face_embedding_json = fields.JSONField()
    representative_face_id = fields.CharField(max_length=255, null=True)
    confidence_score = fields.FloatField(default=0.0)
    
    @property
    def label(self) -> str:
        return self.name

    @label.setter
    def label(self, value: str):
        self.name = value
    
    class Meta:
        table = "person_clusters"