from pydantic import BaseModel, EmailStr, Field


class SignupPayload(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    email: EmailStr
    password: str = Field(min_length=6, max_length=255)


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"