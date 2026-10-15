"""Payments API router: CRUD, state transitions, batch, cancel, refund."""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Query, UploadFile, File
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_roles
from app.core.logging import get_logger, correlation_id_var
from app.core.redis_client import get_redis, PAYMENT_STREAM
from app.db.database import get_db
from app.domain.state_machine import StateMachineError, validate_transition
from app.models import (
    Payment, PaymentState, User, UserRole, Customer,
    Beneficiary, Account, Rail, PaymentStateHistory,
    ScreeningResultRecord, FraudDecisionRecord, LedgerEntry, OutboxEvent,
)
from app.services.idempotency_service import (
    check_idempotency, acquire_idempotency_lock,
    store_idempotency_response, release_idempotency_lock,
    compute_request_hash, IdempotencyConflict, IdempotencyInProgress,
)
from app.services.payment_service import create_payment, get_payment_by_id

router = APIRouter(prefix="/payments", tags=["payments"])
logger = get_logger(__name__)


# ── Request / Response Schemas ─────────────────────────────────────────────────

class CreatePaymentRequest(BaseModel):
    customer_id: str
    beneficiary_id: Optional[str] = None
    sender_account_id: Optional[str] = None
    amount_minor: int = Field(..., gt=0, description="Amount in minor currency units (e.g., paise for INR)")
    currency: str = Field(..., min_length=3, max_length=3)
    payment_type: str = Field("CREDIT_TRANSFER", pattern="^(CREDIT_TRANSFER|DEBIT|REFUND)$")
    urgency: str = Field("NORMAL", pattern="^(INSTANT|NORMAL|BULK)$")
    description: Optional[str] = Field(None, max_length=500)
    end_to_end_id: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, v: str) -> str:
        return v.upper()


class PaymentResponse(BaseModel):
    id: str
    reference: str
    state: str
    amount_minor: int
    currency: str
    fee_minor: int
    customer_id: str
    beneficiary_id: Optional[str]
    rail_id: Optional[str]
    payment_type: str
    urgency: str
    description: Optional[str]
    fraud_decision: Optional[str]
    fraud_score: Optional[int]
    screening_status: Optional[str]
    created_at: datetime
    updated_at: datetime
    settled_at: Optional[datetime]

    class Config:
        from_attributes = True


class CancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class RefundRequest(BaseModel):
    amount_minor: Optional[int] = Field(None, gt=0, description="Partial refund amount; omit for full refund")
    reason: str = Field(..., min_length=1)


