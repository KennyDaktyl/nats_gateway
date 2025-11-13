# app/main.py
import asyncio
import json
import time

import nats
import websockets

from app.core.config import settings
from app.core.logging import logger

subscriptions: dict[str, set] = {}
clients = set()

last_seen: dict[str, float] = {}


async def websocket_handler(ws):
    clients.add(ws)
    logger.info(f"Client connected ({len(clients)} total)")
    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
                if data.get("action") == "subscribe":
                    serial = data.get("serial")
                    if not serial:
                        continue
                    subs = subscriptions.setdefault(serial, set())
                    subs.add(ws)
                    logger.info(f"Client subscribed to {serial}")
            except Exception as e:
                logger.warning(f"Bad websocket message: {e}")
    finally:
        for subs in subscriptions.values():
            subs.discard(ws)
        clients.discard(ws)
        logger.info(f"Client disconnected ({len(clients)} total)")


async def send_to_subscribers(serial: str, payload: dict):
    if serial not in subscriptions:
        return
    dead = []
    msg = json.dumps(payload)
    for ws in list(subscriptions[serial]):
        try:
            await ws.send(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        subscriptions[serial].discard(ws)


async def handle_inverter_message(msg):
    try:
        data = json.loads(msg.data.decode())
        serial = data.get("serial_number")
        if not serial:
            return
        logger.info(f"NATS update for {serial}: {data}")
        await send_to_subscribers(serial, {"type": "inverter_update", "data": data})
    except Exception as e:
        logger.error(f"NATS message error: {e}")


async def handle_heartbeat_message(msg):
    try:
        data = json.loads(msg.data.decode())
        uuid = data.get("uuid")
        status = data.get("status", "unknown")

        last_seen[uuid] = time.time()

        logger.info(f"Heartbeat from {uuid}: {status}")

        payload = {
            "type": "raspberry_heartbeat",
            "data": {
                "uuid": uuid,
                "status": status,
                "timestamp": data.get("timestamp"),
            },
        }

        msg_json = json.dumps(payload)
        dead = []
        for ws in clients:
            try:
                await ws.send(msg_json)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)
    except Exception as e:
        logger.error(f"Failed to handle heartbeat message: {e}")


async def watchdog_offline_checker():
    while True:
        now = time.time()
        offline = [uuid for uuid, ts in last_seen.items() if now - ts > 60]

        for uuid in offline:
            logger.warning(f"Raspberry {uuid} is offline, sending notification")

            payload = {
                "type": "raspberry_heartbeat",
                "data": {"uuid": uuid, "status": "offline"},
            }

            msg_json = json.dumps(payload)
            for ws in list(clients):
                try:
                    await ws.send(msg_json)
                except Exception:
                    pass

            del last_seen[uuid]

        await asyncio.sleep(10)


async def start_gateway():
    logger.info("Starting NATS Gateway...")
    nc = await nats.connect(settings.NATS_URL)

    await nc.subscribe("inverter.*.production", cb=handle_inverter_message)
    await nc.subscribe("raspberry.heartbeat", cb=handle_heartbeat_message)
    logger.info("✅ Subscribed to inverter.*.production and raspberry.heartbeat")

    ws_server = await websockets.serve(websocket_handler, "0.0.0.0", 8765)
    logger.info("🌐 WebSocket server ready on ws://0.0.0.0:8765")

    asyncio.create_task(watchdog_offline_checker())

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(start_gateway())
