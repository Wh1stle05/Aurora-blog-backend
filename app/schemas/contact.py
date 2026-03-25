from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ContactCreate(BaseModel):
    nickname: str = Field(min_length=2, max_length=50)
    email: EmailStr
    content: str = Field(min_length=1, max_length=2000)
    turnstile_token: str | None = None


class AdminContactRead(BaseModel):
    id: int
    nickname: str
    email: EmailStr
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
