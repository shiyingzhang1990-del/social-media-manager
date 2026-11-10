"""
Social Media Manager - Main Application
FastAPI backend serving the dashboard and API.
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings, BASE_DIR
from backend.database import init_db
from backend.api import accounts_router, content_router, dashboard_router, groups_router, templates_router, publish_router, analytics_router
from backend.api.auth import router as auth_router, create_default_admin, get_current_user
from backend.migrate import run_migration
from backend.scheduler import SchedulerEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

scheduler = SchedulerEngine(poll_interval=settings.SCHEDULER_POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB and start scheduler on startup, stop on shutdown."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    run_migration()
    create_default_admin()
    scheduler.start()
    yield
    scheduler.stop()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS - allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(accounts_router, dependencies=[Depends(get_current_user)])
app.include_router(content_router, dependencies=[Depends(get_current_user)])
app.include_router(dashboard_router, dependencies=[Depends(get_current_user)])
app.include_router(groups_router, dependencies=[Depends(get_current_user)])
app.include_router(templates_router, dependencies=[Depends(get_current_user)])
app.include_router(publish_router, dependencies=[Depends(get_current_user)])
app.include_router(analytics_router, dependencies=[Depends(get_current_user)])
app.include_router(auth_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# Serve frontend static files
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


def main():
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )


if __name__ == "__main__":
    main()
