"""Webhook service: HMAC-SHA256 payload signing, delivery with retry, and delivery logs."""
import hashlib
import hmac
import json
import time
import uuid
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import WebhookSubscription, WebhookDelivery

logger = get_logger(__name__)


def generate_webhook_signature(secret: str, payload_str: str, timestamp: int) -> str:
    """Generates HMAC-SHA256 signature formatted as t={timestamp},v1={hash}."""
    signed_payload = f"{timestamp}.{payload_str}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


async def deliver_webhook_event(
    db: AsyncSession,
    subscription: WebhookSubscription,
    event_type: str,
    payload: Dict[str, Any]
) -> WebhookDelivery:
    """Delivers event to webhook endpoint with HMAC signature and logs response."""
    now_ts = int(time.time())
    payload_str = json.dumps(payload, default=str)
    signature = generate_webhook_signature(subscription.secret, payload_str, now_ts)

    headers = {
        "Content-Type": "application/json",
        "X-PayNexus-Signature": signature,
        "X-PayNexus-Event": event_type,
        "X-PayNexus-Delivery": str(uuid.uuid4())
    }

    delivery = WebhookDelivery(
        id=str(uuid.uuid4()),
        subscription_id=subscription.id,
        event_type=event_type,
        payload=payload,
        status="PENDING",
        attempt_count=1,
        created_at=datetime.now(timezone.utc)
    )
    db.add(delivery)
    await db.flush()

    status_code = None
    response_body = None
    is_success = False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(subscription.url, content=payload_str, headers=headers)
            status_code = resp.status_code
            response_body = resp.text[:1000]
            is_success = 200 <= status_code < 300
    except Exception as exc:
        response_body = str(exc)[:500]
        logger.warning(f"Webhook delivery failed for {subscription.url}: {exc}")

    delivery.status = "SUCCESS" if is_success else "FAILED"
    delivery.response_status_code = status_code
    delivery.response_body = response_body
    delivery.delivered_at = datetime.now(timezone.utc)
    await db.flush()

    return delivery


async def broadcast_event(
    db: AsyncSession,
    event_type: str,
    payload: Dict[str, Any]
):
    """Broadcasts event to all active matching webhook subscribers."""
    stmt = select(WebhookSubscription).where(
        WebhookSubscription.is_active == True
    )
    res = await db.execute(stmt)
    subscriptions = res.scalars().all()

    for sub in subscriptions:
        sub_events = sub.events or []
        if "*" in sub_events or event_type in sub_events:
            try:
                await deliver_webhook_event(db, sub, event_type, payload)
            except Exception as e:
                logger.error(f"Error delivering webhook: {e}")
