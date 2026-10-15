"""Unit tests for idempotency service — hash, conflict, replay, in-progress logic."""
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.services.idempotency_service import (
    compute_request_hash,
    check_idempotency,
    IdempotencyConflict,
    IdempotencyInProgress,
    IdempotencyResult,
)
from app.models import IdempotencyKey


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_idem_key(
    key="idem-key-001",
    endpoint="/api/v1/payments",
    request_hash="abc123",
    response_body=None,
    response_status=200,
    expires_offset_secs=3600,
) -> IdempotencyKey:
    record = IdempotencyKey()
    record.key = key
    record.endpoint = endpoint
    record.request_hash = request_hash
    record.response_body = response_body
    record.response_status = response_status
    record.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_offset_secs)
    return record


# ── compute_request_hash ────────────────────────────────────────────────────────

class TestComputeRequestHash:
    def test_sha256_of_body(self):
        body = b'{"amount": 1000, "currency": "INR"}'
        expected = hashlib.sha256(body).hexdigest()
        assert compute_request_hash(body) == expected

    def test_empty_body(self):
        result = compute_request_hash(b"")
        assert len(result) == 64  # SHA-256 hex digest is always 64 chars

    def test_same_body_same_hash(self):
        body = b'{"key": "value"}'
        assert compute_request_hash(body) == compute_request_hash(body)

    def test_different_body_different_hash(self):
        body1 = b'{"amount": 100}'
        body2 = b'{"amount": 200}'
        assert compute_request_hash(body1) != compute_request_hash(body2)

    def test_hash_is_deterministic(self):
        body = b"idempotency-test-payload"
        results = {compute_request_hash(body) for _ in range(10)}
        assert len(results) == 1  # all identical


# ── check_idempotency ──────────────────────────────────────────────────────────

class TestCheckIdempotency:

    @pytest.mark.asyncio
    async def test_new_request_returns_none(self):
        """Completely new key → should return None (proceed with processing)."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.services.idempotency_service.get_redis", return_value=mock_redis):
            result = await check_idempotency(db, "key-new", "/payments", "hash-abc")
        assert result is None

    @pytest.mark.asyncio
    async def test_replay_cached_response(self):
        """Same key + same hash + valid response in DB → replay."""
        existing = _make_idem_key(
            request_hash="hash-xyz",
            response_body={"id": "pay-001", "state": "SUBMITTED"},
            response_status=201,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: existing))

        mock_redis = AsyncMock()
        with patch("app.services.idempotency_service.get_redis", return_value=mock_redis):
            result = await check_idempotency(db, "idem-key-001", "/api/v1/payments", "hash-xyz")

        assert isinstance(result, IdempotencyResult)
        assert result.replayed is True
        assert result.response_status == 201
        assert result.response_body["id"] == "pay-001"

    @pytest.mark.asyncio
    async def test_conflict_on_different_hash(self):
        """Same key, different body hash → IdempotencyConflict."""
        existing = _make_idem_key(request_hash="original-hash")
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: existing))

        mock_redis = AsyncMock()
        with patch("app.services.idempotency_service.get_redis", return_value=mock_redis):
            with pytest.raises(IdempotencyConflict):
                await check_idempotency(db, "idem-key-001", "/api/v1/payments", "different-hash")

    @pytest.mark.asyncio
    async def test_in_progress_when_redis_locked(self):
        """No DB record but Redis lock exists → IdempotencyInProgress."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"1")  # Lock held

        with patch("app.services.idempotency_service.get_redis", return_value=mock_redis):
            with pytest.raises(IdempotencyInProgress):
                await check_idempotency(db, "key-inflight", "/payments", "hash-abc")

    @pytest.mark.asyncio
    async def test_expired_key_treated_as_new(self):
        """Expired idempotency key in DB → treat as new request (return None)."""
        existing = _make_idem_key(
            request_hash="hash-xyz",
            expires_offset_secs=-10,  # expired 10 seconds ago
            response_body={"id": "pay-old"},
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: existing))

        mock_redis = AsyncMock()
        with patch("app.services.idempotency_service.get_redis", return_value=mock_redis):
            result = await check_idempotency(db, "idem-key-001", "/api/v1/payments", "hash-xyz")

        assert result is None  # expired → new

    @pytest.mark.asyncio
    async def test_in_progress_from_db_no_response(self):
        """DB record exists but no response_body yet (still in-flight) → InProgress."""
        existing = _make_idem_key(
            request_hash="hash-xyz",
            response_body=None,  # No response stored yet
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: existing))

        mock_redis = AsyncMock()
        with patch("app.services.idempotency_service.get_redis", return_value=mock_redis):
            with pytest.raises(IdempotencyInProgress):
                await check_idempotency(db, "idem-key-001", "/api/v1/payments", "hash-xyz")
