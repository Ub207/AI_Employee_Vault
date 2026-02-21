"""
WhatsApp Playwright Watcher
----------------------------
Pehli baar: Browser khulega, QR code scan karo apne phone se.
Session save ho jaata hai — dobara scan ki zaroorat nahi.

Usage:
    python whatsapp_playwright_watcher.py           # normal run
    python whatsapp_playwright_watcher.py --setup   # QR scan mode (headless=False)
"""

import argparse
import json
import time
import sys
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

VAULT_PATH    = Path(__file__).parent.resolve()
NEEDS_ACTION  = VAULT_PATH / "Needs_Action"
SESSION_PATH  = VAULT_PATH / ".whatsapp_session"   # browser profile saved here

# Keywords jo urgent messages identify karein
KEYWORDS = [
    "urgent", "asap", "invoice", "payment", "help",
    "price", "quote", "meeting", "call me", "important",
    "order", "refund", "complaint",
]

CHECK_INTERVAL = 30   # seconds between checks
MAX_RETRIES    = 3    # reconnect attempts on crash


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def is_keyword_match(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)


def create_task_file(sender: str, message: str, chat_name: str) -> Path:
    """Create a Needs_Action task file for this WhatsApp message."""
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in chat_name)[:30]
    filepath = NEEDS_ACTION / f"WHATSAPP_{safe_name}_{timestamp}.md"

    content = f"""---
type: whatsapp_message
source: whatsapp
sender: {sender}
chat: {chat_name}
received: {datetime.now().isoformat()}
priority: P1
status: pending
sensitivity_score: 0.3
approval: not_required
---

## WhatsApp Message

**From:** {chat_name} ({sender})
**Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Message Content
{message}

## Suggested Actions
- [ ] Review message and determine response
- [ ] Draft reply (requires approval before sending)
- [ ] Log outcome in /Logs/{datetime.now().strftime('%Y-%m-%d')}.md
"""
    filepath.write_text(content, encoding="utf-8")
    log(f"Task created: {filepath.name}")
    return filepath


# ── Core Watcher ──────────────────────────────────────────────────────────────

