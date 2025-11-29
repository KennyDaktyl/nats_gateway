import json
from app.core.logging import logger
from app.ws.subscriptions import add_subscription, remove_ws, clients

async def websocket_handler(ws):
    clients.add(ws)
    logger.info(f"Client connected ({len(clients)} total)")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                action = data.get("action")

                if action == "subscribe":
                    uuid = data["uuid"]
                    add_subscription(uuid, ws)
                    logger.info(f"WS subscribed to Raspberry {uuid}")
                elif action == "subscribe_many":
                    uuids = data["uuids"]
                    for uuid in uuids:
                        add_subscription(uuid, ws)
                    logger.info(f"WS subscribed to MANY: {uuids}")
            except Exception as e:
                logger.warning(f"Bad WS message: {e}")

    finally:
        remove_ws(ws)
        logger.info(f"Client disconnected ({len(clients)} total)")
