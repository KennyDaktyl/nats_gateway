# app/nats/publisher.py
import json
from app.core.logging import logger

_nats_client = None


def set_nats_client(nc):
    """
    Attach NATS Core client for publishing control events.
    """
    global _nats_client
    _nats_client = nc
    logger.info("NATS client attached to publisher")


async def publish_event(subject: str, action: str, data: dict | None = None):
    if not _nats_client:
        logger.error(
            f"Cannot publish event '{action}' for {subject}: "
            f"NATS client is not set"
        )
        return

    payload = {
        "subject": subject,
        "action": action,
        "data": data or {},
    }

    try:
        await _nats_client.publish(
            f"control.{subject}",
            json.dumps(payload).encode(),
        )
        logger.info(
            f"Published control event '{action}' for {subject}"
        )
    except Exception as e:
        logger.exception(
            f"Failed to publish control event '{action}' for {subject}: {e}"
        )
