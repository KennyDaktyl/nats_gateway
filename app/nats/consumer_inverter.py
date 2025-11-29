import json
from app.core.logging import logger


async def inverter_consumer(sub):
    while True:
        try:
            msgs = await sub.fetch(10, timeout=1)
        except:
            continue

        for msg in msgs:
            try:
                data = json.loads(msg.data.decode())
                logger.info(f"[Inverter] Event: {data}")
                await msg.ack()
            except Exception as e:
                logger.error(f"Inverter consumer error: {e}")
