from __future__ import annotations

import json

from redis import Redis

from app.core.config import settings
from app.pipeline.types import InboundEvent


class EventQueue:
    def __init__(self) -> None:
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self.key = 'leadgen:inbound'

    def push(self, event: InboundEvent) -> None:
        self.redis.rpush(self.key, json.dumps(event.__dict__, ensure_ascii=False))

    def pop(self, timeout: int = 5) -> InboundEvent | None:
        item = self.redis.blpop(self.key, timeout=timeout)
        if not item:
            return None
        _, payload = item
        data = json.loads(payload)
        return InboundEvent(**data)
