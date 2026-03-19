import asyncio
import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback

from app.db.base import Base
from app.db.session import engine
from app.api.routers import auth, posts, comments, reactions, contact, admin, about, tags, stats, monitor

# --- 1. 环境与日志配置 ---
IS_VERCEL = "VERCEL" in os.environ

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("blog-api")

app = FastAPI(title="Blog API")

# --- 2. 全局异常处理 ---
...

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:5173",
    "https://aurorablog.me",
    "https://www.aurorablog.me",
    "https://admin.aurorablog.me",
]

CORS_ORIGINS = os.getenv("CORS_ORIGINS")
if CORS_ORIGINS:
    origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    # 数据库结构现在由 Alembic 统一管理，不再在此处手动执行 SQL 或 create_all
    asyncio.create_task(monitor.monitor_system())


@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/api/system/routes")
def get_routes():
    """获取所有可用的 API 路由列表"""
    url_list = []
    # 排除不需要展示的内部路由
    exclude_names = ["root", "get_routes", "monitor_system"]
    for route in app.routes:
        if hasattr(route, "path") and not route.path.startswith("/uploads"):
            if hasattr(route, "name") and route.name in exclude_names:
                continue
            url_list.append({
                "path": route.path,
                "name": route.name if hasattr(route, "name") else "unnamed",
                "methods": list(route.methods) if hasattr(route, "methods") else []
            })
    return url_list


app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(reactions.router)
app.include_router(contact.router)
app.include_router(admin.router)
app.include_router(about.router)
app.include_router(tags.router)
app.include_router(stats.router)
