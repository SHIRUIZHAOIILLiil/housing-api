from __future__ import annotations

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional


class UserBase(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=30,
        description="Unique username (letters, numbers, underscore).",
        examples=["shirui_zh"]
    )
    email: EmailStr = Field(
        ...,
        min_length=5,
        max_length=254,
        description="Unique email address.",
        examples=["s.zhao@example.com"]
    )


class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plain password (will be hashed and never stored in plain text).",
        examples=["Str0ngPassw0rd!"]
    )

    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain a digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain a letter")
        return v


class UserOut(UserBase):
    id: int
    created_at: str


class TokenOut(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field("bearer", description="Token type, usually 'bearer'.")


class LoginIn(BaseModel):

    username: str = Field(..., min_length=3, max_length=30, examples=["shirui_zh"])
    password: str = Field(..., min_length=8, max_length=128, examples=["Str0ngPassw0rd!"])


class UserPatch(BaseModel):

    email: Optional[str] = Field(None, min_length=5, max_length=254, examples=["new@example.com"])
    password: Optional[str] = Field(None, min_length=8, max_length=128, examples=["EvenStr0ngerPass!"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"email": "new@example.com"},
                {"password": "EvenStr0ngerPass!"},
            ]
        }
    }