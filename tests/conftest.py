import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is on sys.path for namespace package import
sys.path.insert(0, "/app")

# Ensure DB URL is set before importing app modules
os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["R2_ENDPOINT"] = "https://example.r2.cloudflarestorage.com"
os.environ["R2_ACCESS_KEY_ID"] = "key"
os.environ["R2_SECRET_ACCESS_KEY"] = "secret"
os.environ["R2_BUCKET"] = "bucket"
os.environ["R2_PUBLIC_BASE_URL"] = "https://cdn.example.com"

from app.api import deps
from app.db.base import Base
import app.db.session as database
import app.main as main

engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# Patch global engine/session used by the app
main.engine = engine
main.Base = Base
database.engine = engine
database.SessionLocal = TestingSessionLocal

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

main.app.dependency_overrides[deps.get_db] = override_get_db


@pytest.fixture()
def client():
    return TestClient(main.app)

@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
