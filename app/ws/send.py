#app/ws/send.py
import json
from app.ws.subscriptions import (
    get_raspberry_subscribers,
    get_inverter_subscribers
)


async def send_to_subscribers(uuid: str, payload: dict):
    subs = get_raspberry_subscribers(uuid)
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


async def send_to_inverter_subscribers(serial: str, payload: dict):
    subs = get_inverter_subscribers(serial)
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
