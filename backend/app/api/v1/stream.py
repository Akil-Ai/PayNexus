"""Real-time Server-Sent Events (SSE) payment stream."""
import asyncio
import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.core.redis_client import get_redis, PAYMENT_STREAM
from app.core.logging import get_logger

router = APIRouter(prefix="/stream", tags=["stream"])
logger = get_logger(__name__)


@router.get("/payments")
async def stream_payment_events(request: Request):
    """
    Subscribes the frontend client to real-time payment state changes.
    Yields events from Redis Stream or heartbeat ping every 15s.
    """
    async def event_generator():
        redis = await get_redis()
        last_id = "$"  # Only new events

        while True:
            if await request.is_disconnected():
                break

            try:
                # Read from Redis stream with timeout of 2 seconds
                streams = await redis.xread({PAYMENT_STREAM: last_id}, count=10, block=2000)
                if streams:
                    for stream_name, messages in streams:
                        for msg_id, data in messages:
                            last_id = msg_id
                            yield {
                                "event": "payment_update",
                                "id": msg_id,
                                "data": json.dumps(data)
                            }
                else:
                    # Keep-alive heartbeat ping
                    yield {
                        "event": "ping",
                        "data": json.dumps({"timestamp": asyncio.get_event_loop().time()})
                    }
            except Exception as e:
                logger.debug(f"SSE loop error: {e}")
                await asyncio.sleep(2)

    return EventSourceResponse(event_generator())
