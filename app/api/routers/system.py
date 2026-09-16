import hmac
import logging
import os

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import text

from app.api.routers.monitor import run_monitor_once
from app.db.session import engine

logger = logging.getLogger("blog-api.system")

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
def health():
    """轻量健康检查：确认进程存活且数据库可连接。"""
    database_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        database_ok = False
        logger.warning("[Health] database check failed: %s", exc)

    return {
        "status": "ok" if database_ok else "degraded",
        "database": database_ok,
    }


def _verify_cron_secret(authorization: str | None, secret: str | None) -> None:
    """校验定时任务密钥。

    Vercel Cron 在项目里配置了 CRON_SECRET 环境变量时，会自动带上
    `Authorization: Bearer <CRON_SECRET>`；其他平台的定时器可以用 ?secret= 传入。
    """
    expected = os.getenv("CRON_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="CRON_SECRET is not configured")

    provided = ""
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    if not provided:
        provided = (secret or "").strip()

    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@router.api_route("/cron/monitor", methods=["GET", "POST"])
def cron_monitor(
    authorization: str | None = Header(default=None),
    secret: str | None = Query(default=None),
):
    """定时任务入口（serverless 环境替代常驻监控循环）。"""
    _verify_cron_secret(authorization, secret)
    result = run_monitor_once(check_system_load=False)
    return {"success": True, "data": result}
