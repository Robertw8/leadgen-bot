import asyncio

from app.services.queue import EventQueue
from app.services.telegram_client import TelegramIngest


async def main() -> None:
    queue = EventQueue()
    ing = TelegramIngest(queue)
    await ing.run()


if __name__ == '__main__':
    asyncio.run(main())
