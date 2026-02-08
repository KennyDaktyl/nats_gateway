import asyncio
from app.core.logging import logger

# -------------------------------------------------------------------
# Global state (protected by lock)
# -------------------------------------------------------------------

# subject -> set(ws)
subscribers: dict[str, set] = {}

# ws -> set(subject)
ws_sets: dict = {}

_subs_lock = asyncio.Lock()


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def ws_label(ws) -> str:
    peer = getattr(ws, "remote_address", None)
    if isinstance(peer, tuple) and len(peer) >= 2:
        peer_repr = f"{peer[0]}:{peer[1]}"
    else:
        peer_repr = str(peer) if peer else "unknown"
    return f"ws#{id(ws)}@{peer_repr}"


# -------------------------------------------------------------------
# Subscription management
# -------------------------------------------------------------------

async def add_subscription(subject: str, ws) -> bool:
    """
    Add ws to subject.

    Returns:
        True  -> this ws is the FIRST subscriber for this subject
        False -> subject already had subscribers
    """
    async with _subs_lock:
        subs = subscribers.setdefault(subject, set())
        already = ws in subs
        was_empty = len(subs) == 0

        subs.add(ws)
        ws_sets.setdefault(ws, set()).add(subject)

        logger.info(
            f"[subs] {subject} <- {ws_label(ws)} "
            f"({'already' if already else 'new'}) | total={len(subs)}"
        )

        return was_empty and not already


async def remove_subscription(subject: str, ws) -> bool:
    """
    Remove ws from subject.

    Returns:
        True  -> subject has NO subscribers left
        False -> subject still has subscribers
    """
    async with _subs_lock:
        subs = subscribers.get(subject)
        if not subs or ws not in subs:
            return False

        subs.remove(ws)
        ws_sets.get(ws, set()).discard(subject)

        logger.info(
            f"[subs] {subject} -/-> {ws_label(ws)} | remaining={len(subs)}"
        )

        if not subs:
            subscribers.pop(subject, None)
            logger.info(
                f"[subs] Subject {subject} has no remaining WS subscribers"
            )
            return True

        return False


async def remove_ws(ws):
    """
    Remove websocket from ALL subjects.

    Returns:
        removed_count: int
        emptied_subjects: set[str]
    """
    async with _subs_lock:
        subjects = ws_sets.pop(ws, set())
        emptied_subjects: set[str] = set()

        for subject in subjects:
            subs = subscribers.get(subject)
            if not subs:
                continue

            subs.discard(ws)
            if not subs:
                subscribers.pop(subject, None)
                emptied_subjects.add(subject)

        logger.info(
            f"[subs] {ws_label(ws)} removed from {len(subjects)} subjects"
        )

        return len(subjects), emptied_subjects


# -------------------------------------------------------------------
# Read helpers (SAFE snapshots)
# -------------------------------------------------------------------

async def get_subscribers(subject: str) -> set:
    """
    Returns a SNAPSHOT of WS subscribers for subject.
    """
    async with _subs_lock:
        return set(subscribers.get(subject, set()))


async def get_subscribers_for_ws(ws) -> set[str]:
    """
    Returns a SNAPSHOT of subjects for this WS.
    """
    async with _subs_lock:
        return set(ws_sets.get(ws, set()))


async def subscribers_count(subject: str) -> int:
    """
    Returns number of WS subscribers for subject.
    """
    async with _subs_lock:
        return len(subscribers.get(subject, set()))


# -------------------------------------------------------------------
# WS lifecycle
# -------------------------------------------------------------------

async def register_client(ws):
    """
    Register new WS connection.
    """
    async with _subs_lock:
        ws_sets.setdefault(ws, set())
