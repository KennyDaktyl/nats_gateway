import json
import asyncio

from app.ws.subscriptions import (
    get_subscribers,
    ws_label,
)
from app.core.logging import logger


SEND_TIMEOUT = 1.0  # seconds


async def _send_one(ws, msg: str, subject: str) -> bool:
    """
    Send message to single WS client.

    Returns:
        True  -> delivered
        False -> failed / timeout
    """
    try:
        await asyncio.wait_for(ws.send(msg), timeout=SEND_TIMEOUT)
        return True
    except asyncio.TimeoutError:
        logger.warning(
            f"WS send timeout to {ws_label(ws)} for subject {subject}"
        )
    except Exception as e:
        logger.warning(
            f"WS send failed to {ws_label(ws)} "
            f"for subject {subject}: {e}"
        )
    return False


async def send_to_subscribers(subject: str, data: dict):
    # ---------------------------------------------------------
    # Snapshot subscribers (SAFE)
    # ---------------------------------------------------------
    subs = await get_subscribers(subject)
    if not subs:
        logger.debug(f"No WS subscribers for subject {subject}")
        return

    msg = json.dumps(data)

    logger.info(
        f"Sending event for subject {subject} "
        f"to {len(subs)} WS client(s): "
        f"{[ws_label(ws) for ws in subs]}"
    )

    # ---------------------------------------------------------
    # Fan-out PARALLEL (isolated clients)
    # ---------------------------------------------------------
    tasks = [
        _send_one(ws, msg, subject)
        for ws in subs
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=False,
    )

    delivered = sum(1 for r in results if r)

    logger.info(
        f"Sent event for subject {subject} "
        f"to {delivered}/{len(subs)} WS subscriber(s)"
    )
