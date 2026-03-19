from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, SmallInteger, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    nickname = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)  # 存储头像文件名
    last_nickname_at = Column(DateTime(timezone=True), nullable=True)  # 上次修改昵称的时间
    is_banned = Column(SmallInteger, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    nickname_history = relationship("UserNicknameHistory", back_populates="user", cascade="all, delete-orphan")
    email_history = relationship("UserEmailHistory", back_populates="user", cascade="all, delete-orphan")
    avatar_history = relationship("UserAvatarHistory", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="user", cascade="all, delete-orphan")


class UserNicknameHistory(Base):
    __tablename__ = "user_nickname_histories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    old_nickname = Column(String(50), nullable=False)
    new_nickname = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="nickname_history")


class UserEmailHistory(Base):
    __tablename__ = "user_email_histories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    old_email = Column(String(255), nullable=False)
    new_email = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="email_history")


class UserAvatarHistory(Base):
    __tablename__ = "user_avatar_histories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    old_avatar = Column(String(255), nullable=True)
    new_avatar = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="avatar_history")
