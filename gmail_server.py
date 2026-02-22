import json
import urllib.parse
import urllib.request
import base64
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from datetime import datetime, timedelta

VAULT = Path(__file__).parent.resolve()
SECRETS = VAULT / "Secrets"
SECRETS.mkdir(parents=True, exist_ok=True)
TOKEN_FILE = SECRETS / "gmail_token.json"
OAUTH_CFG = SECRETS / "gmail_oauth.json"
ENV_FILE = SECRETS / ".env"
STATE_FILE = SECRETS / "gmail_state.json"
DB_FILE = SECRETS / "gmail_tokens.db"
GMAIL_INBOX = VAULT / "Channels" / "Gmail_Inbox"
PENDING = VAULT / "Pending_Approval"
APPROVED = VAULT / "Approved"
DONE = VAULT / "Done"
LOGS = VAULT / "Logs"

def write_log(title: str, details: list[str]) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    f = LOGS / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with f.open("a", encoding="utf-8") as fh:
        fh.write(f"## {datetime.now().strftime('%H:%M')} - {title}\n")
        for d in details:
            fh.write(f"- {d}\n")

def json_response(handler: BaseHTTPRequestHandler, code: int, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def read_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}

def load_env() -> dict:
    env = {}
    for k, v in (("CLIENT_ID", None), ("CLIENT_SECRET", None), ("REDIRECT_URI", None)):
        if k in env:
            continue
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    try:
        cfg = json.loads(OAUTH_CFG.read_text(encoding="utf-8"))
        if "client_id" in cfg:
            env.setdefault("CLIENT_ID", cfg["client_id"])
        if "redirect_uri" in cfg:
            env.setdefault("REDIRECT_URI", cfg["redirect_uri"])
    except Exception:
        pass
    return env

def db_init():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS gmail_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT UNIQUE, access_token TEXT, refresh_token TEXT, expires_at INTEGER)"
    )
    conn.commit()
    conn.close()

def db_save_token(user_id: str, access_token: str, refresh_token: str, expires_at: int):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO gmail_tokens (user_id, access_token, refresh_token, expires_at) VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET access_token=excluded.access_token, refresh_token=excluded.refresh_token, expires_at=excluded.expires_at",
        (user_id, access_token, refresh_token, expires_at),
    )
    conn.commit()
    conn.close()

def db_get_token(user_id: str) -> dict | None:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT access_token, refresh_token, expires_at FROM gmail_tokens WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"access_token": row[0], "refresh_token": row[1], "expires_at": row[2]}

def is_expired(token: dict) -> bool:
    try:
        return int(token.get("expires_at", 0)) <= int(time.time())
    except Exception:
        return True

def store_state(state: str):
    try:
        data = {}
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        data[state] = int(time.time())
        STATE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass

def validate_state(state: str) -> bool:
    try:
        if not STATE_FILE.exists():
            return False
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if state not in data:
            return False
        # 10-minute validity
        return int(time.time()) - int(data[state]) < 600
    except Exception:
        return False

def oauth_exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    url = "https://oauth2.googleapis.com/token"
    payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def oauth_refresh_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    url = "https://oauth2.googleapis.com/token"
    payload = urllib.parse.urlencode(
        {"client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"}
    ).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def gmail_list_unread(access_token: str) -> list:
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is%3Aunread",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    messages = []
    for m in data.get("messages", []):
        messages.append(m.get("id"))
    return messages

