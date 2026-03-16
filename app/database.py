import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库连接逻辑：优先使用 Vercel Postgres，其次是本地环境变量
DATABASE_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")

# 如果没有配置任何数据库，默认使用本地 Docker 开发环境
if not DATABASE_URL:
    DATABASE_URL = "postgresql+psycopg://blog:blogpass@localhost:5432/blogdb"

# 兼容性处理：SQLAlchemy 2.0+ 要求 postgresql:// 或 postgresql+psycopg:// 
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
