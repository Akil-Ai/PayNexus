"""Payment service: creates payments and drives the state machine."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger, correlation_id_var
from app.core.metrics import payments_total, payment_amount_total
from app.domain.state_machine import validate_transition, StateMachineError
from app.models import (
    Payment, PaymentState, PaymentStateHistory, OutboxEvent,
    LedgerAccount, LedgerEntry, Hold, Fee,
)
from app.services.audit_service import write_audit_entry

logger = get_logger(__name__)


def generate_payment_reference() -> str:
    """Generate human-readable payment reference."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    uid = uuid.uuid4().hex[:8].upper()
    return f"PNX-{ts}-{uid}"


async def create_payment(
    db: AsyncSession,
    *,
    customer_id: str,
    amount_minor: int,
    currency: str,
    beneficiary_id: Optional[str] = None,
    sender_account_id: Optional[str] = None,
    payment_type: str = "CREDIT_TRANSFER",
    urgency: str = "NORMAL",
    description: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    actor_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Payment:
    """Create a new payment in CREATED state."""
    reference = generate_payment_reference()
    cid = correlation_id or correlation_id_var.get() or str(uuid.uuid4())

    payment = Payment(
        id=str(uuid.uuid4()),
        reference=reference,
        idempotency_key=idempotency_key,
        customer_id=customer_id,
        beneficiary_id=beneficiary_id,
        sender_account_id=sender_account_id,
        amount_minor=amount_minor,
        currency=currency.upper(),
        payment_type=payment_type,
        urgency=urgency,
        description=description,
        state=PaymentState.CREATED,
        version=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(payment)

    # State history
    history = PaymentStateHistory(
        payment_id=payment.id,
        from_state=None,
        to_state=PaymentState.CREATED,
        actor_id=actor_id,
        actor_type="USER" if actor_id else "SYSTEM",
        reason="Payment created",
        correlation_id=cid,
    )
    db.add(history)

    # Outbox event
    outbox = OutboxEvent(
        aggregate_type="PAYMENT",
        aggregate_id=payment.id,
        event_type="PAYMENT_CREATED",
        payload={
            "payment_id": payment.id,
            "reference": reference,
            "customer_id": customer_id,
            "amount_minor": amount_minor,
            "currency": currency,
            "urgency": urgency,
            "correlation_id": cid,
        },
    )
    db.add(outbox)

    await db.flush()

    # Metrics
    payments_total.labels(currency=currency, rail="none", state="CREATED").inc()
    payment_amount_total.labels(currency=currency).inc(amount_minor)

    # Audit
    await write_audit_entry(
        db,
        entity_type="PAYMENT",
        entity_id=payment.id,
        action="PAYMENT_CREATED",
        actor_id=actor_id,
        actor_type="USER" if actor_id else "SYSTEM",
        correlation_id=cid,
        new_values={
            "reference": reference,
            "amount_minor": amount_minor,
            "currency": currency,
            "state": PaymentState.CREATED.value,
        },
    )

    logger.info("Payment created", extra={
        "payment_id": payment.id,
        "reference": reference,
        "amount_minor": amount_minor,
        "currency": currency,
    })
    return payment


async def transition_payment_state(
    db: AsyncSession,
    payment: Payment,
    new_state: PaymentState,
    *,
    actor_id: Optional[str] = None,
    actor: Optional[str] = None,
    actor_type: str = "SYSTEM",
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Payment:
    """
    Transition payment to new state with optimistic locking.
    Raises StateMachineError for illegal transitions.
    Raises StaleDataError if version conflict detected.
    """
    actor_id = actor_id or actor
    validate_transition(payment.state, new_state)
    cid = correlation_id or correlation_id_var.get() or str(uuid.uuid4())
    old_state = payment.state

    # Optimistic locking: update only if version matches
    result = await db.execute(
        update(Payment)
        .where(Payment.id == payment.id, Payment.version == payment.version)
        .values(
            state=new_state,
            version=Payment.version + 1,
            updated_at=datetime.now(timezone.utc),
        )
        .returning(Payment.version)
    )
    updated = result.scalar_one_or_none()
    if updated is None:
        raise ValueError(
            f"Optimistic locking conflict on payment {payment.id}: "
            "version mismatch, please retry"
        )

    payment.state = new_state
    payment.version = updated

    # Special state field updates
    if new_state == PaymentState.SUBMITTED:
        payment.submitted_at = datetime.now(timezone.utc)
    elif new_state == PaymentState.SETTLED:
        payment.settled_at = datetime.now(timezone.utc)

    # State history
    history = PaymentStateHistory(
        payment_id=payment.id,
        from_state=old_state,
        to_state=new_state,
        actor_id=actor_id,
        actor_type=actor_type,
        reason=reason,
        correlation_id=cid,
        metadata=metadata,
    )
    db.add(history)

    # Outbox event
    outbox = OutboxEvent(
        aggregate_type="PAYMENT",
        aggregate_id=payment.id,
        event_type=f"PAYMENT_{new_state.value}",
        payload={
            "payment_id": payment.id,
            "reference": payment.reference,
            "from_state": old_state.value,
            "to_state": new_state.value,
            "reason": reason,
            "correlation_id": cid,
        },
    )
    db.add(outbox)

    # Audit
    await write_audit_entry(
        db,
        entity_type="PAYMENT",
        entity_id=payment.id,
        action=f"STATE_TRANSITION_{old_state.value}_TO_{new_state.value}",
        actor_id=actor_id,
        actor_type=actor_type,
        correlation_id=cid,
        old_values={"state": old_state.value, "version": payment.version - 1},
        new_values={"state": new_state.value, "version": payment.version},
    )

    # Metrics
    payments_total.labels(
        currency=payment.currency,
        rail=payment.rail_id or "none",
        state=new_state.value,
    ).inc()

    logger.info(
        "Payment state transition",
        extra={
            "payment_id": payment.id,
            "from_state": old_state.value,
            "to_state": new_state.value,
            "actor_id": actor_id,
            "reason": reason,
        },
    )
    return payment


async def get_payment_by_id(db: AsyncSession, payment_id: str) -> Optional[Payment]:
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()


async def get_payment_by_reference(db: AsyncSession, reference: str) -> Optional[Payment]:
    result = await db.execute(
        select(Payment).where(Payment.reference == reference)
    )
    return result.scalar_one_or_none()


async def place_hold(
    db: AsyncSession,
    payment: Payment,
    ledger_account_id: str,
) -> Hold:
    """Place a hold (authorization) on the customer's ledger account."""
    hold = Hold(
        payment_id=payment.id,
        ledger_account_id=ledger_account_id,
        amount_minor=payment.amount_minor + payment.fee_minor,
        currency=payment.currency,
    )
    db.add(hold)

    # Get suspense account
    suspense = await _get_system_ledger_account(db, f"SUSPENSE_{payment.currency}")
    if suspense:
        entry = LedgerEntry(
            payment_id=payment.id,
            debit_account_id=ledger_account_id,
            credit_account_id=suspense.id,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            entry_type="HOLD",
            description=f"Authorization hold for payment {payment.reference}",
        )
        db.add(entry)

    await db.flush()
    return hold


async def settle_ledger(
    db: AsyncSession,
    payment: Payment,
    customer_ledger_account_id: str,
) -> None:
    """Post final settlement ledger entries."""
    # Get accounts
    suspense = await _get_system_ledger_account(db, f"SUSPENSE_{payment.currency}")
    revenue = await _get_system_ledger_account(db, f"REVENUE_{payment.currency}")
    beneficiary_la = await _get_or_create_transit_account(db, payment.currency)

    if suspense and beneficiary_la:
        # Main transfer: suspense -> beneficiary transit
        entry = LedgerEntry(
            payment_id=payment.id,
            debit_account_id=suspense.id,
            credit_account_id=beneficiary_la.id,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            entry_type="SETTLE",
            description=f"Settlement for payment {payment.reference}",
        )
        db.add(entry)

    if payment.fee_minor > 0 and suspense and revenue:
        # Fee entry: suspense -> revenue
        fee_entry = LedgerEntry(
            payment_id=payment.id,
            debit_account_id=suspense.id,
            credit_account_id=revenue.id,
            amount_minor=payment.fee_minor,
            currency=payment.currency,
            entry_type="FEE",
            description=f"Fee for payment {payment.reference}",
        )
        db.add(fee_entry)
        db.add(Fee(
            payment_id=payment.id,
            fee_type="SERVICE_FEE",
            amount_minor=payment.fee_minor,
            currency=payment.currency,
        ))

    # Release hold
    await db.execute(
        update(Hold)
        .where(Hold.payment_id == payment.id, Hold.is_released == False)
        .values(is_released=True, released_at=datetime.now(timezone.utc))
    )

    payment.amount_settled_minor = payment.amount_minor
    await db.flush()


async def reverse_ledger(
    db: AsyncSession,
    payment: Payment,
    reason: str,
) -> None:
    """Post compensating entries to reverse/refund a payment."""
    suspense = await _get_system_ledger_account(db, f"SUSPENSE_{payment.currency}")
    beneficiary_la = await _get_or_create_transit_account(db, payment.currency)
    customer_la = await _get_customer_ledger_account(db, payment)

    if suspense and beneficiary_la and customer_la:
        # Reverse: beneficiary transit -> customer
        entry = LedgerEntry(
            payment_id=payment.id,
            debit_account_id=beneficiary_la.id,
            credit_account_id=customer_la.id,
            amount_minor=payment.amount_settled_minor or payment.amount_minor,
            currency=payment.currency,
            entry_type="REVERSE",
            description=f"Reversal: {reason}",
        )
        db.add(entry)

    # Also release any remaining holds
    await db.execute(
        update(Hold)
        .where(Hold.payment_id == payment.id, Hold.is_released == False)
        .values(is_released=True, released_at=datetime.now(timezone.utc))
    )
    await db.flush()


async def _get_system_ledger_account(db: AsyncSession, name: str) -> Optional[LedgerAccount]:
    result = await db.execute(
        select(LedgerAccount).where(LedgerAccount.name == name, LedgerAccount.is_system == True)
    )
    return result.scalar_one_or_none()


async def _get_or_create_transit_account(db: AsyncSession, currency: str) -> Optional[LedgerAccount]:
    name = f"TRANSIT_{currency}"
    result = await db.execute(
        select(LedgerAccount).where(LedgerAccount.name == name)
    )
    acct = result.scalar_one_or_none()
    if not acct:
        acct = LedgerAccount(
            name=name,
            account_type="LIABILITY",
            currency=currency,
            is_system=True,
        )
        db.add(acct)
        await db.flush()
    return acct


async def _get_customer_ledger_account(db: AsyncSession, payment: Payment) -> Optional[LedgerAccount]:
    if not payment.sender_account_id:
        return None
    result = await db.execute(
        select(LedgerAccount).where(LedgerAccount.account_id == payment.sender_account_id)
    )
    return result.scalar_one_or_none()
