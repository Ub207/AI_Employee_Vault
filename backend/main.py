"""Gold-tier FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routes import health, tasks, approvals, logs, admin
from backend.models.token import Token
from backend.integrations import gmail_router, whatsapp, linkedin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None
_gmail_task: asyncio.Task | None = None
_gmail_shutdown: asyncio.Event | None = None
_whatsapp_task: asyncio.Task | None = None
_whatsapp_shutdown: asyncio.Event | None = None
_linkedin_task: asyncio.Task | None = None
_linkedin_shutdown: asyncio.Event | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Gold-tier database...")
    await init_db()
    logger.info("Database ready.")

    global _scheduler_task, _gmail_task, _gmail_shutdown, _whatsapp_task, _whatsapp_shutdown, _linkedin_task, _linkedin_shutdown
    try:
        from backend.services.scheduler_service import run_scheduler_loop
        _scheduler_task = asyncio.create_task(run_scheduler_loop())
        logger.info("Scheduler started.")
    except Exception as e:
        logger.warning(f"Scheduler not started: {e}")

    # Start Gmail polling loop with a dedicated shutdown event for clean exit
    try:
        from backend.services.gmail_service import run_gmail_poll_loop
        _gmail_shutdown = asyncio.Event()
        _gmail_task = asyncio.create_task(run_gmail_poll_loop(_gmail_shutdown))
        logger.info("Gmail poller started.")
    except Exception as e:
        logger.warning(f"Gmail poller not started: {e}")

    # Start WhatsApp polling loop (fallback for missed webhooks)
    try:
        from backend.services.whatsapp_service import run_whatsapp_poll_loop
        _whatsapp_shutdown = asyncio.Event()
        _whatsapp_task = asyncio.create_task(run_whatsapp_poll_loop(_whatsapp_shutdown))
        logger.info("WhatsApp poller started.")
    except Exception as e:
        logger.warning(f"WhatsApp poller not started: {e}")

    # Start LinkedIn token health polling loop
    try:
        from backend.services.linkedin_service import run_linkedin_poll_loop
        _linkedin_shutdown = asyncio.Event()
        _linkedin_task = asyncio.create_task(run_linkedin_poll_loop(_linkedin_shutdown))
        logger.info("LinkedIn poller started.")
    except Exception as e:
        logger.warning(f"LinkedIn poller not started: {e}")

    yield

    # Shutdown — signal all loops before cancelling tasks
    for event in (_gmail_shutdown, _whatsapp_shutdown, _linkedin_shutdown):
        if event:
            event.set()
    for task in (_scheduler_task, _gmail_task, _whatsapp_task, _linkedin_task):
        if task:
            task.cancel()
            try:
                await task
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
app.include_router(gmail_router.router)
app.include_router(whatsapp.router)
app.include_router(linkedin.router)
app.include_router(admin.router)
