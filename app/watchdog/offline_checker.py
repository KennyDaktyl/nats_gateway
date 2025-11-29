import time
import asyncio
from app.ws.send import send_to_subscribers


async def watchdog(last_seen: dict, raspberry_status: dict):
    while True:
        now = time.time()

        for uuid, ts in list(last_seen.items()):
            if now - ts > 60:
                raspberry_status[uuid] = "offline"

                await send_to_subscribers(uuid, {
                    "type": "raspberry_heartbeat",
                    "data": {
                        "uuid": uuid,
                        "status": "offline",
                        "timestamp": int(time.time())
                    }
                })

                del last_seen[uuid]

        await asyncio.sleep(10)
