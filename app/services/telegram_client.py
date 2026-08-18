from __future__ import annotations

from telethon import TelegramClient, events

from app.core.config import settings
from app.pipeline.types import InboundEvent
from app.services.queue import EventQueue


class TelegramIngest:
    def __init__(self, queue: EventQueue):
        if not settings.tg_api_id or not settings.tg_api_hash:
            raise RuntimeError('TG_API_ID/TG_API_HASH are required')
        self.client = TelegramClient(settings.tg_session_name, settings.tg_api_id, settings.tg_api_hash)
        self.queue = queue

    async def run(self) -> None:
        @self.client.on(events.NewMessage(incoming=True))
        async def handler(event):
            if not event.raw_text:
                return
            sender = await event.get_sender()
            inbound = InboundEvent(
                tg_message_id=str(event.id),
                tg_chat_id=str(event.chat_id),
                tg_user_id=str(getattr(sender, 'id', 'unknown')),
                text=event.raw_text,
            )
            self.queue.push(inbound)

        await self.client.start()
        await self.client.run_until_disconnected()
