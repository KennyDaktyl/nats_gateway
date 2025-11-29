subscriptions: dict[str, set] = {}
clients = set()

def add_subscription(uuid: str, ws):
    subscriptions.setdefault(uuid, set()).add(ws)

def remove_ws(ws):
    for subs in subscriptions.values():
        subs.discard(ws)
    clients.discard(ws)

def get_subscribers(uuid: str):
    return subscriptions.get(uuid, set())
