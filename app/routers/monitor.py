import psutil
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..database import SessionLocal
from ..models import User, Comment
from ..deps import get_db

router = APIRouter(prefix="/api/monitor", tags=["monitor"])

@router.post("/ban/{user_id}")
def ban_user(user_id: int, db: Session = Depends(get_db)):
    """FastAPI interface to ban a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if getattr(user, "is_banned", 0) == 0:
        user.is_banned = 1
        db.commit()
        return {"msg": f"User {user_id} has been banned"}
    return {"msg": f"User {user_id} is already banned"}


async def monitor_system():
    while True:
        try:
            # Check system metrics
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            # 当 CPU 使用率 ≥ 90%，内存使用率 ≥ 80%，或磁盘使用率 ≥ 90% 时
            if cpu >= 90 or memory >= 80 or disk >= 90:
                with SessionLocal() as db:
                    # 统计每位用户 5 分钟内的评论数量
                    five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
                    abusive_users = db.query(Comment.author_id).filter(
                        Comment.created_at >= five_mins_ago
                    ).group_by(Comment.author_id).having(
                        func.count(Comment.id) > 50
                    ).all()
                    
                    # 若超过 50 条，通过 FastAPI 接口封禁该用户
                    for (author_id,) in abusive_users:
                        try:
                            # 通过调用接口函数封禁该用户
                            ban_user(author_id, db)
                            print(f"[Monitor] User {author_id} automatically banned due to spam during high system load.")
                        except Exception as inner_e:
                            print(f"[Monitor] Failed to ban user {author_id}: {inner_e}")
                            
        except Exception as e:
            print(f"[Monitor] Error during system monitoring: {e}")
        
        # Check every 30 seconds
        await asyncio.sleep(30)
