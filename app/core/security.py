from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
import os
import hashlib
import secrets

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

import logging

logger = logging.getLogger("blog-api.security")

def _env_str(name: str, default: str) -> str:
    """读取字符串型环境变量。

    空字符串按“未设置”处理：在 Vercel 控制台里很容易把变量留成空值，
    os.getenv(name, default) 在这种情况下会返回 '' 而不是 default。
    """
    value = os.getenv(name)
    return value if value is not None and value.strip() else default


def _env_int(name: str, default: int) -> int:
    raw = _env_str(name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"环境变量 {name} 必须是整数，当前值为 {raw!r}") from exc


JWT_SECRET = _env_str("JWT_SECRET", "dev_secret_change_me")
JWT_EXPIRES_MINUTES = _env_int("JWT_EXPIRES_MINUTES", 120)
REFRESH_TOKEN_EXPIRES_DAYS = _env_int("REFRESH_TOKEN_EXPIRES_DAYS", 30)
ALGORITHM = "HS256"

if _env_str("ENV", "dev").lower() == "prod" and JWT_SECRET == "dev_secret_change_me":
    logger.warning(
        "JWT_SECRET 仍是开发默认值，生产环境请务必设置强随机密钥；"
        "否则任何人都能伪造登录令牌"
    )


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
    pepper = _env_str("REFRESH_TOKEN_PEPPER", "dev_refresh_pepper_change_me")
    data = (token + pepper).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def refresh_token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
