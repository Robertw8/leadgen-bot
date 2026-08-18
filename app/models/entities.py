from datetime import datetime
from enum import Enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeadStatus(str, Enum):
    NEW = 'new'
    WARM = 'warm'
    HOT = 'hot'
    TRASH = 'trash'
    HANDOFF = 'handoff'


class Chat(Base):
    __tablename__ = 'chats'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_chat_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    messages: Mapped[list['Message']] = relationship(back_populates='chat')


class Lead(Base):
    __tablename__ = 'leads'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[str] = mapped_column(String(64), index=True)
    tg_chat_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[LeadStatus] = mapped_column(SAEnum(LeadStatus), default=LeadStatus.NEW)
    score: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    pain: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_message_id: Mapped[str] = mapped_column(String(64), index=True)
    tg_user_id: Mapped[str] = mapped_column(String(64), index=True)
    tg_chat_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chat_id: Mapped[int | None] = mapped_column(ForeignKey('chats.id'), nullable=True)
    chat: Mapped[Chat | None] = relationship(back_populates='messages')


class MemoryFact(Base):
    __tablename__ = 'memory_facts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey('leads.id'), index=True)
    fact: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlaybookSnippet(Base):
    __tablename__ = 'playbook_snippets'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)  # script|chat
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
