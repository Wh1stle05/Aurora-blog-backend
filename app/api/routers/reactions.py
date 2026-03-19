from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import Reaction, User
from app import schemas

router = APIRouter(prefix="/api/reactions", tags=["reactions"])


@router.post("")
def react(
    payload: schemas.ReactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.value == 0:
        db.query(Reaction).filter(
            Reaction.user_id == current_user.id,
            Reaction.target_type == payload.target_type,
            Reaction.target_id == payload.target_id,
        ).delete()
        db.commit()
        return {"ok": True}

    existing = db.query(Reaction).filter(
        Reaction.user_id == current_user.id,
        Reaction.target_type == payload.target_type,
        Reaction.target_id == payload.target_id,
    ).first()
    if existing:
        existing.value = payload.value
    else:
        existing = Reaction(
            user_id=current_user.id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            value=payload.value,
        )
        db.add(existing)
    db.commit()
    return {"ok": True}

