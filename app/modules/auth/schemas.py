from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    # min_length=8 is the minimum; production deployments should enforce stronger policies
    password: str = Field(min_length=8, max_length=100)
    display_name: str = Field(min_length=1, max_length=100)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str
    avatar_url: str | None
    # Intentionally omits hashed_password, preferences, and is_active from public API responses
    created_at: datetime


class UserUpdate(BaseModel):
    # All fields optional — PATCH semantics; callers send only the fields they want to change
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # Seconds until the access token expires — lets clients schedule a refresh proactively
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str
