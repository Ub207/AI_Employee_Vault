"""Gold-tier FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routes import health, tasks, approvals, logs
from backend.integrations import gmail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Gold-tier database...")
    await init_db()
    logger.info("Database ready.")

    # Start scheduler background loop
    global _scheduler_task
    try:
        from backend.services.scheduler_service import run_scheduler_loop
        _scheduler_task = asyncio.create_task(run_scheduler_loop())
        logger.info("Scheduler started.")
    except Exception as e:
        logger.warning(f"Scheduler not started: {e}")

    yield

    # Shutdown
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    logger.info("Gold-tier backend shut down.")


app = FastAPI(
    title="Digital FTE Gold Backend",
    description="Gold-tier API for the AI Employee Vault — DB-backed task pipeline with sensitivity scoring and SLA tracking.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(logs.router)
app.include_router(gmail.router)
