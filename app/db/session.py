import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .base import Base

DATABASE_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql+psycopg://blog:blogpass@localhost:5432/blogdb"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Vercel 自动注入 VERCEL=1；其他 serverless 平台可显式设置 SERVERLESS=1
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("SERVERLESS"))

# serverless 实例会被大量并发创建，连接池会迅速打爆数据库连接数上限，
# 因此默认不池化（依赖数据库侧/上游池化，如 Neon 的 -pooler 连接串）。
# 可用 DB_POOL=default 在 serverless 环境下强制恢复连接池。
_POOL_MODE = os.getenv("DB_POOL", "").strip().lower()
_use_null_pool = IS_SERVERLESS if not _POOL_MODE else _POOL_MODE in {"null", "nullpool"}

_engine_kwargs: dict = {"pool_pre_ping": True}
if _use_null_pool:
    _engine_kwargs["poolclass"] = NullPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
