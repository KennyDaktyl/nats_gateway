import asyncio
import json
import time

import nats
import websockets

from app.core.config import settings
from app.core.logging import logger

# 🎯 WS subskrypcje: uuid -> set(ws)
subscriptions: dict[str, set] = {}

# opcjonalnie można trzymać pełną listę klientów
clients = set()

# do watchdog
last_seen: dict[str, float] = {}
raspberry_status: dict[str, str] = {}


# ============================================================
#   🔵 WebSocket: użytkownik subskrybuje Raspberry po uuid
# ============================================================
async def websocket_handler(ws):
    clients.add(ws)
    logger.info(f"Client connected ({len(clients)} total)")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                action = data.get("action")

                # 🔹 SUB: pojedynczy uuid
                if action == "subscribe":
                    uuid = data.get("uuid")
                    if uuid:
                        subscriptions.setdefault(uuid, set()).add(ws)
                        logger.info(f"WS subscribed to Raspberry {uuid}")
                    continue

                # 🔹 SUB: lista uuid użytkownika
                if action == "subscribe_many":
                    uuids = data.get("uuids", [])
                    for uuid in uuids:
                        subscriptions.setdefault(uuid, set()).add(ws)
                    logger.info(f"WS subscribed to Raspberry list: {uuids}")
                    continue

            except Exception as e:
                logger.warning(f"Bad WS message: {e}")

    finally:
        # wyczyść WS ze wszystkich subskrypcji
        for subs in subscriptions.values():
            subs.discard(ws)
        clients.discard(ws)
        logger.info(f"Client disconnected ({len(clients)} total)")


# ============================================================
#   📨 Wysyłanie wiadomości TYLKO do subskrybentów danego uuid
# ============================================================
async def send_to_subscribers(uuid: str, payload: dict):
    if uuid not in subscriptions:
        return

    msg = json.dumps(payload)
    dead = []

    for ws in list(subscriptions[uuid]):
        try:
            await ws.send(msg)
        except Exception:
            dead.append(ws)

    # usuń martwe połączenia
    for ws in dead:
        subscriptions[uuid].discard(ws)


# ============================================================
#   🔆 Obsługa inverter.*.production
# ============================================================
async def handle_inverter_message(msg):
    try:
        data = json.loads(msg.data.decode())
        serial = data.get("serial_number")

        if not serial:
            return

        logger.info(f"[NATS] inverter update for {serial}: {data}")

        # tutaj też możesz używać send_to_subscribers(serial), jeśli UI subskrybuje po serialu
        # ale to inny temat
    except Exception as e:
        logger.error(f"NATS message error: {e}")


# ============================================================
#   💓 Heartbeat Raspberry Pi
# ============================================================
async def handle_heartbeat_message(msg):
    try:
        data = json.loads(msg.data.decode())
        uuid = data.get("uuid")
        timestamp = data.get("timestamp", int(time.time()))

        if not uuid:
            logger.warning("Received heartbeat without UUID")
            return

        # Zapisz ostatni czas kontaktu
        last_seen[uuid] = time.time()

        # status online
        was_status = raspberry_status.get(uuid)
        if was_status != "online":
            logger.info(f"🔵 Raspberry {uuid} is now ONLINE")

        raspberry_status[uuid] = "online"

        payload = {
            "type": "raspberry_heartbeat",
            "data": {
                **data,               # pełne dane: gpio, devices, free_slots
                "status": "online",
                "timestamp": timestamp
            },
        }

        logger.info(f"💓 Heartbeat from {uuid}: {data}")

        # WYŚLIJ TYLKO do subskrybentów tego UUID
        await send_to_subscribers(uuid, payload)

    except Exception as e:
        logger.error(f"Failed to handle heartbeat message: {e}")


# ============================================================
#   🔴 Watchdog: oznacza offline po 60s
# ============================================================
async def watchdog_offline_checker():
    while True:
        now = time.time()

        offline = [
            uuid for uuid, ts in last_seen.items()
            if now - ts > 60
        ]

        for uuid in offline:
            was_status = raspberry_status.get(uuid)

            if was_status != "offline":
                logger.warning(f"🔴 Raspberry {uuid} went OFFLINE")

            raspberry_status[uuid] = "offline"

            payload = {
                "type": "raspberry_heartbeat",
                "data": {
                    "uuid": uuid,
                    "status": "offline",
                    "timestamp": int(time.time()),
                },
            }

            # WYŚLIJ TYLKO do subskrybentów
            await send_to_subscribers(uuid, payload)

            del last_seen[uuid]

        await asyncio.sleep(10)


# ============================================================
#   🚀 Start Gateway
# ============================================================
async def start_gateway():
    logger.info("Starting NATS Gateway...")

    nc = await nats.connect(settings.NATS_URL)

    await nc.subscribe("inverter.*.production", cb=handle_inverter_message)

    # agent wysyła: raspberry.<uuid>.heartbeat
    await nc.subscribe("raspberry.*.heartbeat", cb=handle_heartbeat_message)

    logger.info("✅ Subscribed to inverter.*.production and raspberry.*.heartbeat")

    await websockets.serve(websocket_handler, "0.0.0.0", 8765)
    logger.info("🌐 WebSocket server ready on ws://0.0.0.0:8765")

    # watchdog offline
    asyncio.create_task(watchdog_offline_checker())

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(start_gateway())
