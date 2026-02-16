"""Health check endpoint."""

import time

from fastapi import APIRouter

from backend.schemas import HealthResponse

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        tier="gold",
        uptime_seconds=round(time.time() - _start_time, 2),
    )
