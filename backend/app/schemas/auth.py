from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    profile_image_url: str | None
    is_email_verified: bool
    is_admin: bool
    created_at: datetime | None


class UsageSummaryResponse(BaseModel):
    consultation_count: int
    last_consultation_at: datetime | None


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1)


class DeleteAccountResponse(BaseModel):
    message: str


class DeleteConsultationsResponse(BaseModel):
    message: str
    deleted_count: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
