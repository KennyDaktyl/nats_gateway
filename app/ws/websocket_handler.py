import json
from app.core.logging import logger

from app.ws.subscriptions import (
    add_subscription,
    remove_subscription,
    get_subscribers_for_ws,
    remove_ws,
    register_client,
    ws_label,
)

from app.nats.publisher import publish_event


async def websocket_handler(ws, nats_manager):
    # ---------------------------------------------------------
    # Register WS connection
    # ---------------------------------------------------------
    await register_client(ws)
    logger.info(f"Client connected {ws_label(ws)}")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                action = data.get("action")

                # =================================================
                # SINGLE SUBSCRIBE
                # =================================================
                if action == "subscribe":
                    subject = data.get("subject")
                    if not subject:
                        logger.warning(
                            f"{ws_label(ws)} subscribe without subject"
                        )
                        continue

                    is_first = await add_subscription(subject, ws)

                    # 🔥 KLUCZOWA POPRAWKA
                    if is_first:
                        await nats_manager.start(subject)     # REALNY START
                        await publish_event(subject, "start") # EVENT INFO

                    logger.info(
                        f"{ws_label(ws)} subscribed to {subject}"
                    )

                # =================================================
                # SUBSCRIBE MANY (FULL REPLACE – SOURCE OF TRUTH)
                # =================================================
                elif action == "subscribe_many":
                    subjects = set(data.get("subjects", []))
                    current = await get_subscribers_for_ws(ws)

                    # -----------------------------
                    # Unsubscribe removed subjects
                    # -----------------------------
                    for subject in current - subjects:
                        emptied = await remove_subscription(subject, ws)
                        if emptied:
                            await nats_manager.stop(subject)   # REAL STOP
                            await publish_event(subject, "stop")

                    # -----------------------------
                    # Subscribe new subjects
                    # -----------------------------
                    for subject in subjects - current:
                        is_first = await add_subscription(subject, ws)
                        if is_first:
                            await nats_manager.start(subject)
                            await publish_event(subject, "start")

                    logger.info(
                        f"{ws_label(ws)} subscribe_many -> {list(subjects)}"
                    )

                # =================================================
                # UNSUBSCRIBE MANY (EXPLICIT)
                # =================================================
                elif action == "unsubscribe_many":
                    subjects = set(data.get("subjects", []))

                    for subject in subjects:
                        emptied = await remove_subscription(subject, ws)
                        if emptied:
                            await nats_manager.stop(subject)
                            await publish_event(subject, "stop")

                    logger.info(
                        f"{ws_label(ws)} unsubscribe_many -> {list(subjects)}"
                    )

                # =================================================
                # UNKNOWN ACTION
                # =================================================
                else:
                    logger.warning(
                        f"{ws_label(ws)} unknown action: {action}"
                    )

            except json.JSONDecodeError:
                logger.warning(
                    f"Invalid JSON from {ws_label(ws)}: {raw}"
                )
            except Exception as e:
                logger.exception(
                    f"Bad WS message from {ws_label(ws)}: {e}"
                )

    finally:
        # ---------------------------------------------------------
        # Cleanup WS on disconnect
        # ---------------------------------------------------------
        removed_count, emptied_subjects = await remove_ws(ws)

        for subject in emptied_subjects:
            await nats_manager.stop(subject)   # 🔥 REAL STOP
            await publish_event(subject, "stop")

        logger.info(
            f"Client disconnected {ws_label(ws)}, "
            f"removed from {removed_count} subjects"
        )
