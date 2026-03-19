import psutil
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import func

from app.db.session import SessionLocal
from app.models import Comment, User


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
                    
                    # 若超过 50 条，直接在监控任务中封禁该用户
                    for (author_id,) in abusive_users:
                        try:
                            user = db.get(User, author_id)
                            if user and getattr(user, "is_banned", 0) == 0:
                                user.is_banned = 1
                                db.commit()
                            print(f"[Monitor] User {author_id} automatically banned due to spam during high system load.")
                        except Exception as inner_e:
                            print(f"[Monitor] Failed to ban user {author_id}: {inner_e}")
                            
        except Exception as e:
            print(f"[Monitor] Error during system monitoring: {e}")
        
        # Check every 30 seconds
        await asyncio.sleep(30)
