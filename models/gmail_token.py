from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from models.base import Base

class GmailToken(Base):
    __tablename__ = "gmail_tokens"
    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String)
    refresh_token = Column(String)
    token_uri = Column(String)
    client_id = Column(String)
    client_secret = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
