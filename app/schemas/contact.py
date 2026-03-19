from pydantic import BaseModel, EmailStr, Field


class ContactCreate(BaseModel):
    nickname: str = Field(min_length=2, max_length=50)
    email: EmailStr
    content: str = Field(min_length=1, max_length=2000)
