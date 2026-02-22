import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

SECRETS = Path(__file__).parent / "Secrets"
SECRETS.mkdir(parents=True, exist_ok=True)
DB_PATH = SECRETS / "app.sqlite"

def init_db() -> None:
    load_dotenv(SECRETS / ".env")
    url = os.getenv("DATABASE_URL", "")
    if url and url.startswith("postgresql"):
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from models.base import Base
            from models.gmail_token import GmailToken  # noqa
            engine = create_engine(url, future=True)
            Base.metadata.create_all(bind=engine)
            return
        except Exception:
            pass
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS gmail_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, access_token TEXT, refresh_token TEXT, token_uri TEXT, client_id TEXT, client_secret TEXT, created_at TEXT)"
    )
    conn.commit()
    conn.close()

def db_save_token(access_token: str, refresh_token: str, token_uri: str, client_id: str, client_secret: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM gmail_tokens")
    cur.execute(
        "INSERT INTO gmail_tokens (access_token, refresh_token, token_uri, client_id, client_secret, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (access_token, refresh_token, token_uri, client_id, client_secret),
    )
    conn.commit()
    conn.close()

def db_get_token() -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT access_token, refresh_token, token_uri, client_id, client_secret FROM gmail_tokens LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"access_token": row[0], "refresh_token": row[1], "token_uri": row[2], "client_id": row[3], "client_secret": row[4]}