class WhatsAppWatcher:
    def __init__(self, headless: bool = True, setup_mode: bool = False):
        self.headless = headless
        self.setup_mode = setup_mode
        self.seen_messages: set[str] = set()
        self.browser = None
        self.page = None

    def start(self, playwright):
        """Launch browser with saved session."""
        SESSION_PATH.mkdir(parents=True, exist_ok=True)
        log(f"Launching browser (headless={self.headless}) ...")

        # WhatsApp Web headless mode block karta hai — always visible run karo
        # Window minimize kar sakte ho taskbar se
        self.browser = playwright.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_PATH),
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-notifications",
            ],
        )
        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()

    def wait_for_login(self):
        """Navigate to WhatsApp Web and wait until logged in."""
        log("Opening web.whatsapp.com ...")
        self.page.goto("https://web.whatsapp.com", timeout=60_000)

        # Updated selectors for current WhatsApp Web UI (2025)
        LOGGED_IN_SELECTORS = [
            '#side',
            '#pane-side',
            '[data-testid="chat-list"]',
            'div[aria-label="Chat list"]',
            '[data-testid="chatlist-header"]',
            '[aria-label="Search input textbox"]',
            '[data-testid="search-input"]',
            '[data-testid="default-user"]',
            'div[tabindex="-1"][role="grid"]',
        ]

        def is_logged_in(total_timeout_ms=15_000) -> bool:
            # Divide total timeout evenly across selectors
            per_selector_ms = max(2_000, total_timeout_ms // len(LOGGED_IN_SELECTORS))
            for selector in LOGGED_IN_SELECTORS:
                try:
                    self.page.wait_for_selector(selector, timeout=per_selector_ms)
                    log(f"Logged in detected via: {selector}")
                    return True
                except Exception:
                    continue
            # JS fallback: QR canvas gone aur app loaded
            try:
                result = self.page.evaluate(
                    "() => !!document.getElementById('side') || "
                    "!!document.getElementById('pane-side') || "
                    "(!document.querySelector('canvas[aria-label]') && "
                    " !!document.querySelector('#app > div > div'))"
                )
                if result:
                    log("Logged in detected via JS check")
                    return True
            except Exception:
                pass
            return False

        # Check agar already logged in hai
        if is_logged_in(total_timeout_ms=15_000):
            log("Already logged in!")
            return

        # QR code wait — setup mode ya session expire hone pe
        if not self.setup_mode:
            log("Session expired ya login lost — setup mode mein chalaao:")
            log("  python whatsapp_playwright_watcher.py --setup")
            sys.exit(1)

        log("QR code scan karo apne phone se ...")
        log("Waiting for QR scan (5 minutes) ...")
        if is_logged_in(total_timeout_ms=300_000):
            log("Login successful! Session saved.")
        else:
            log("Login timeout — dobara try karo.")
            sys.exit(1)

    def get_unread_messages(self) -> list[dict]:
        """Chat list se unread messages fetch karo."""
        messages = []
        try:
            # Unread badge wale chats dhundo
            unread_chats = self.page.query_selector_all(
                '[data-testid="chat-list"] [data-testid="cell-frame-container"]'
            )

            for chat in unread_chats:
                try:
                    # Unread count badge check karo
                    badge = chat.query_selector('[data-testid="icon-unread-count"]')
                    if not badge:
                        continue

                    # Chat name
                    name_el = chat.query_selector('[data-testid="cell-frame-title"] span')
                    chat_name = name_el.inner_text() if name_el else "Unknown"

                    # Last message preview
                    msg_el = chat.query_selector('[data-testid="last-msg-status"] ~ span, '
                                                  '[data-testid="cell-frame-primary-detail"]')
                    message = msg_el.inner_text() if msg_el else ""

                    # Unique key — dedup ke liye
                    key = f"{chat_name}:{message}"
                    if key in self.seen_messages:
                        continue

                    if is_keyword_match(message) or is_keyword_match(chat_name):
                        messages.append({
                            "chat_name": chat_name,
                            "sender": chat_name,
                            "message": message,
                            "key": key,
                        })

                except Exception:
                    continue

        except Exception as e:
            log(f"Error reading chats: {e}")

        return messages

    def run_loop(self):
        """Main polling loop."""
        log(f"WhatsApp Watcher active — checking every {CHECK_INTERVAL}s")
        log(f"Keywords: {', '.join(KEYWORDS)}")

        while True:
            try:
                # Page alive check
                if self.page.is_closed():
                    log("Page closed — reconnecting ...")
                    self.wait_for_login()

                messages = self.get_unread_messages()

                for msg in messages:
                    create_task_file(
                        sender=msg["sender"],
                        message=msg["message"],
                        chat_name=msg["chat_name"],
                    )
                    self.seen_messages.add(msg["key"])

                if not messages:
                    log("No new keyword messages.")

            except Exception as e:
                log(f"Loop error: {e}")

            time.sleep(CHECK_INTERVAL)

    def close(self):
        if self.browser:
            self.browser.close()


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="WhatsApp Playwright Watcher")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Pehli baar QR scan ke liye visible browser open karo",
    )
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    retries = 0
    while retries < MAX_RETRIES:
        watcher = WhatsAppWatcher(headless=False, setup_mode=args.setup)
        try:
            with sync_playwright() as p:
                watcher.start(p)
                watcher.wait_for_login()

                if args.setup:
                    log("Setup complete! Session saved.")
                    log("Ab normal mode mein chalaao: python whatsapp_playwright_watcher.py")
                    watcher.close()
                    return

                watcher.run_loop()

        except KeyboardInterrupt:
            log("Watcher stopped by user.")
            watcher.close()
            return

        except Exception as e:
            log(f"Crash: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                log(f"Restarting in 10s ... (attempt {retries}/{MAX_RETRIES})")
                time.sleep(10)
            else:
                log("Max retries reached. Watcher stopped.")
                watcher.close()
                sys.exit(1)


if __name__ == "__main__":
    main()
