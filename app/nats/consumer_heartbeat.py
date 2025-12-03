# app/nats/consumer_heartbeat.py
import json
import time
from app.core.logging import logger
from app.ws.send import send_to_subscribers

last_seen = {}
raspberry_status = {}

async def heartbeat_consumer(sub):
    while True:
        try:
            msgs = await sub.fetch(10, timeout=1)
        except:
            continue

        for msg in msgs:
            try:
                data = json.loads(msg.data.decode())
                uuid = data["uuid"]

                last_seen[uuid] = time.time()
                raspberry_status[uuid] = "online"

                logger.info(f"Heartbeat {uuid}, payload: {data}")

                await send_to_subscribers(uuid, {
                    "type": "raspberry_heartbeat",
                    "data": {**data, "status": "online"}
                })

                await msg.ack()
            except Exception as e:
                logger.error(f"Heartbeat consumer error: {e}")
