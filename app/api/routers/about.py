from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db, require_admin
from app.models import AboutPage, User
from app import schemas

router = APIRouter(prefix="/api/about", tags=["about"])

# 前台获取最新的 About 内容
@router.get("", response_model=schemas.AboutRead)
def get_latest_about(db: Session = Depends(get_db)):
    about = db.query(AboutPage).order_by(AboutPage.created_at.desc()).first()
    if not about:
        # 如果数据库没有记录，返回一个默认值
        return {
            "id": 0,
            "content": "# 关于我\n\n尚未设置关于页内容，请在管理后台更新。",
            "created_at": "2024-01-01T00:00:00"
        }
    return about

# 后台管理接口 (需要管理员权限)
@router.get("/history", response_model=List[schemas.AboutRead])
def list_about_history(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    return db.query(AboutPage).order_by(AboutPage.created_at.desc()).all()

@router.post("", response_model=schemas.AboutRead)
def create_about_version(
    payload: schemas.AboutCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    about = AboutPage(content=payload.content)
    db.add(about)
    db.commit()
    db.refresh(about)
    return about

@router.delete("/{about_id}")
def delete_about_version(
    about_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    about = db.query(AboutPage).filter(AboutPage.id == about_id).first()
    if not about:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(about)
    db.commit()
    return {"ok": True}
