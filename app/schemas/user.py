from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    nickname: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    code: str = Field(min_length=6, max_length=6)


class UserRead(BaseModel):
    id: int
    nickname: str
    email: EmailStr
    avatar: Optional[str] = None
    last_nickname_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NicknameUpdate(BaseModel):
    nickname: str = Field(min_length=2, max_length=50)


class EmailUpdate(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class HistoryRead(BaseModel):
    id: int
    old_value: str
    new_value: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserRead(BaseModel):
    id: int
    nickname: str
    email: EmailStr
    avatar: Optional[str] = None
    created_at: datetime
    post_count: int = 0
    comment_count: int = 0
    is_banned: int = 0

    class Config:
        from_attributes = True
