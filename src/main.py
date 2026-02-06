from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.router import api_router
from src.config import get_settings
from src.db.database import init_db
from src.scheduler.runner import start_scheduler

settings = get_settings()
scheduler: Optional[object] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    logger.info("Starting up...")
    await init_db()

    # 啟動排程器
    scheduler = start_scheduler()

    yield

    # 關閉排程器
    if scheduler:
        scheduler.shutdown()
    logger.info("Shutting down...")


# Disable interactive docs in production
docs_url = None if settings.is_production else "/docs"
redoc_url = None if settings.is_production else "/redoc"

app = FastAPI(
    title="Credit Card Crawler API",
    description="台灣信用卡資訊查詢與推薦 API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
)

# Configure CORS origins
default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
if settings.cors_origins:
    cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]
else:
    cors_origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/admin/status")
async def admin_status(x_admin_key: str = Header(None)):
    # Require admin key in production
    if settings.is_production:
        if not settings.admin_api_key:
            raise HTTPException(status_code=503, detail="Admin API not configured")
        if x_admin_key != settings.admin_api_key:
            raise HTTPException(status_code=401, detail="Invalid admin key")

    jobs = []
    if scheduler:
        for job in scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else None,
                }
            )

    return {
        "scheduler_running": scheduler is not None and scheduler.running,
        "jobs": jobs,
    }
