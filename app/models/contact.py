from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.db.base import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    nickname = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
