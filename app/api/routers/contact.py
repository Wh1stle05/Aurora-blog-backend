from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Contact
from app import schemas
from app.services.turnstile import verify_turnstile

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("")
def create_contact(
    payload: schemas.ContactCreate,
    db: Session = Depends(get_db),
    request: Request = None,
):
    if not payload.turnstile_token:
        raise HTTPException(status_code=400, detail="缺少人机验证")
    client_ip = request.client.host if request and request.client else None
    if not verify_turnstile(payload.turnstile_token, client_ip):
        raise HTTPException(status_code=403, detail="人机验证失败")

    entry = Contact(nickname=payload.nickname, email=payload.email, content=payload.content)
    db.add(entry)
    db.commit()
    return {"ok": True}
