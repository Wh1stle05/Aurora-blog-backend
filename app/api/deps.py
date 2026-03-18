from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError
import os

from app.db.session import SessionLocal
from app.models import User
from app.core.security import ALGORITHM, JWT_SECRET

ADMIN_EMAILS = {email.strip() for email in os.getenv("ADMIN_EMAILS", "").split(",") if email.strip()}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication",
    )
    
    # Try getting token from Cookie first (Production recommendation)
    token = request.cookies.get("access_token")
    
    # Fallback to Authorization Header (if needed for API testing)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise credentials_exception
    return user


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
        
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    user = db.query(User).filter(User.id == int(user_id)).first()
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not ADMIN_EMAILS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access not configured")
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user
