from fastapi import APIRouter
from pydantic import BaseModel

from app.pipeline.types import InboundEvent
from app.services.queue import EventQueue

router = APIRouter()
queue = EventQueue()


class IngestPayload(BaseModel):
    tg_message_id: str
    tg_chat_id: str
    tg_user_id: str
    text: str


@router.get('/health')
def health() -> dict:
    return {'ok': True}


@router.post('/ingest')
def ingest(payload: IngestPayload) -> dict:
    queue.push(InboundEvent(**payload.model_dump()))
    return {'queued': True}
