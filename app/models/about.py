from sqlalchemy import Column, Integer, Text, DateTime, func
from app.db.base import Base


class AboutPage(Base):
    __tablename__ = "about_pages"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
