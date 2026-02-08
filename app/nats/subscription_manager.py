import asyncio
from app.core.logging import logger

class NatsSubscriptionManager:
    def __init__(self, nc, on_message_cb):
        self._nc = nc
        self._on_message_cb = on_message_cb
        self._subs = {}
        self._lock = asyncio.Lock()

    async def start(self, subject: str):
        async with self._lock:
            if subject in self._subs:
                return

            logger.info(f"[nats] subscribe {subject}")
            sub = await self._nc.subscribe(subject, cb=self._on_message_cb)
            self._subs[subject] = sub

    async def stop(self, subject: str):
        async with self._lock:
            sub = self._subs.pop(subject, None)
            if not sub:
                return

            logger.info(f"[nats] unsubscribe {subject}")
            await sub.unsubscribe()
