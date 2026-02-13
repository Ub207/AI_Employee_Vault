"""
AI Employee Vault — Config Loader (Silver Tier)
Shared configuration utility. All scripts read settings from config.yaml through this module.
"""

import yaml
from datetime import datetime, timedelta
from pathlib import Path

VAULT_PATH = Path(__file__).parent.resolve()
CONFIG_FILE = VAULT_PATH / "config.yaml"

_config_cache: dict | None = None


def load_config() -> dict:
    """Load and cache config.yaml. Returns the full config dict."""
    global _config_cache
    if _config_cache is None:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


def reload_config() -> dict:
    """Force-reload config.yaml (clears cache)."""
    global _config_cache
    _config_cache = None
    return load_config()


def get_path(folder_name: str) -> Path:
    """Resolve a folder path from config. e.g. get_path('inbox') -> VAULT/Needs_Action"""
    cfg = load_config()
    folder = cfg.get("folders", {}).get(folder_name, folder_name)
    return VAULT_PATH / folder


def get_sla_deadline(priority: str, start_time: datetime | None = None) -> datetime:
    """Return the SLA deadline for a given priority level."""
    cfg = load_config()
    start = start_time or datetime.now()
    prio_cfg = cfg.get("priority", {})
    if priority in prio_cfg and isinstance(prio_cfg[priority], dict):
        hours = prio_cfg[priority].get("sla_hours", 24)
    else:
        default_prio = prio_cfg.get("default", "P2")
        hours = prio_cfg.get(default_prio, {}).get("sla_hours", 24)
    return start + timedelta(hours=hours)


def get_priority_from_keywords(text: str) -> str | None:
    """Scan text for priority keywords, return highest priority found or None."""
    cfg = load_config()
    keywords = cfg.get("priority", {}).get("keywords", {})
    text_lower = text.lower()
    best = None
    for word, prio in keywords.items():
        if word in text_lower:
            if best is None or prio < best:
                best = prio
    return best


def log_event(title: str, details: list[str] | None = None) -> None:
    """Shared logging function — appends to /Logs/<date>.md."""
    logs_dir = get_path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"## {datetime.now().strftime('%H:%M')} - {title}\n")
        for d in (details or []):
            f.write(f"- {d}\n")


if __name__ == "__main__":
    cfg = load_config()
    print("Config loaded successfully:")
    for key in cfg:
        print(f"  {key}: {cfg[key]}")
