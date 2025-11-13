# services/publisher.py
import json

from app.core.logging import logger


async def publish_message(nc, subject: str, data: dict):
    try:
        await nc.publish(subject, json.dumps(data).encode())
        logger.info(f"Sended message to {subject}: {data}")
    except Exception as e:
        logger.error(f"Failed to publish message to {subject}: {e}")
