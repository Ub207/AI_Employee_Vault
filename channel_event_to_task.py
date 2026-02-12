import json
import re
from datetime import datetime
from pathlib import Path

VAULT_PATH = Path(__file__).parent.resolve()
NEEDS_ACTION = VAULT_PATH / "Needs_Action"

def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s or "event"

def event_to_task(event_path: Path) -> Path:
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    data = {}
    try:
        with event_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"source": event_path.parent.name, "text": event_path.read_text(encoding="utf-8")}
    source = str(data.get("source", event_path.parent.name))
    sender = str(data.get("from", data.get("sender", "unknown")))
    subject = str(data.get("subject", data.get("text", "New message")))
    priority = str(data.get("priority", "medium"))
    created = datetime.now().strftime("%Y-%m-%d")
    base = f"{source}-{slugify(subject)[:32]}-{datetime.now().strftime('%H%M%S')}.md"
    out = NEEDS_ACTION / base
    sensitivity = "external_communication"
    body = []
    body.append("---")
    body.append("type: task")
    body.append(f"priority: {priority}")
    body.append("status: new")
    body.append(f"created: {created}")
    body.append(f"source: {source}")
    body.append(f"sensitivity: {sensitivity}")
    body.append("---")
    body.append("")
    body.append(f"# Incoming {source} Message")
    body.append(f"- From: {sender}")
    body.append(f"- Subject: {subject}")
    body.append("")
    body.append("## Requested Action")
    body.append("- Draft an appropriate reply and route for approval per handbook.")
    out.write_text("\n".join(body) + "\n", encoding="utf-8")
    return out

if __name__ == "__main__":
    import sys
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if p and p.exists():
        print(event_to_task(p))
