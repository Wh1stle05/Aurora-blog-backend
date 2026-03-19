from datetime import datetime

from pydantic import BaseModel, Field


class TagRead(BaseModel):
    id: int
    name: str
    is_visible: int = 1
    created_at: datetime

    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
