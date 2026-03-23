from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .user import UserRead


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    tags: Optional[str] = None
    slug: Optional[str] = Field(default=None, max_length=255)
    summary: Optional[str] = Field(default=None, max_length=300)
    cover_image: Optional[str] = Field(default=None, max_length=255)


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = None
    tags: Optional[str] = None
    is_visible: Optional[int] = None
    slug: Optional[str] = Field(default=None, max_length=255)
    summary: Optional[str] = Field(default=None, max_length=300)
    cover_image: Optional[str] = Field(default=None, max_length=255)


class PostImageRead(BaseModel):
    id: int
    filename: str
    content_type: str
    object_key: str

    class Config:
        from_attributes = True


class PostRead(BaseModel):
    id: int
    title: str
    slug: str
    content: str
    summary: Optional[str] = None
    cover_image: Optional[str] = None
    tags: Optional[str] = None
    view_count: int = 0
    is_visible: int = 1
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: UserRead
    like_count: int = 0
    dislike_count: int = 0
    comment_count: int = 0
    user_reaction: int = 0
    images: List[PostImageRead] = []

    class Config:
        from_attributes = True
