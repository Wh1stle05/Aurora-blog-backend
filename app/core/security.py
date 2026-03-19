from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
import os
import hashlib
import secrets

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "120"))
REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "30"))
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MINUTES)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    pepper = os.getenv("REFRESH_TOKEN_PEPPER", "dev_refresh_pepper_change_me")
    data = (token + pepper).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def refresh_token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
