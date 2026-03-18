from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, SmallInteger, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uniq_user_target"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = Column(String(20), nullable=False)  # post or comment
    target_id = Column(Integer, nullable=False)
    value = Column(SmallInteger, nullable=False)  # 1 or -1
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="reactions")
