"""Idempotency service: Redis SETNX lock + DB unique constraint as final arbiter."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis_client import get_redis
from app.core.logging import get_logger
from app.core.metrics import idempotency_replays_total, idempotency_conflicts_total
from app.models import IdempotencyKey

settings = get_settings()
logger = get_logger(__name__)

LOCK_PREFIX = "idempotency:lock:"
LOCK_TTL = settings.idempotency_lock_timeout_seconds
KEY_TTL = settings.idempotency_ttl_seconds


def compute_request_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


class IdempotencyConflict(Exception):
    """Same key, different body."""
    pass


class IdempotencyInProgress(Exception):
    """Concurrent identical request is being processed."""
    pass


class IdempotencyResult:
    def __init__(self, replayed: bool, response_status: int, response_body: dict):
        self.replayed = replayed
        self.response_status = response_status
        self.response_body = response_body


async def check_idempotency(
    db: AsyncSession,
    key: str,
    endpoint: str,
    request_hash: str,
) -> Optional[IdempotencyResult]:
    """
    Check if this idempotency key has been seen before.
    Returns IdempotencyResult if already processed, None if new request.
    Raises IdempotencyConflict or IdempotencyInProgress as appropriate.
    """
    # 1. Check Redis lock (in-flight indicator)
    redis = await get_redis()
    lock_key = f"{LOCK_PREFIX}{key}:{endpoint}"

    # 2. Check DB for completed response
    result = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.key == key,
            IdempotencyKey.endpoint == endpoint,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Check hash matches
        if existing.request_hash != request_hash:
            idempotency_conflicts_total.inc()
            raise IdempotencyConflict(
                f"Idempotency key '{key}' was previously used with a different request body."
            )
        # Check not expired
        if existing.expires_at < datetime.now(timezone.utc):
            return None  # Expired, treat as new
        # Return cached response
        if existing.response_body is not None:
            idempotency_replays_total.inc()
            return IdempotencyResult(
                replayed=True,
                response_status=existing.response_status or 200,
                response_body=existing.response_body,
            )
        # Key exists but no response yet (in-flight in DB)
        raise IdempotencyInProgress("Request is being processed.")

    # 3. Check Redis lock for in-flight
    lock_value = await redis.get(lock_key)
    if lock_value:
        raise IdempotencyInProgress("Concurrent request with same key is being processed.")

    return None  # New request


async def acquire_idempotency_lock(
    db: AsyncSession,
    key: str,
    endpoint: str,
    request_hash: str,
) -> bool:
    """
    Acquire Redis lock and insert DB record for in-flight tracking.
    Returns True if lock acquired (this request should proceed).
    """
    redis = await get_redis()
    lock_key = f"{LOCK_PREFIX}{key}:{endpoint}"

    # SETNX with TTL
    acquired = await redis.set(lock_key, "1", ex=LOCK_TTL, nx=True)
    if not acquired:
        raise IdempotencyInProgress("Concurrent request with same key is being processed.")

    # Insert placeholder in DB (unique constraint as final arbiter)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=KEY_TTL)
    try:
        idem_record = IdempotencyKey(
            key=key,
            request_hash=request_hash,
            endpoint=endpoint,
            expires_at=expires_at,
        )
        db.add(idem_record)
        await db.flush()  # Will raise IntegrityError if duplicate
    except IntegrityError:
        await db.rollback()
        # Race condition: another request won the DB constraint
        # Release our Redis lock too
        await redis.delete(lock_key)
        raise IdempotencyInProgress("Concurrent request with same key is being processed.")

    return True


async def store_idempotency_response(
    db: AsyncSession,
    key: str,
    endpoint: str,
    response_status: int,
    response_body: dict,
    payment_id: Optional[str] = None,
) -> None:
    """Store the response for future replays."""
    redis = await get_redis()
    lock_key = f"{LOCK_PREFIX}{key}:{endpoint}"

    result = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.key == key,
            IdempotencyKey.endpoint == endpoint,
        )
    )
    record = result.scalar_one_or_none()
    if record:
        record.response_status = response_status
        record.response_body = response_body
        record.payment_id = payment_id
        await db.flush()

    # Release Redis lock
    await redis.delete(lock_key)


async def release_idempotency_lock(key: str, endpoint: str) -> None:
    """Release lock on failure/error (so retries can proceed)."""
    redis = await get_redis()
    lock_key = f"{LOCK_PREFIX}{key}:{endpoint}"
    await redis.delete(lock_key)
