from pydantic import BaseModel, EmailStr

from .user import UserRead


class SendCodeRequest(BaseModel):
    email: EmailStr
    turnstile_token: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
