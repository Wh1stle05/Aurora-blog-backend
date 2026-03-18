from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    nickname: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    code: str = Field(min_length=6, max_length=6)


class SendCodeRequest(BaseModel):
    email: EmailStr
    turnstile_token: str | None = None


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


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    tags: Optional[str] = None


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = None
    tags: Optional[str] = None
    is_visible: Optional[int] = None


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
    content: str
    tags: Optional[str] = None
    view_count: int = 0
    is_visible: int = 1
    created_at: datetime
    author: UserRead
    like_count: int = 0
    dislike_count: int = 0
    comment_count: int = 0
    user_reaction: int = 0
    images: List[PostImageRead] = []

    class Config:
        from_attributes = True


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


class ReactionCreate(BaseModel):
    target_type: str = Field(pattern="^(post|comment)$")
    target_id: int
    value: int = Field(ge=-1, le=1)


class ContactCreate(BaseModel):
    nickname: str = Field(min_length=2, max_length=50)
    email: EmailStr
    content: str = Field(min_length=1, max_length=2000)


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


class AboutRead(BaseModel):
    id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class AboutCreate(BaseModel):
    content: str


class TagRead(BaseModel):
    id: int
    name: str
    is_visible: int = 1
    created_at: datetime

    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

CommentRead.model_rebuild()
