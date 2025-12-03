#app/ws/inverter_subscriptions.py
inverter_subscriptions: dict[str, set] = {}
clients_inverter = set()

def add_inverter_subscription(serial: str, ws):
    inverter_subscriptions.setdefault(serial, set()).add(ws)

def remove_inverter_ws(ws):
    for subs in inverter_subscriptions.values():
        subs.discard(ws)
    clients_inverter.discard(ws)

def get_inverter_subscribers(serial: str):
    return inverter_subscriptions.get(serial, set())