def _payment_to_dict(p: Payment) -> dict:
    return {
        "id": p.id,
        "reference": p.reference,
        "state": p.state.value,
        "amount_minor": p.amount_minor,
        "currency": p.currency,
        "fee_minor": p.fee_minor,
        "customer_id": p.customer_id,
        "beneficiary_id": p.beneficiary_id,
        "rail_id": p.rail_id,
        "payment_type": p.payment_type,
        "urgency": p.urgency,
        "description": p.description,
        "fraud_decision": p.fraud_decision.value if p.fraud_decision else None,
        "fraud_score": p.fraud_score,
        "screening_status": p.screening_status.value if p.screening_status else None,
        "rail_reference": p.rail_reference,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "settled_at": p.settled_at.isoformat() if p.settled_at else None,
        "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
        "version": p.version,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_payment_endpoint(
    body: CreatePaymentRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new payment. Requires Idempotency-Key header."""
    if not idempotency_key:
        raise HTTPException(status_code=422, detail="Idempotency-Key header is required")

    raw_body = await request.body()
    request_hash = compute_request_hash(raw_body)
    endpoint = "POST:/api/v1/payments"
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    correlation_id_var.set(correlation_id)

    # Check idempotency
    try:
        existing = await check_idempotency(db, idempotency_key, endpoint, request_hash)
        if existing and existing.replayed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content=existing.response_body,
                status_code=existing.response_status,
                headers={"Idempotent-Replayed": "true"},
            )
    except IdempotencyConflict as e:
        raise HTTPException(status_code=422, detail=str(e))
    except IdempotencyInProgress:
        raise HTTPException(status_code=409, detail="Request is being processed")

    # Acquire lock
    try:
        await acquire_idempotency_lock(db, idempotency_key, endpoint, request_hash)
    except IdempotencyInProgress:
        raise HTTPException(status_code=409, detail="Concurrent request with same key")

    try:
        # Create payment
        payment = await create_payment(
            db,
            customer_id=body.customer_id,
            amount_minor=body.amount_minor,
            currency=body.currency,
            beneficiary_id=body.beneficiary_id,
            sender_account_id=body.sender_account_id,
            payment_type=body.payment_type,
            urgency=body.urgency,
            description=body.description,
            idempotency_key=idempotency_key,
            actor_id=current_user.id,
            correlation_id=correlation_id,
        )
        await db.commit()

        response_body = _payment_to_dict(payment)
        await store_idempotency_response(
            db, idempotency_key, endpoint, 201, response_body, payment.id
        )
        await db.commit()

        # Publish to stream for orchestrator
        redis = await get_redis()
        import json
        await redis.xadd(PAYMENT_STREAM, {
            "event_type": "PAYMENT_CREATED",
            "payload": json.dumps({"payment_id": payment.id, "correlation_id": correlation_id}),
        })

        from fastapi.responses import JSONResponse
        return JSONResponse(content=response_body, status_code=201,
                          headers={"X-Correlation-ID": correlation_id})

    except Exception as e:
        await db.rollback()
        await release_idempotency_lock(idempotency_key, endpoint)
        logger.error("Payment creation failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {str(e)}")


@router.get("")
async def list_payments(
    state: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List payments with server-side pagination, filters, and search."""
    query = select(Payment)

    if state:
        query = query.where(Payment.state == state)
    if currency:
        query = query.where(Payment.currency == currency.upper())
    if customer_id:
        query = query.where(Payment.customer_id == customer_id)
    if search:
        query = query.where(
            or_(
                Payment.reference.ilike(f"%{search}%"),
                Payment.rail_reference.ilike(f"%{search}%"),
                Payment.description.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    # Sort
    sort_col = getattr(Payment, sort_by, Payment.created_at)
    if sort_dir == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(sort_col)

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    payments = result.scalars().all()

    return {
        "items": [_payment_to_dict(p) for p in payments],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment detail with full timeline."""
    result = await db.execute(
        select(Payment)
        .options(
            selectinload(Payment.state_history),
            selectinload(Payment.screening_results),
            selectinload(Payment.fraud_decisions),
            selectinload(Payment.ledger_entries),
            selectinload(Payment.customer),
            selectinload(Payment.beneficiary),
            selectinload(Payment.rail),
        )
        .where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    response = _payment_to_dict(payment)
    response["timeline"] = [
        {
            "id": h.id,
            "from_state": h.from_state.value if h.from_state else None,
            "to_state": h.to_state.value,
            "actor_id": h.actor_id,
            "actor_type": h.actor_type,
            "reason": h.reason,
            "correlation_id": h.correlation_id,
            "created_at": h.created_at.isoformat(),
        }
        for h in sorted(payment.state_history, key=lambda x: x.created_at)
    ]
    response["screening"] = [
        {
            "screening_type": s.screening_type,
            "subject_type": s.subject_type,
            "subject_name": s.subject_name,
            "result": s.result.value,
            "score": float(s.score) if s.score else None,
            "matched_name": s.matched_name,
        }
        for s in payment.screening_results
    ]
    response["fraud"] = [
        {
            "decision": f.decision.value,
            "total_score": f.total_score,
            "ml_score": float(f.ml_score) if f.ml_score else None,
            "triggered_rules": f.triggered_rules,
            "reasons": f.reasons,
            "allow_threshold": f.allow_threshold,
            "block_threshold": f.block_threshold,
            "created_at": f.created_at.isoformat(),
        }
        for f in payment.fraud_decisions
    ]
    response["ledger_entries"] = [
        {
            "id": e.id,
            "entry_type": e.entry_type,
            "amount_minor": e.amount_minor,
            "currency": e.currency,
            "description": e.description,
            "created_at": e.created_at.isoformat(),
        }
        for e in payment.ledger_entries
    ]
    if payment.customer:
        response["customer"] = {
            "id": payment.customer.id,
            "full_name": payment.customer.full_name,
            "kyc_level": payment.customer.kyc_level.value,
        }
    if payment.beneficiary:
        response["beneficiary"] = {
            "id": payment.beneficiary.id,
            "name": payment.beneficiary.name,
            "account_number_masked": payment.beneficiary.account_number_masked,
        }
    if payment.rail:
        response["rail"] = {
            "id": payment.rail.id,
            "code": payment.rail.code,
            "name": payment.rail.name,
        }
    return response


@router.post("/{payment_id}/cancel")
async def cancel_payment(
    payment_id: str,
    body: CancelRequest,
    current_user: User = Depends(require_roles(
        UserRole.ADMIN, UserRole.OPERATIONS, UserRole.MERCHANT
    )),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a payment."""
    payment = await get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    try:
        validate_transition(payment.state, PaymentState.CANCELLED)
    except StateMachineError as e:
        raise HTTPException(status_code=422, detail=str(e))

    from app.services.payment_service import transition_payment_state
    await transition_payment_state(
        db, payment, PaymentState.CANCELLED,
        actor_id=current_user.id, actor_type="USER", reason=body.reason
    )
    await db.commit()
    return _payment_to_dict(payment)


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: str,
    body: RefundRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(require_roles(
        UserRole.ADMIN, UserRole.OPERATIONS
    )),
    db: AsyncSession = Depends(get_db),
):
    """Refund a settled payment (full or partial)."""
    payment = await get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.state != PaymentState.SETTLED:
        raise HTTPException(status_code=422, detail="Only SETTLED payments can be refunded")

    refund_amount = body.amount_minor or payment.amount_minor
    if refund_amount > payment.amount_minor:
        raise HTTPException(status_code=422, detail="Refund amount exceeds original")

    # Create refund payment
    from app.services.payment_service import create_payment as _create_payment
    is_partial = refund_amount < payment.amount_minor
    new_state = PaymentState.PARTIALLY_REFUNDED if is_partial else PaymentState.REFUNDED

    refund = await _create_payment(
        db,
        customer_id=payment.customer_id,
        amount_minor=refund_amount,
        currency=payment.currency,
        payment_type="REFUND",
        urgency="NORMAL",
        description=f"Refund for {payment.reference}: {body.reason}",
        actor_id=current_user.id,
    )
    refund.parent_payment_id = payment.id
    refund.rail_id = payment.rail_id

    from app.services.payment_service import transition_payment_state
    await transition_payment_state(
        db, payment, new_state,
        actor_id=current_user.id, actor_type="USER",
        reason=f"Refund initiated: {body.reason}"
    )
    payment.refunded_amount_minor = (payment.refunded_amount_minor or 0) + refund_amount

    await db.commit()
    return {
        "refund_payment": _payment_to_dict(refund),
        "original_payment": _payment_to_dict(payment),
    }


@router.get("/{payment_id}/events")
async def get_payment_events(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all outbox events for a payment."""
    result = await db.execute(
        select(OutboxEvent)
        .where(OutboxEvent.aggregate_id == payment_id)
        .order_by(OutboxEvent.created_at)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "payload": e.payload,
            "published": e.published,
            "published_at": e.published_at.isoformat() if e.published_at else None,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/{payment_id}/audit")
async def get_payment_audit(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log entries for a payment."""
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT id, sequence, action, actor_id, actor_type, correlation_id,
                   old_values, new_values, row_hash, created_at
            FROM audit_log
            WHERE entity_type = 'PAYMENT' AND entity_id = :payment_id
            ORDER BY sequence ASC
        """),
        {"payment_id": payment_id}
    )
    rows = result.fetchall()
    return [
        {
            "id": r.id,
            "sequence": r.sequence,
            "action": r.action,
            "actor_id": r.actor_id,
            "actor_type": r.actor_type,
            "correlation_id": r.correlation_id,
            "old_values": r.old_values,
            "new_values": r.new_values,
            "row_hash": r.row_hash,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
