import json
from app.ws.subscriptions import get_subscribers


async def send_to_subscribers(uuid: str, payload: dict):
    subs = get_subscribers(uuid)
    if not subs:
        return

    msg = json.dumps(payload)
    dead = []

    for ws in list(subs):
        try:
            await ws.send(msg)
        except:
            dead.append(ws)

    for ws in dead:
        subs.discard(ws)
