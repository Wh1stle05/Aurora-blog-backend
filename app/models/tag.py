from sqlalchemy import Column, Integer, String, DateTime, SmallInteger, func
from app.db.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    is_visible = Column(SmallInteger, default=1, nullable=False)  # 1 为可见，0 为隐藏
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
