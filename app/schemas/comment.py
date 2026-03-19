from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .user import UserRead


class CommentCreate(BaseModel):
    content: str = Field(min_length=1)
    parent_id: Optional[int] = None


class CommentRead(BaseModel):
    id: int
    post_id: int
    author: UserRead
    parent_id: Optional[int]
    content: str
    is_visible: int = 1
    created_at: datetime
    like_count: int = 0
    dislike_count: int = 0
    user_reaction: int = 0
    children: List["CommentRead"] = []

    class Config:
        from_attributes = True


class AdminCommentRead(BaseModel):
    id: int
    post_id: int
    post_title: str
    author: UserRead
    content: str
    created_at: datetime
    is_visible: int

    class Config:
        from_attributes = True


class AdminCommentVisibilityUpdate(BaseModel):
    is_visible: int = Field(ge=0, le=1)


CommentRead.model_rebuild()
