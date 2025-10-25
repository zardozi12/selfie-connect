from pydantic import BaseModel, EmailStr, Field, validator
import re

class SignupPayload(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)

    @validator('password')
    def validate_password(cls, v: str):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"