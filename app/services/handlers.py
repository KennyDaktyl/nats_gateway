# services/handlers.py
import json

from nats.aio.msg import Msg

from app.core.logging import logger


async def handle_raspberry_message(msg: Msg):
    try:
        data = json.loads(msg.data.decode())
        logger.info(f"Received Raspberry message: {data}")
    except Exception as e:
        logger.error(f"Failed to handle Raspberry message: {e}")


async def handle_inverter_message(msg: Msg):
    data = json.loads(msg.data.decode())
    logger.info(f"🟢 [NATS] Inverter update received: {data}")


async def handle_heartbeat_message(msg: Msg, clients: set):
    try:
        data = json.loads(msg.data.decode())
        uuid = data.get("uuid")
        status = data.get("status", "unknown")
        logger.info(f"Heartbeat from {uuid}: {status}")

        payload = {
            "type": "raspberry_heartbeat",
            "data": {
                "uuid": uuid,
                "status": status,
                "timestamp": data.get("timestamp"),
            },
        }

        msg = json.dumps(payload)
        dead = []
        for ws in clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)
    except Exception as e:
        logger.error(f"Failed to handle heartbeat message: {e}")
