import asyncio

import structlog

from app.db.session import SessionLocal
from app.pipeline.engine import PipelineEngine
from app.services.llm_router import LLMRouter
from app.services.queue import EventQueue
from app.services.repositories import LeadRepo, MemoryRepo, MessageRepo, PlaybookRepo

log = structlog.get_logger(__name__)


async def run_worker() -> None:
    queue = EventQueue()
    llm = LLMRouter()

    while True:
        event = queue.pop(timeout=5)
        if not event:
            await asyncio.sleep(0.2)
            continue

        db = SessionLocal()
        try:
            engine = PipelineEngine(
                msg_repo=MessageRepo(db),
                lead_repo=LeadRepo(db),
                memory_repo=MemoryRepo(db),
                playbook_repo=PlaybookRepo(db),
                llm=llm,
            )
            result = await engine.process(event)
            log.info('processed', event=event.__dict__, result=result)
        except Exception as exc:
            log.exception('worker_failed', error=str(exc), event=event.__dict__)
        finally:
            db.close()


if __name__ == '__main__':
    asyncio.run(run_worker())
