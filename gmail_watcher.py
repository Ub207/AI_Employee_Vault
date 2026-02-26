"""
Gmail Watcher — monitors Channels/Gmail_Inbox for JSON event files.
Extends BaseWatcher.

Two modes (config-driven):
  "json"  — watches Channels/Gmail_Inbox/*.json dropped by an external agent (default)
  "imap"  — polls Gmail directly via IMAP4_SSL every check_interval seconds

IMAP setup (Secrets/.env):
  GMAIL_ADDRESS=you@gmail.com
  GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # 16-char Google App Password

JSON event format (for "json" mode):
  {
    "id": "unique_message_id",
    "from": "sender@example.com",
    "subject": "Subject text",
    "received_at": "2026-02-25T10:00:00",
    "snippet": "First few lines of email body..."
  }
"""

import email
import imaplib
import json
import os
import re
from datetime import datetime
from email.header import decode_header
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from base_watcher import BaseWatcher
from config_loader import (
    get_path,
    get_priority_from_keywords,
    load_config,
    log_event,
)

VAULT_PATH = Path(__file__).parent.resolve()


# ── JSON inbox mode ────────────────────────────────────────────────────────────

class _JsonInboxHandler(FileSystemEventHandler):
    """Watchdog handler: routes new .json files to GmailWatcher.process_event."""

    def __init__(self, watcher: "GmailWatcher"):
        self.watcher = watcher

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".json"):
            return
        path = Path(event.src_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            event_dict = {
                "id": data.get("id", path.stem),
                "from": data.get("from", "unknown"),
                "subject": data.get("subject", "(No Subject)"),
                "date": data.get("received_at", datetime.now().isoformat()),
                "snippet": data.get("snippet", ""),
                "_source_file": path,
            }
            self.watcher.process_event(event_dict)
            # Archive processed file so it isn't re-read after restart
            done_dir = path.parent / "processed"
            done_dir.mkdir(exist_ok=True)
            path.rename(done_dir / path.name)
        except Exception as e:
            self.watcher.log(f"JSON inbox error ({path.name}): {e}")
            log_event("GmailWatcher JSON Error", [f"File: {path.name}", f"Error: {e}"])


# ── Main watcher class ─────────────────────────────────────────────────────────

class GmailWatcher(BaseWatcher):
    check_interval = 120   # seconds (used in IMAP mode; JSON mode is event-driven)
    watcher_name = "GmailWatcher"

    def __init__(self):
        super().__init__()
        self.needs_action = get_path("inbox")

        cfg = load_config()
        gmail_cfg = cfg.get("channels", {}).get("gmail", {})
        self.mode: str = gmail_cfg.get("mode", "json")  # "json" | "imap"
        self.imap_query: str = gmail_cfg.get("imap_query", "is:unread is:important")
        self.default_priority: str = gmail_cfg.get("priority", "P1")
        self.inbox_dir = VAULT_PATH / gmail_cfg.get("watch_folder", "Channels/Gmail_Inbox")

        # IMAP state
        self.imap: imaplib.IMAP4_SSL | None = None
        self.processed_ids: set[str] = set()

        # JSON mode state
        self._observer: Observer | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        if self.mode == "imap":
            self._connect_imap()
        else:
            self.log(f"JSON mode: watching {self.inbox_dir}")

    def disconnect(self) -> None:
        if self.mode == "imap" and self.imap:
            try:
                self.imap.logout()
            except Exception:
                pass
            self.imap = None
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=5)
            except Exception:
                pass
            self._observer = None

    def before_loop(self) -> None:
        if self.mode == "json":
            self.inbox_dir.mkdir(parents=True, exist_ok=True)
            self.needs_action.mkdir(parents=True, exist_ok=True)
            handler = _JsonInboxHandler(self)
            self._observer = Observer()
            self._observer.schedule(handler, str(self.inbox_dir), recursive=False)
            self._observer.start()
            self.log(f"Watchdog observer started on {self.inbox_dir}")

            # Process any pre-existing JSON files
            existing = list(self.inbox_dir.glob("*.json"))
            if existing:
                self.log(f"Processing {len(existing)} existing JSON file(s) ...")
                for f in existing:
                    handler.on_created(type("E", (), {"is_directory": False, "src_path": str(f)})())

    # ── Core interface ────────────────────────────────────────────────────────

    def check_new_events(self) -> list[dict]:
        if self.mode == "json":
            # Observer handles events; check observer health
            if self._observer and not self._observer.is_alive():
                raise RuntimeError("Watchdog observer died — triggering reconnect")
            return []  # events are pushed via _JsonInboxHandler.on_created
        else:
            return self._fetch_imap_events()

    def process_event(self, event: dict) -> None:
        """Write a task file to /Needs_Action for this email event."""
        self.needs_action.mkdir(parents=True, exist_ok=True)

        sender = event.get("from", "unknown")
        subject = event.get("subject", "(No Subject)")
        received = event.get("date", datetime.now().isoformat())
        snippet = event.get("snippet", "")
        msg_id = event.get("id", "unknown")

        priority = get_priority_from_keywords(f"{subject} {snippet}") or self.default_priority

        safe_id = re.sub(r"\W+", "_", str(msg_id))[:20]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.needs_action / f"EMAIL_{safe_id}_{timestamp}.md"

        filepath.write_text(
            f"""---
type: email
source: gmail
from: {sender}
subject: "{subject}"
received: {received}
priority: {priority}
status: pending
---

## Email from {sender}

**Subject:** {subject}
**Received:** {received}
**Priority:** {priority}

### Snippet
{snippet}

## Suggested Actions
- [ ] Read full email and determine required action
- [ ] Draft reply if needed → route through Pending_Approval if external
- [ ] Log outcome in /Logs/{datetime.now().strftime('%Y-%m-%d')}.md
""",
            encoding="utf-8",
        )
        self.log(f"Task created: {filepath.name}")
        log_event("GmailWatcher Task Created", [
            f"From: {sender}",
            f"Subject: {subject}",
            f"Priority: {priority}",
            f"File: {filepath.name}",
        ])

    # ── IMAP internals ────────────────────────────────────────────────────────

    def _connect_imap(self) -> None:
        from dotenv import load_dotenv
        load_dotenv(VAULT_PATH / "Secrets" / ".env")

        host = os.getenv("GMAIL_IMAP_HOST", "imap.gmail.com")
        address = os.getenv("GMAIL_ADDRESS", "").strip()
        password = os.getenv("GMAIL_APP_PASSWORD", "").strip()

        if not address or not password:
            raise ValueError(
                "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in Secrets/.env\n"
                "Generate an App Password at: https://myaccount.google.com/apppasswords"
            )

        self.log(f"IMAP connecting to {host} as {address} ...")
        self.imap = imaplib.IMAP4_SSL(host)
        self.imap.login(address, password)
        self.log("Gmail IMAP connected.")

    def _ensure_imap(self) -> None:
        """Reconnect if IMAP session timed out."""
        try:
            self.imap.noop()
        except Exception:
            self.log("IMAP session dropped — reconnecting ...")
            self._connect_imap()

    def _fetch_imap_events(self) -> list[dict]:
        self._ensure_imap()
        events = []
        try:
            self.imap.select("INBOX")
            # X-GM-RAW lets us use native Gmail search queries
            _, raw_ids = self.imap.search(None, f'X-GM-RAW "{self.imap_query}"')
        except imaplib.IMAP4.error as e:
            self.log(f"IMAP search failed: {e}")
            raise

        new_ids = [
            mid.decode()
            for mid in raw_ids[0].split()
            if mid.decode() not in self.processed_ids
        ]
        if new_ids:
            self.log(f"Found {len(new_ids)} new email(s).")

        for msg_id in new_ids:
            try:
                _, data = self.imap.fetch(msg_id, "(RFC822)")
                if not data or not data[0]:
                    continue
                msg = email.message_from_bytes(data[0][1])
                events.append({
                    "id": msg_id,
                    "from": _decode_header_str(msg.get("From", "")),
                    "subject": _decode_header_str(msg.get("Subject", "")),
                    "date": msg.get("Date", ""),
                    "snippet": _extract_snippet(msg),
                })
                self.processed_ids.add(msg_id)
            except Exception as e:
                self.log(f"Error fetching email {msg_id}: {e}")

        return events


# ── Standalone helpers ─────────────────────────────────────────────────────────

def _decode_header_str(value: str) -> str:
    parts = decode_header(value or "")
    out = []
    for part, charset in parts:
        if isinstance(part, bytes):
            out.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(str(part))
    return " ".join(out)


def _extract_snippet(msg: email.message.Message, max_chars: int = 500) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )[:max_chars]
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )[:max_chars]
    return ""


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    GmailWatcher().run()


if __name__ == "__main__":
    main()
