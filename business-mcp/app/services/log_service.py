"""
Business activity logger — writes structured entries to vault/logs/business.log.
"""

import logging
from datetime import datetime, timezone
from app.core.config import settings

# ── Configure the dedicated file logger ──
_logger = logging.getLogger("business_activity")
_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

_handler = logging.FileHandler(settings.log_file_path, encoding="utf-8")
_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
_logger.addHandler(_handler)


def log_activity(action: str, detail: str, status: str = "OK") -> dict:
    """
    Write one line to the business log and return the entry as a dict.
    """
    ts = datetime.now(timezone.utc).isoformat()
    entry = f"action={action} | status={status} | detail={detail}"
    _logger.info(entry)
    return {"timestamp": ts, "action": action, "status": status, "detail": detail}
