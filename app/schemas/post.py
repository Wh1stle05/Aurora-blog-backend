from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from .user import UserRead


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    tags: Optional[str] = None
    slug: Optional[str] = Field(default=None, max_length=255)
    summary: Optional[str] = Field(default=None, max_length=300)
    cover_image: Optional[str] = Field(default=None, max_length=255)
    # 展示用发布时间（留空 = 使用上传时间）
    published_at: Optional[datetime] = None


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = None
    tags: Optional[str] = None
    is_visible: Optional[int] = None
    slug: Optional[str] = Field(default=None, max_length=255)
    summary: Optional[str] = Field(default=None, max_length=300)
    cover_image: Optional[str] = Field(default=None, max_length=255)
    # 显式传 null 表示清空自定义时间（回到上传时间）
    published_at: Optional[datetime] = None


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
    # created_at = 页面展示时间（若设置了 published_at 则等于它，否则等于真实上传时间）
    created_at: datetime
    # 真实上传时间（不会被 published_at 影响）
    uploaded_at: Optional[datetime] = None
    # 手动设置的展示时间；为 null 表示跟随上传时间
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    author: UserRead
    like_count: int = 0
    dislike_count: int = 0
    comment_count: int = 0
    user_reaction: int = 0
    images: List[PostImageRead] = []

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def _apply_display_time(self):
        """前端展示用的是 created_at，这里把可编辑的 published_at 映射上去，
        并把真实上传时间保留在 uploaded_at。

        注意：FastAPI 会用 response_model 再验证一次已构造好的实例，
        所以这里必须是幂等的（uploaded_at 只在第一次填充）。
        """
        if self.uploaded_at is None:
            self.uploaded_at = self.created_at
        if self.published_at is not None:
            self.created_at = self.published_at
        return self
