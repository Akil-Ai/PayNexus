"""Double-entry ledger service: accounts, entries, holds, settlement, and balance calculation."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, text, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    LedgerAccount, LedgerEntry, LedgerEntryType,
    Payment, Account, Hold, Fee
)

logger = get_logger(__name__)


class LedgerInvariantViolation(Exception):
    """Raised when sum(debits) != sum(credits) for a transaction."""
    pass


class InsufficientFundsError(Exception):
    """Raised when available balance is insufficient for hold or debit."""
    pass


async def get_or_create_ledger_account(
    db: AsyncSession,
    account_number: Optional[str] = None,
    name: str = "Account",
    currency: str = "INR",
    account_type: str = "LIABILITY",
    customer_id: Optional[str] = None,
    account_id: Optional[str] = None,
    is_system: bool = False
) -> LedgerAccount:
    """Finds or initializes a ledger account matching models.py schema."""
    if account_id:
        stmt = select(LedgerAccount).where(LedgerAccount.account_id == account_id)
        res = await db.execute(stmt)
        acc = res.scalar_one_or_none()
        if acc:
            return acc

    stmt = select(LedgerAccount).where(LedgerAccount.name == name)
    res = await db.execute(stmt)
    acc = res.scalar_one_or_none()
    if not acc:
        acc = LedgerAccount(
            id=str(uuid.uuid4()),
            account_id=account_id,
            name=name,
            account_type=account_type if account_type in ("ASSET", "LIABILITY", "INCOME", "EXPENSE") else "LIABILITY",
            currency=currency.upper()[:3],
            is_system=is_system or (account_id is None),
            created_at=datetime.now(timezone.utc)
        )
        db.add(acc)
        await db.flush()
    return acc



async def calculate_account_balance(
    db: AsyncSession,
    ledger_account_id: str
) -> Dict[str, int]:
    """
    Computes posted balance, active holds, and available balance for a ledger account.
    Returns:
        {
            "posted_balance_minor": int,
            "held_balance_minor": int,
            "available_balance_minor": int
        }
    """
    # 1. Total credits and debits from posted entries
    debits_stmt = select(func.coalesce(func.sum(LedgerEntry.amount_minor), 0)).where(
        and_(
            LedgerEntry.ledger_account_id == ledger_account_id,
            LedgerEntry.entry_type == LedgerEntryType.DEBIT
        )
    )
    credits_stmt = select(func.coalesce(func.sum(LedgerEntry.amount_minor), 0)).where(
        and_(
            LedgerEntry.ledger_account_id == ledger_account_id,
            LedgerEntry.entry_type == LedgerEntryType.CREDIT
        )
    )

    debits_res = await db.execute(debits_stmt)
    credits_res = await db.execute(credits_stmt)
    total_debits = debits_res.scalar() or 0
    total_credits = credits_res.scalar() or 0

    # Liability / Customer account convention: credits increase balance, debits decrease
    posted_balance = total_credits - total_debits

    # 2. Sum of active holds
    holds_stmt = select(func.coalesce(func.sum(Hold.amount_minor), 0)).where(
        and_(
            Hold.ledger_account_id == ledger_account_id,
            Hold.status == "ACTIVE"
        )
    )
    holds_res = await db.execute(holds_stmt)
    held_balance = holds_res.scalar() or 0

    available_balance = posted_balance - held_balance

    return {
        "posted_balance_minor": posted_balance,
        "held_balance_minor": held_balance,
        "available_balance_minor": available_balance
    }


async def post_journal_transaction(
    db: AsyncSession,
    transaction_id: str,
    entries: List[Dict[str, Any]],
    description: str = "",
    correlation_id: Optional[str] = None
) -> List[LedgerEntry]:
    """
    Posts balanced debit/credit entries for a transaction.
    Enforces the double-entry invariant: sum(debits) == sum(credits).
    """
    total_debits = 0
    total_credits = 0

    for e in entries:
        amt = e["amount_minor"]
        if e["entry_type"] == LedgerEntryType.DEBIT or e["entry_type"] == "DEBIT":
            total_debits += amt
        elif e["entry_type"] == LedgerEntryType.CREDIT or e["entry_type"] == "CREDIT":
            total_credits += amt
        else:
            raise ValueError(f"Invalid entry type: {e['entry_type']}")

    if total_debits != total_credits:
        raise LedgerInvariantViolation(
            f"Ledger invariant violation: debits ({total_debits}) != credits ({total_credits})"
        )

    posted_entries = []
    now = datetime.now(timezone.utc)
    for e in entries:
        entry = LedgerEntry(
            id=str(uuid.uuid4()),
            payment_id=transaction_id,
            ledger_account_id=e["ledger_account_id"],
            entry_type=LedgerEntryType.DEBIT if (e["entry_type"] == LedgerEntryType.DEBIT or e["entry_type"] == "DEBIT") else LedgerEntryType.CREDIT,
            amount_minor=e["amount_minor"],
            currency=e["currency"],
            description=e.get("description", description),
            reference_id=transaction_id,
            created_at=now
        )
        db.add(entry)
        posted_entries.append(entry)

    await db.flush()
    return posted_entries


async def place_hold(
    db: AsyncSession,
    payment_id: str,
    ledger_account_id: str,
    amount_minor: int,
    currency: str,
    description: str = "Pre-authorization hold"
) -> Hold:
    """Places a hold on funds during payment AUTHORISATION."""
    # Check available balance
    bal = await calculate_account_balance(db, ledger_account_id)
    if bal["available_balance_minor"] < amount_minor:
        raise InsufficientFundsError(
            f"Insufficient available funds. Required: {amount_minor}, Available: {bal['available_balance_minor']}"
        )

    hold = Hold(
        id=str(uuid.uuid4()),
        payment_id=payment_id,
        ledger_account_id=ledger_account_id,
        amount_minor=amount_minor,
        currency=currency.upper(),
        status="ACTIVE",
        description=description,
        created_at=datetime.now(timezone.utc)
    )
    db.add(hold)
    await db.flush()
    return hold


async def release_hold(
    db: AsyncSession,
    payment_id: str,
    reason: str = "Payment failed or cancelled"
) -> Optional[Hold]:
    """Releases an active hold when payment fails or cancels."""
    stmt = select(Hold).where(
        and_(
            Hold.payment_id == payment_id,
            Hold.status == "ACTIVE"
        )
    )
    res = await db.execute(stmt)
    hold = res.scalar_one_or_none()
    if hold:
        hold.status = "RELEASED"
        hold.released_at = datetime.now(timezone.utc)
        hold.release_reason = reason
        await db.flush()
    return hold


async def settle_payment_ledger(
    db: AsyncSession,
    payment: Payment,
    sender_ledger_acc_id: str,
    receiver_ledger_acc_id: str,
    clearing_ledger_acc_id: Optional[str] = None
) -> List[LedgerEntry]:
    """
    Settles a payment:
    1. Releases any active hold
    2. Posts balanced double-entry ledger entries:
       - Debit sender account
       - Credit receiver / clearing account
       - Posts fee entries if fee > 0
    """
    # 1. Release hold if exists
    await release_hold(db, payment.id, reason="Settled into ledger entries")

    entries = [
        {
            "ledger_account_id": sender_ledger_acc_id,
            "entry_type": LedgerEntryType.DEBIT,
            "amount_minor": payment.amount_minor,
            "currency": payment.currency,
            "description": f"Settlement for payment {payment.reference}"
        },
        {
            "ledger_account_id": receiver_ledger_acc_id,
            "entry_type": LedgerEntryType.CREDIT,
            "amount_minor": payment.amount_minor,
            "currency": payment.currency,
            "description": f"Settlement for payment {payment.reference}"
        }
    ]

    # Handle fee if applicable
    if payment.fee_minor and payment.fee_minor > 0 and clearing_ledger_acc_id:
        fee_entry_debit = {
            "ledger_account_id": sender_ledger_acc_id,
            "entry_type": LedgerEntryType.DEBIT,
            "amount_minor": payment.fee_minor,
            "currency": payment.currency,
            "description": f"Processing fee for {payment.reference}"
        }
        fee_entry_credit = {
            "ledger_account_id": clearing_ledger_acc_id,
            "entry_type": LedgerEntryType.CREDIT,
            "amount_minor": payment.fee_minor,
            "currency": payment.currency,
            "description": f"Fee income for {payment.reference}"
        }
        entries.extend([fee_entry_debit, fee_entry_credit])

    posted = await post_journal_transaction(
        db=db,
        transaction_id=payment.id,
        entries=entries,
        description=f"Settlement of {payment.reference}",
        correlation_id=payment.id
    )
    return posted


async def reverse_settlement_ledger(
    db: AsyncSession,
    payment: Payment,
    sender_ledger_acc_id: str,
    receiver_ledger_acc_id: str,
    reason: str = "Payment reversal/refund"
) -> List[LedgerEntry]:
    """
    Compensating transaction for reversed/refunded payment.
    Never deletes or updates past entries; writes inverse compensating entries.
    """
    entries = [
        {
            "ledger_account_id": receiver_ledger_acc_id,
            "entry_type": LedgerEntryType.DEBIT,
            "amount_minor": payment.amount_minor,
            "currency": payment.currency,
            "description": f"Reversal of {payment.reference}: {reason}"
        },
        {
            "ledger_account_id": sender_ledger_acc_id,
            "entry_type": LedgerEntryType.CREDIT,
            "amount_minor": payment.amount_minor,
            "currency": payment.currency,
            "description": f"Refund credit for {payment.reference}: {reason}"
        }
    ]

    posted = await post_journal_transaction(
        db=db,
        transaction_id=payment.id,
        entries=entries,
        description=f"Compensating reversal for {payment.reference}"
    )
    return posted
