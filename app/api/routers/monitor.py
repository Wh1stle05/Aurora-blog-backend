import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.db.session import SessionLocal
from app.models import Comment, User

logger = logging.getLogger("blog-api.monitor")

# 系统负载阈值（仅自托管/容器环境有效）
CPU_THRESHOLD = 90.0
MEMORY_THRESHOLD = 80.0
DISK_THRESHOLD = 90.0

# 反滥用规则：5 分钟内评论数超过该值即自动封禁
ABUSE_WINDOW_MINUTES = 5
ABUSE_COMMENT_THRESHOLD = 50

# 自托管模式下监控循环的间隔（秒）
MONITOR_INTERVAL_SECONDS = 30


def _read_system_load() -> dict:
    """读取宿主机负载。psutil 延迟导入：serverless 环境不依赖它。"""
    import psutil

    return {
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent,
    }


def _load_is_high(load: dict) -> bool:
    return (
        load["cpu"] >= CPU_THRESHOLD
        or load["memory"] >= MEMORY_THRESHOLD
        or load["disk"] >= DISK_THRESHOLD
    )


def ban_abusive_users() -> list[int]:
    """封禁短时间内高频评论的用户，返回本次被封禁的用户 ID 列表。"""
    five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=ABUSE_WINDOW_MINUTES)
    banned: list[int] = []

    with SessionLocal() as db:
        abusive_users = (
            db.query(Comment.author_id)
            .filter(Comment.created_at >= five_mins_ago)
            .group_by(Comment.author_id)
            .having(func.count(Comment.id) > ABUSE_COMMENT_THRESHOLD)
            .all()
        )

        for (author_id,) in abusive_users:
            try:
                user = db.get(User, author_id)
                if user and getattr(user, "is_banned", 0) == 0:
                    user.is_banned = 1
                    db.commit()
                    banned.append(author_id)
                    logger.warning(
                        "[Monitor] user %s automatically banned: more than %s comments within %s minutes",
                        author_id,
                        ABUSE_COMMENT_THRESHOLD,
                        ABUSE_WINDOW_MINUTES,
                    )
            except Exception as inner_e:
                db.rollback()
                logger.warning("[Monitor] failed to ban user %s: %s", author_id, inner_e)

    return banned


def run_monitor_once(*, check_system_load: bool = True) -> dict:
    """执行一次监控。

    - check_system_load=True：自托管模式，仅在宿主机负载过高时才做反滥用检查。
    - check_system_load=False：serverless（Vercel / Cloud Run 等）模式，宿主机负载
      指标无意义，只按评论频率做反滥用检查。
    """
    result: dict = {
        "checked_system_load": check_system_load,
        "load": None,
        "skipped": False,
        "banned_users": [],
    }

    if check_system_load:
        try:
            load = _read_system_load()
        except Exception as exc:  # psutil 缺失或容器内不可用
            logger.warning("[Monitor] psutil unavailable, skipping load check: %s", exc)
            load = None

        result["load"] = load
        if load is not None and not _load_is_high(load):
            result["skipped"] = True
            return result

    result["banned_users"] = ban_abusive_users()
    return result


async def monitor_system():
    """自托管环境下的常驻监控循环；serverless 环境请改用定时任务调用 run_monitor_once。"""
    while True:
        try:
            run_monitor_once(check_system_load=True)
        except Exception as exc:
            logger.warning("[Monitor] error during system monitoring: %s", exc)

        await asyncio.sleep(MONITOR_INTERVAL_SECONDS)
