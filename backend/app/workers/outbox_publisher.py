"""Transactional Outbox Publisher worker.
Periodically queries unpublished outbox_events from PostgreSQL and publishes them to Redis Streams.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.redis_client import get_redis, PAYMENT_STREAM
from app.db.database import AsyncSessionLocal
from app.models import OutboxEvent

logger = get_logger(__name__)
settings = get_settings()


async def publish_outbox_batch():
    """Fetches unpublished events and pushes them to Redis Streams."""
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(OutboxEvent).where(
                OutboxEvent.published == False
            ).order_by(OutboxEvent.created_at.asc()).limit(100)

            res = await db.execute(stmt)
            events = res.scalars().all()

            if not events:
                return 0

            redis = await get_redis()
            published_ids = []

            for event in events:
                payload_data = event.payload or {}
                if isinstance(payload_data, dict):
                    stream_data = {
                        "event_id": event.id,
                        "event_type": event.event_type,
                        "aggregate_type": event.aggregate_type,
                        "aggregate_id": event.aggregate_id,
                        "payload": json.dumps(payload_data),
                        "created_at": event.created_at.isoformat() if event.created_at else ""
                    }
                else:
                    stream_data = {
                        "event_id": event.id,
                        "event_type": event.event_type,
                        "aggregate_type": event.aggregate_type,
                        "aggregate_id": event.aggregate_id,
                        "payload": str(payload_data)
                    }

                await redis.xadd(PAYMENT_STREAM, stream_data)
                event.published = True
                event.published_at = datetime.now(timezone.utc)
                published_ids.append(event.id)

            await db.commit()
            return len(published_ids)
        except Exception as exc:
            logger.error(f"Outbox publisher loop error: {exc}", exc_info=True)
            await db.rollback()
            return 0


async def main():
    setup_logging()
    logger.info("Outbox Publisher worker started.")
    poll_interval = 0.5  # 500ms

    while True:
        try:
            count = await publish_outbox_batch()
            if count == 0:
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            logger.info("Outbox publisher stopping...")
            break
        except Exception as err:
            logger.error(f"Unexpected error in outbox worker: {err}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
