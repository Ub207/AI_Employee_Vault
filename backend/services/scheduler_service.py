"""Background scheduler — reads cron schedules from vault config.yaml."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from backend.config import settings
from backend.core.enums import Priority
from backend.database import async_session
from backend.models.task import Task
from backend.models.log import Log

logger = logging.getLogger(__name__)

STATE_FILE = "scheduler_state.json"


def _load_config() -> list[dict]:
    config_path = Path(settings.VAULT_PATH) / "config.yaml"
    if not config_path.exists():
        return []
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("scheduler", [])


def _load_state() -> dict:
    state_path = Path(settings.VAULT_PATH) / STATE_FILE
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {}


def _save_state(state: dict) -> None:
    state_path = Path(settings.VAULT_PATH) / STATE_FILE
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2, default=str)


async def _check_and_create_tasks() -> None:
    try:
        from croniter import croniter
    except ImportError:
        logger.warning("croniter not installed — scheduler disabled")
        return

    schedules = _load_config()
    if not schedules:
        return

    state = _load_state()
    now = datetime.now(timezone.utc)

    async with async_session() as db:
        for sched in schedules:
            name = sched["name"]
            cron_expr = sched["cron"]
            template = sched["template"]
            priority = sched.get("priority", "P2")

            last_run_str = state.get(name)
            if last_run_str:
                last_run = datetime.fromisoformat(last_run_str)
            else:
                last_run = now

            cron = croniter(cron_expr, last_run)
            next_run = cron.get_next(datetime)
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)

            if next_run <= now:
                task = Task(
                    title=f"[Scheduled] {template}",
                    body=f"Auto-created by scheduler: {name}",
                    priority=priority,
                    status="pending",
                    source="scheduler",
                )
                db.add(task)
                db.add(Log(
                    action="scheduler_created_task",
                    details=json.dumps({"schedule": name, "template": template}),
                ))
                state[name] = now.isoformat()
                logger.info(f"Scheduler created task: {template}")
        
        await db.commit()

    _save_state(state)


async def run_scheduler_loop() -> None:
    """Run scheduler checks every 60 seconds."""
    while True:
        try:
            await _check_and_create_tasks()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(60)
