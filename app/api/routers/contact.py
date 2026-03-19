from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Contact
from app import schemas

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("")
def create_contact(payload: schemas.ContactCreate, db: Session = Depends(get_db)):
    entry = Contact(nickname=payload.nickname, email=payload.email, content=payload.content)
    db.add(entry)
    db.commit()
    return {"ok": True}