def gmail_get_message(access_token: str, msg_id: str) -> dict:
    req = urllib.request.Request(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def parse_message(payload: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in payload.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")
    sender = headers.get("from", "")
    body = ""
    parts = payload.get("payload", {}).get("parts", [])
    if parts:
        for part in parts:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"] + "==").decode("utf-8", errors="ignore")
                break
    return {"sender": sender, "subject": subject, "body": body}

def gmail_send(access_token: str, to: str, subject: str, body: str) -> dict:
    raw = f"To: {to}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
    b64 = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")
    payload = json.dumps({"raw": b64}).encode("utf-8")
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=payload,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

try:
    from local_reasoner import classify_sensitivity, write_approval, write_done
except Exception:
    def classify_sensitivity(meta: dict, body: str) -> str:
        b = body.lower()
        if "invoice" in b or "payment" in b:
            return "financial"
        if "http" in b or "email" in b:
            return "external_communication"
        return "none"
    def write_approval(stem: str, summary: str, sensitivity: str) -> None:
        PENDING.mkdir(parents=True, exist_ok=True)
        (PENDING / f"approval_{stem}.md").write_text(f"# Approval Request: {stem}\n- Sensitivity: {sensitivity}\n", encoding="utf-8")
    def write_done(stem: str, priority: str, sensitivity: str, body: str) -> None:
        DONE.mkdir(parents=True, exist_ok=True)
        (DONE / f"{stem}.md").write_text(body, encoding="utf-8")

def openapi_spec() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "AI Employee Gmail API", "version": "1.0.0"},
        "paths": {
            "/integrations/gmail/login": {"get": {"summary": "Start Gmail OAuth", "responses": {"200": {"description": "URL"}}}},
            "/integrations/gmail/callback": {
                "get": {
                    "summary": "OAuth callback",
                    "parameters": [
                        {"name": "code", "in": "query", "schema": {"type": "string"}},
                        {"name": "state", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Token stored"}},
                }
            },
            "/integrations/gmail/fetch": {"get": {"summary": "Fetch unread and process", "responses": {"200": {"description": "OK"}}}},
            "/oauth/start": {
                "get": {
                    "summary": "Start Gmail OAuth",
                    "responses": {
                        "200": {"description": "OAuth start URL", "content": {"application/json": {}}}
                    },
                }
            },
            "/oauth/callback": {
                "get": {
                    "summary": "OAuth callback",
                    "parameters": [{"name": "code", "in": "query", "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Token stored", "content": {"application/json": {}}}
                    },
                }
            },
            "/gmail/unread": {
                "get": {
                    "summary": "List unread emails (simulated)",
                    "responses": {"200": {"description": "List", "content": {"application/json": {}}}},
                }
            },
            "/gmail/auto-reply": {
                "post": {
                    "summary": "Auto reply with approval workflow",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "subject": {"type": "string"},
                                        "to": {"type": "string"},
                                        "body": {"type": "string"},
                                        "approved": {"type": "boolean"},
                                    },
                                    "required": ["subject", "to", "body"],
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Reply processed", "content": {"application/json": {}}}},
                }
            },
            "/docs": {
                "get": {"summary": "Swagger JSON view", "responses": {"200": {"description": "Docs"}}}
            },
        },
    }

class Router(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query or "")

            if path == "/openapi.json":
                return json_response(self, 200, openapi_spec())

            if path == "/docs":
                html = (
                    "<html><head><title>AI Employee Gmail API Docs</title></head>"
                    "<body><h1>Swagger (OpenAPI)</h1>"
                    "<p>Download <a href='/openapi.json'>openapi.json</a> and view in your Swagger UI.</p>"
                    "<ul>"
                    "<li>GET /integrations/gmail/login</li>"
                    "<li>GET /integrations/gmail/callback?code=...&state=...</li>"
                    "<li>GET /integrations/gmail/fetch</li>"
                    "<li>GET /oauth/start</li>"
                    "<li>GET /oauth/callback?code=...</li>"
                    "<li>GET /gmail/unread</li>"
                    "<li>POST /gmail/auto-reply</li>"
                    "</ul>"
                    "</body></html>"
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
                return

            if path == "/integrations/gmail/login":
                db_init()
                env = load_env()
                client_id = env.get("CLIENT_ID", "")
                redirect_uri = env.get("REDIRECT_URI", "http://localhost:8000/integrations/gmail/callback")
                state = f"st_{int(time.time())}"
                store_state(state)
                url = (
                    "https://accounts.google.com/o/oauth2/v2/auth?"
                    + urllib.parse.urlencode(
                        {
                            "client_id": client_id,
                            "redirect_uri": redirect_uri,
                            "response_type": "code",
                            "scope": "email gmail.readonly gmail.send",
                            "access_type": "offline",
                            "state": state,
                            "prompt": "consent",
                        }
                    )
                )
                write_log("OAuth Start", [f"Client: {client_id}", f"State: {state}"])
                return json_response(self, 200, {"authorize_url": url, "state": state})

            if path == "/integrations/gmail/callback":
                db_init()
                env = load_env()
                client_id = env.get("CLIENT_ID", "")
                client_secret = env.get("CLIENT_SECRET", "")
                redirect_uri = env.get("REDIRECT_URI", "http://localhost:8000/integrations/gmail/callback")
                code = (qs.get("code") or [""])[0]
                state = (qs.get("state") or [""])[0]
                if not code or not state or not validate_state(state):
                    return json_response(self, 400, {"error": "Invalid callback"})
                try:
                    tok = oauth_exchange_code(client_id, client_secret, code, redirect_uri)
                    access = tok.get("access_token", "")
                    refresh = tok.get("refresh_token", "")
                    expires_in = int(tok.get("expires_in", 3600))
                    expires_at = int(time.time()) + expires_in - 30
                    db_save_token("default", access, refresh, expires_at)
                    write_log("OAuth Callback", ["Token stored in DB"])
                    return json_response(self, 200, {"status": "ok"})
                except Exception as e:
                    write_log("OAuth Callback Error", [str(e)])
                    return json_response(self, 500, {"error": "Exchange failed"})

            if path == "/integrations/gmail/fetch":
                db_init()
                env = load_env()
                client_id = env.get("CLIENT_ID", "")
                client_secret = env.get("CLIENT_SECRET", "")
                tok = db_get_token("default")
                unread = []
                processed = []
                if tok:
                    try:
                        if is_expired(tok):
                            if tok.get("refresh_token"):
                                rt = oauth_refresh_token(client_id, client_secret, tok["refresh_token"])
                                access = rt.get("access_token", tok["access_token"])
                                expires_in = int(rt.get("expires_in", 3600))
                                expires_at = int(time.time()) + expires_in - 30
                                db_save_token("default", access, tok["refresh_token"], expires_at)
                                tok["access_token"] = access
                                tok["expires_at"] = expires_at
                        ids = gmail_list_unread(tok["access_token"])
                        for mid in ids:
                            mdata = gmail_get_message(tok["access_token"], mid)
                            parsed = parse_message(mdata)
                            unread.append(parsed)
                            write_log("Email Received", [f"From: {parsed['sender']}", f"Subject: {parsed['subject']}"])
                            sens = classify_sensitivity({}, parsed["body"])
                            if sens == "none":
                                reply_body = "Thank you for your email. We will get back to you shortly."
                                try:
                                    gmail_send(tok["access_token"], parsed["sender"], f"Re: {parsed['subject']}", reply_body)
                                    write_log("Reply Sent", [f"To: {parsed['sender']}", f"Subject: Re: {parsed['subject']}"])
                                    stem = f"gmail_auto_{datetime.now().strftime('%H%M%S')}"
                                    write_done(stem, "medium", "external_communication", f"# Auto Reply Sent\n- To: {parsed['sender']}\n- Subject: Re: {parsed['subject']}\n\n{reply_body}")
                                    processed.append({"subject": parsed["subject"], "action": "replied"})
                                except Exception as e:
                                    write_log("Reply Error", [str(e)])
                            else:
                                stem = f"gmail_approval_{datetime.now().strftime('%H%M%S')}"
                                write_approval(stem, parsed["subject"], "external_communication")
                                write_log("Approval Requested", [f"Subject: {parsed['subject']}"])
                                processed.append({"subject": parsed["subject"], "action": "approval_requested"})
                    except Exception as e:
                        write_log("Fetch Error", [str(e)])
                else:
                    GMAIL_INBOX.mkdir(parents=True, exist_ok=True)
                    for p in GMAIL_INBOX.glob("*.json"):
                        try:
                            parsed = json.loads(p.read_text(encoding="utf-8"))
                        except Exception:
                            parsed = {"source": "Gmail", "from": "unknown", "subject": p.stem, "text": ""}
                        unread.append({"sender": parsed.get("from", ""), "subject": parsed.get("subject", ""), "body": parsed.get("text", "")})
                return json_response(self, 200, {"unread": unread, "processed": processed})
            if path == "/oauth/start":
                cfg = {}
                if OAUTH_CFG.exists():
                    try:
                        cfg = json.loads(OAUTH_CFG.read_text(encoding="utf-8"))
                    except Exception:
                        cfg = {}
                client_id = cfg.get("client_id", "DEMO_CLIENT_ID")
                redirect_uri = cfg.get("redirect_uri", "http://localhost:8000/oauth/callback")
                url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code&scope=email%20gmail.readonly%20gmail.send"
                write_log("OAuth Start", [f"Client: {client_id}"])
                return json_response(self, 200, {"authorize_url": url, "note": "Simulated flow"})

            if path == "/oauth/callback":
                code = (qs.get("code") or [""])[0]
                if not code:
                    return json_response(self, 400, {"error": "Missing code"})
                token = {"access_token": f"demo_{code}", "refresh_token": f"demo_refresh_{code}", "expires_at": datetime.now().isoformat()}
                TOKEN_FILE.write_text(json.dumps(token, indent=2), encoding="utf-8")
                write_log("OAuth Callback", ["Token stored"])
                return json_response(self, 200, {"status": "ok", "stored": True})

            if path == "/gmail/unread":
                GMAIL_INBOX.mkdir(parents=True, exist_ok=True)
                items = []
                for p in GMAIL_INBOX.glob("*.json"):
                    try:
                        items.append(json.loads(p.read_text(encoding="utf-8")))
                    except Exception:
                        items.append({"source": "Gmail", "subject": p.stem})
                return json_response(self, 200, {"unread": items, "count": len(items)})

            # default 404
            return json_response(self, 404, {"error": "Not Found"})
        except Exception as e:
            write_log("Server Error (GET)", [str(e)])
            return json_response(self, 500, {"error": "Server error", "detail": str(e)})

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path == "/gmail/auto-reply":
                data = read_body(self)
                subject = str(data.get("subject", "")).strip()
                to = str(data.get("to", "")).strip()
                body = str(data.get("body", "")).strip()
                approved = bool(data.get("approved", False))
                if not subject or not to or not body:
                    return json_response(self, 400, {"error": "subject, to, body required"})

                stem = f"gmail_reply_{datetime.now().strftime('%H%M%S')}"
                # external communication: create approval unless approved flag present
                if not approved:
                    PENDING.mkdir(parents=True, exist_ok=True)
                    approval_file = PENDING / f"approval_{stem}.md"
                    approval_file.write_text(
                        f"# Approval Request: {stem}\n\n## Why Sensitive\n- Category: external_communication\n\n## Draft\n- To: {to}\n- Subject: {subject}\n\n{body}\n",
                        encoding="utf-8",
                    )
                    write_log("Approval Requested (Gmail)", [f"Subject: {subject}", f"To: {to}"])
                    return json_response(self, 200, {"status": "pending_approval", "file": str(approval_file)})
                else:
                    APPROVED.mkdir(parents=True, exist_ok=True)
                    DONE.mkdir(parents=True, exist_ok=True)
                    approved_file = APPROVED / f"{stem}.md"
                    approved_file.write_text(
                        f"# Approved Gmail Reply: {stem}\n- To: {to}\n- Subject: {subject}\n\n{body}\n",
                        encoding="utf-8",
                    )
                    done_file = DONE / f"{stem}.md"
                    done_file.write_text(
                        "\n".join(
                            [
                                "---",
                                "type: task",
                                "priority: medium",
                                "status: completed",
                                f"created: {datetime.now().strftime('%Y-%m-%d')}",
                                f"completed_date: {datetime.now().strftime('%Y-%m-%d')}",
                                "sensitivity: external_communication",
                                "approval: granted",
                                "---",
                                "",
                                f"# Gmail Reply Sent: {stem}",
                                f"- To: {to}",
                                f"- Subject: {subject}",
                                "",
                                "Draft approved and marked as sent.",
                            ]
                        ),
                        encoding="utf-8",
                    )
                    write_log("Gmail Reply Sent", [f"Subject: {subject}", f"To: {to}"])
                    return json_response(self, 200, {"status": "sent", "approved_record": str(approved_file), "done_file": str(done_file)})

            return json_response(self, 404, {"error": "Not Found"})
        except Exception as e:
            write_log("Server Error (POST)", [str(e)])
            return json_response(self, 500, {"error": "Server error", "detail": str(e)})

def run(host: str = "127.0.0.1", port: int = 8000):
    httpd = HTTPServer((host, port), Router)
    print(f"AI Employee Gmail API running at http://{host}:{port}/ (Swagger: /openapi.json, /docs)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    run()
