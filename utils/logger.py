from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).parent.parent.resolve()
LOGS = VAULT / "Logs"

def write_log(title: str, details: list[str]) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    f = LOGS / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with f.open("a", encoding="utf-8") as fh:
        fh.write(f"## {datetime.now().strftime('%H:%M')} - {title}\n")
        for d in details:
            fh.write(f"- {d}\n")
