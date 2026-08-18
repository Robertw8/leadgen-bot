from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models.entities import Lead, LeadStatus, MemoryFact, Message, PlaybookSnippet


class MessageRepo:
    def __init__(self, db: Session):
        self.db = db

    def save(self, tg_message_id: str, tg_user_id: str, tg_chat_id: str, role: str, text: str) -> Message:
        msg = Message(
            tg_message_id=tg_message_id,
            tg_user_id=tg_user_id,
            tg_chat_id=tg_chat_id,
            role=role,
            text=text,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def last_messages(self, tg_chat_id: str, limit: int = 20) -> list[Message]:
        q = (
            select(Message)
            .where(Message.tg_chat_id == tg_chat_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        return list(reversed(self.db.execute(q).scalars().all()))


class LeadRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, tg_user_id: str, tg_chat_id: str) -> Lead:
        q = select(Lead).where(Lead.tg_user_id == tg_user_id, Lead.tg_chat_id == tg_chat_id)
        lead = self.db.execute(q).scalar_one_or_none()
        if lead:
            return lead
        lead = Lead(tg_user_id=tg_user_id, tg_chat_id=tg_chat_id)
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update_status(self, lead: Lead, status: LeadStatus, score: int | None = None) -> Lead:
        lead.status = status
        if score is not None:
            lead.score = score
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update_summary(self, lead: Lead, summary: str, pain: str, next_step: str) -> Lead:
        lead.summary = summary
        lead.pain = pain
        lead.next_step = next_step
        self.db.commit()
        self.db.refresh(lead)
        return lead


class MemoryRepo:
    def __init__(self, db: Session):
        self.db = db

    def add_fact(self, lead_id: int, fact: str) -> None:
        self.db.add(MemoryFact(lead_id=lead_id, fact=fact))
        self.db.commit()

    def recent_facts(self, lead_id: int, limit: int = 6) -> list[str]:
        q = (
            select(MemoryFact)
            .where(MemoryFact.lead_id == lead_id)
            .order_by(desc(MemoryFact.created_at))
            .limit(limit)
        )
        return [row.fact for row in self.db.execute(q).scalars().all()]


class PlaybookRepo:
    def __init__(self, db: Session):
        self.db = db

    def add_snippet(self, source_type: str, source_name: str, content: str) -> None:
        self.db.add(PlaybookSnippet(source_type=source_type, source_name=source_name, content=content))
        self.db.commit()

    def find_relevant(self, query: str, limit: int = 5) -> list[str]:
        keywords = [w.strip() for w in query.lower().split() if len(w.strip()) > 3][:8]
        if not keywords:
            return []

        conditions = [PlaybookSnippet.content.ilike(f'%{kw}%') for kw in keywords]
        q = select(PlaybookSnippet).where(or_(*conditions)).order_by(desc(PlaybookSnippet.created_at)).limit(limit)
        snippets = self.db.execute(q).scalars().all()
        return [s.content for s in snippets]
