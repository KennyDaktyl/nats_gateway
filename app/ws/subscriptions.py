# app/ws/subscriptions.py
raspberry_subs: dict[str, set] = {}
inverter_subs: dict[str, set] = {}

clients = set()


def add_raspberry_subscription(uuid: str, ws):
    raspberry_subs.setdefault(uuid, set()).add(ws)


def add_inverter_subscription(serial: str, ws):
    inverter_subs.setdefault(serial, set()).add(ws)


def remove_inverter_subscription(serial: str, ws):
    if serial in inverter_subs:
        inverter_subs[serial].discard(ws)


def remove_ws(ws):
    for subs in raspberry_subs.values():
        subs.discard(ws)

    for subs in inverter_subs.values():
        subs.discard(ws)

    clients.discard(ws)


def get_raspberry_subscribers(uuid: str):
    return raspberry_subs.get(uuid, set())


def get_inverter_subscribers(serial: str):
    return inverter_subs.get(serial, set())
