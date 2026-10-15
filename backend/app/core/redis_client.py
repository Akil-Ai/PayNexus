"""Redis client singleton and helper utilities."""
import asyncio
import json
from typing import Any, Optional
import redis.asyncio as redis_async

from app.core.config import get_settings

settings = get_settings()

_redis_client: Optional[redis_async.Redis] = None


async def get_redis() -> redis_async.Redis:
    global _redis_client
    if _redis_client is None:
        try:
            client = redis_async.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            await asyncio.wait_for(client.ping(), timeout=0.8)
            _redis_client = client
        except Exception:
            try:
                import fakeredis.aioredis as fake_async
                _redis_client = fake_async.FakeRedis(decode_responses=True)
            except Exception:
                _redis_client = redis_async.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


# ── Stream helpers ────────────────────────────────────────────────────────────

PAYMENT_STREAM = "payment_events"
DLQ_STREAM = "payment_events_dlq"
CONSUMER_GROUP = "orchestrator"
RECON_GROUP = "reconciliation"


async def publish_event(stream: str, event_type: str, payload: dict) -> str:
    """Publish event to a Redis Stream. Returns stream message ID."""
    r = await get_redis()
    msg_id = await r.xadd(stream, {
        "event_type": event_type,
        "payload": json.dumps(payload),
    })
    return msg_id


async def ensure_consumer_group(stream: str, group: str) -> None:
    """Create consumer group if it doesn't exist."""
    r = await get_redis()
    try:
        await r.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception:
        pass  # Already exists


async def read_group(
    stream: str,
    group: str,
    consumer: str,
    count: int = 10,
    block_ms: int = 2000,
) -> list:
    r = await get_redis()
    return await r.xreadgroup(
        groupname=group,
        consumername=consumer,
        streams={stream: ">"},
        count=count,
        block=block_ms,
    )


async def ack_message(stream: str, group: str, msg_id: str) -> None:
    r = await get_redis()
    await r.xack(stream, group, msg_id)


async def move_to_dlq(stream: str, msg_id: str, payload: dict, reason: str) -> None:
    r = await get_redis()
    await r.xadd(DLQ_STREAM, {
        "original_stream": stream,
        "original_message_id": msg_id,
        "payload": json.dumps(payload),
        "failure_reason": reason,
    })
