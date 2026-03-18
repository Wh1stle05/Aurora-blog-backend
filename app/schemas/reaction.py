from pydantic import BaseModel, Field


class ReactionCreate(BaseModel):
    target_type: str = Field(pattern="^(post|comment)$")
    target_id: int
    value: int = Field(ge=-1, le=1)
