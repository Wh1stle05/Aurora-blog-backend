from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from ..deps import get_db, get_current_user
from ..models import Reaction, User
from .. import schemas

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


@router.get("/summary")
def summary(target_type: str, target_id: int, db: Session = Depends(get_db)):
    if target_type not in {"post", "comment"}:
        raise HTTPException(status_code=400, detail="Invalid target type")
    rows = (
        db.query(
            func.sum(case((Reaction.value == 1, 1), else_=0)).label("likes"),
            func.sum(case((Reaction.value == -1, 1), else_=0)).label("dislikes"),
        )
        .filter(Reaction.target_type == target_type, Reaction.target_id == target_id)
        .all()
    )
    likes = int(rows[0].likes or 0)
    dislikes = int(rows[0].dislikes or 0)
    return {"likes": likes, "dislikes": dislikes}
