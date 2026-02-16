"""
business-mcp — FastAPI MCP server for Digital FTE (Hackathon-0).

Capabilities:
  POST /mcp/send-email          — Send an email via SMTP
  POST /mcp/create-linkedin-post — Publish a LinkedIn text post
  POST /mcp/log-activity        — Log a business activity entry

Run:
  uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
"""

import logging

from fastapi import FastAPI
from app.core.config import settings
from app.routers.business import router as business_router

# ── Application-level logging ──
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("business-mcp")

# ── FastAPI app ──
app = FastAPI(
    title="business-mcp",
    description="MCP server for Digital FTE — email, LinkedIn, activity logging.",
    version="1.0.0",
)

app.include_router(business_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "business-mcp"}


logger.info("business-mcp ready on %s:%s", settings.mcp_host, settings.mcp_port)
