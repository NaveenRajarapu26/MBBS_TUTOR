# --- ADD/REPLACE in models.py ---

import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, mapped_column, Mapped, Session
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from uuid import uuid4

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///local.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base = declarative_base()

class QueryLog(Base):  # keep old log if you want
    __tablename__ = "query_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_type: Mapped[str] = mapped_column(String(32))
    question: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# NEW: one row per active conversation/session (cookie `sid`)
class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sid: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # session id
    mode: Mapped[str] = mapped_column(String(24), default="explain")       # last used mode
    exam_focus: Mapped[str] = mapped_column(String(64), default="Final MBBS")
    summary: Mapped[str] = mapped_column(Text, default="")                 # rolling long-term memory
    turns: Mapped[int] = mapped_column(Integer, default=0)                 # count of user messages
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(engine)

# Helpers
def get_or_create_conversation(sid: str | None) -> Conversation:
    if not sid:
        sid = str(uuid4())
    with Session(engine) as s:
        conv = s.query(Conversation).filter_by(sid=sid).one_or_none()
        if not conv:
            conv = Conversation(sid=sid)
            s.add(conv); s.commit(); s.refresh(conv)
        return conv

def save_message(conversation_id: int, role: str, content: str) -> None:
    with Session(engine) as s:
        m = Message(conversation_id=conversation_id, role=role, content=content)
        s.add(m)
        # bump turns/updated_at on user messages
        conv = s.get(Conversation, conversation_id)
        if role == "user":
            conv.turns += 1
        conv.updated_at = datetime.utcnow()
        s.commit()

def get_recent_messages(conversation_id: int, limit: int = 12) -> list[Message]:
    with Session(engine) as s:
        return (
            s.query(Message)
            .filter_by(conversation_id=conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
            .all()
        )[::-1]  # oldest→newest

def update_summary(conversation_id: int, new_summary: str) -> None:
    with Session(engine) as s:
        conv = s.get(Conversation, conversation_id)
        conv.summary = new_summary
        conv.updated_at = datetime.utcnow()
        s.commit()
