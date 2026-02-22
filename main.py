from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import os
import time
import json
import secrets
from pathlib import Path
from database import init_db, db_save_token, db_get_token
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.sensitivity import classify_sensitivity
from utils.workflow import write_approval, write_done
from utils.logger import write_log

VAULT = Path(__file__).parent.resolve()
SECRETS = VAULT / "Secrets"
SECRETS.mkdir(parents=True, exist_ok=True)
STATE_FILE = SECRETS / "oauth_state.json"

app = FastAPI(title="AI Employee Gold Backend", version="1.0.0")

class AutoReplyBody(BaseModel):
    subject: str
    to: str
    body: str
    approved: bool = False

def read_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def write_state(s: dict) -> None:
    STATE_FILE.write_text(json.dumps(s), encoding="utf-8")

def get_env() -> dict:
    load_dotenv(SECRETS / ".env")
    return {
        "CLIENT_ID": os.getenv("CLIENT_ID", ""),
        "CLIENT_SECRET": os.getenv("CLIENT_SECRET", ""),
        "REDIRECT_URI": os.getenv("REDIRECT_URI", "http://localhost:8000/integrations/gmail/callback"),
    }

def store_token(creds: Credentials) -> None:
    env = get_env()
    db_save_token(
        access_token=creds.token,
        refresh_token=creds.refresh_token or "",
        token_uri="https://oauth2.googleapis.com/token",
        client_id=env["CLIENT_ID"],
        client_secret=env["CLIENT_SECRET"],
    )

def load_credentials() -> Credentials | None:
    tok = db_get_token()
    if not tok:
        return None
    return Credentials(
        token=tok["access_token"],
        refresh_token=tok["refresh_token"],
        token_uri=tok["token_uri"],
        client_id=tok["client_id"],
        client_secret=tok["client_secret"],
        scopes=["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send", "email"],
    )

@app.on_event("startup")
def startup():
    init_db()

@app.get("/integrations/gmail/login")
def gmail_login():
    env = get_env()
    if not env["CLIENT_ID"] or not env["CLIENT_SECRET"]:
        raise HTTPException(status_code=400, detail="Missing CLIENT_ID/CLIENT_SECRET in .env")
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": env["CLIENT_ID"],
                "client_secret": env["CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["email", "https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"],
    )
    flow.redirect_uri = env["REDIRECT_URI"]
    state = secrets.token_urlsafe(16)
    s = read_state()
    s[state] = int(time.time())
    write_state(s)
    auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", state=state, prompt="consent")
    write_log("OAuth Start", [f"Client set", f"State: {state}"])
    return JSONResponse({"authorize_url": auth_url, "state": state})

@app.get("/integrations/gmail/callback")
def gmail_callback(request: Request):
    env = get_env()
    query = dict(request.query_params)
    code = query.get("code", "")
    state = query.get("state", "")
    s = read_state()
    if not code or state not in s or int(time.time()) - int(s[state]) > 600:
        raise HTTPException(status_code=400, detail="Invalid state or code")
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": env["CLIENT_ID"],
                "client_secret": env["CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["email", "https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"],
    )
    flow.redirect_uri = env["REDIRECT_URI"]
    flow.fetch_token(code=code)
    store_token(flow.credentials)
    write_log("OAuth Callback", ["Token stored"])
    return JSONResponse({"status": "ok"})

@app.get("/integrations/gmail/fetch")
def gmail_fetch():
    try:
        creds = load_credentials()
        if not creds:
            return JSONResponse({"error": "No credentials"}, status_code=400)
        if not creds.valid and creds.refresh_token:
            from google.auth.transport.requests import Request as GoogleRequest
            creds.refresh(GoogleRequest())
            store_token(creds)
        service = build("gmail", "v1", credentials=creds)
        lst = service.users().messages().list(userId="me", q="is:unread").execute()
        ids = [m["id"] for m in lst.get("messages", [])]
        items = []
        processed = []
        for mid in ids:
            msg = service.users().messages().get(userId="me", id=mid, format="full").execute()
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            sender = headers.get("from", "")
            subject = headers.get("subject", "")
            body = ""
            parts = msg.get("payload", {}).get("parts", [])
            if parts:
                for part in parts:
                    if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                        import base64
                        body = base64.urlsafe_b64decode(part["body"]["data"] + "==").decode("utf-8", errors="ignore")
                        break
            items.append({"sender": sender, "subject": subject})
            write_log("Email Received", [f"From: {sender}", f"Subject: {subject}"])
            sens = classify_sensitivity({}, body)
            if sens == "none":
                reply_body = "Thank you for your email. We will get back to you shortly."
                service.users().messages().send(
                    userId="me",
                    body={
                        "raw": __import__("base64").urlsafe_b64encode(f"To: {sender}\r\nSubject: Re: {subject}\r\n\r\n{reply_body}".encode("utf-8")).decode("utf-8")
                    },
                ).execute()
                stem = f"gmail_auto_{int(time.time())}"
                write_done(stem, "medium", "external_communication", f"# Auto Reply Sent\n- To: {sender}\n- Subject: Re: {subject}\n\n{reply_body}")
                write_log("Reply Sent", [f"To: {sender}", f"Subject: Re: {subject}"])
                processed.append({"subject": subject, "action": "replied"})
            else:
                stem = f"gmail_approval_{int(time.time())}"
                write_approval(stem, subject, "external_communication")
                write_log("Approval Requested", [f"Subject: {subject}"])
                processed.append({"subject": subject, "action": "approval_requested"})
        return JSONResponse({"unread": items, "processed": processed})
    except Exception as e:
        write_log("Fetch Error", [str(e)])
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        pass
