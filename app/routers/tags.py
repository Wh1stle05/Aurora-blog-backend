from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..deps import get_db, require_admin
from ..models import Tag, User
from .. import schemas

router = APIRouter(prefix="/api/tags", tags=["tags"])

@router.get("", response_model=List[schemas.TagRead])
def list_tags(db: Session = Depends(get_db)):
    return db.query(Tag).order_by(Tag.name).all()

@router.post("", response_model=schemas.TagRead)
def create_tag(
    payload: schemas.TagCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    # Check if tag already exists
    existing = db.query(Tag).filter(Tag.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")
    
    tag = Tag(name=payload.name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()
    return {"ok": True}
