from datetime import datetime

from pydantic import BaseModel


class AboutRead(BaseModel):
    id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class AboutCreate(BaseModel):
    content: str
