import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta
from app.db.database import AsyncSessionLocal
from sqlalchemy import select
from app.models import (
    ExceptionCase, ExceptionStatus, ExceptionType,
    DlqEvent, Payment
)

async def seed_data():
    async with AsyncSessionLocal() as db:
        pmts = (await db.execute(select(Payment).limit(10))).scalars().all()
        if not pmts:
            print("No payments found")
            return

        now = datetime.now(timezone.utc)
        cases = [
            ExceptionCase(
                id=str(uuid.uuid4()),
                case_number=f"EXC-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                exception_type=ExceptionType.AMOUNT_MISMATCH,
                status=ExceptionStatus.OPEN,
                priority=1,
                payment_id=pmts[0].id,
                title=f"Reconciliation amount discrepancy on payment {pmts[0].reference}",
                description=f"External rail statement reported variance of 25.00 INR against internal double-entry ledger on payment {pmts[0].reference}.",
                resolution_code="SETTLEMENT_VARIANCE",
                resolution_notes="Adjust ledger entry after verifying bank batch cut-off time.",
                sla_deadline=now + timedelta(hours=4),
                created_at=now - timedelta(hours=1)
            ),
            ExceptionCase(
                id=str(uuid.uuid4()),
                case_number=f"EXC-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                exception_type=ExceptionType.STATUS_MISMATCH,
                status=ExceptionStatus.IN_REVIEW,
                priority=2,
                payment_id=pmts[1].id,
                title="Status mismatch: rail reports SUCCESS but payment is SUBMITTED",
                description=f"Payment {pmts[1].reference} processed by SWIFT rail with pacs.002 ACCP confirmation, internal state out of sync.",
                resolution_code="STATE_RESYNC",
                resolution_notes="Transition internal payment state to SETTLED and release ledger hold.",
                sla_deadline=now + timedelta(hours=12),
                assigned_to=None,
                created_at=now - timedelta(hours=3)
            ),
            ExceptionCase(
                id=str(uuid.uuid4()),
                case_number=f"EXC-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                exception_type=ExceptionType.MISSING_AT_RAIL,
                status=ExceptionStatus.OPEN,
                priority=1,
                payment_id=pmts[2].id,
                title="Transaction missing in UPI end-of-day settlement batch file",
                description=f"Payment {pmts[2].reference} dispatched to UPI gateway was absent from camt.053 intraday settlement statement.",
                resolution_code="MANUAL_INQUIRY",
                resolution_notes="File rail inquiry ticket with NPCI clearinghouse.",
                sla_deadline=now + timedelta(hours=2),
                created_at=now - timedelta(minutes=40)
            ),
            ExceptionCase(
                id=str(uuid.uuid4()),
                case_number=f"EXC-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                exception_type=ExceptionType.DUPLICATE,
                status=ExceptionStatus.RESOLVED,
                priority=3,
                payment_id=pmts[3].id,
                title="Duplicate transaction attempt identified by idempotency filter",
                description="Client submitted identical idempotency key within 120s window.",
                resolution_code="CLOSED_IDEMPOTENT",
                resolution_notes="Original payload replayed successfully with cached response.",
                sla_deadline=now - timedelta(hours=1),
                resolved_at=now - timedelta(minutes=20),
                created_at=now - timedelta(hours=5)
            )
        ]
        db.add_all(cases)

        dlqs = [
            DlqEvent(
                id=str(uuid.uuid4()),
                original_stream="payment_events",
                original_message_id="1729074000000-0",
                event_type="RAIL_DISPATCH_TIMEOUT",
                payload={"payment_id": pmts[4].id, "rail": "SWIFT", "retry_attempts": 3, "amount_minor": pmts[4].amount_minor},
                failure_reason="Connection timeout after 3 retries: SWIFT rail adapter responded with HTTP 504 Gateway Timeout.",
                retry_count=3,
                resolved=False,
                created_at=now - timedelta(hours=2)
            ),
            DlqEvent(
                id=str(uuid.uuid4()),
                original_stream="payment_events",
                original_message_id="1729074100000-0",
                event_type="VALIDATION_POISON_PILL",
                payload={"payment_id": pmts[5].id, "rail": "NEFT", "error_detail": "Malformed ISO 20022 XML at <GrpHdr>"},
                failure_reason="Malformed ISO 20022 XML: XMLSchema validation failed at element <GrpHdr><MsgId>.",
                retry_count=1,
                resolved=False,
                created_at=now - timedelta(hours=4)
            ),
            DlqEvent(
                id=str(uuid.uuid4()),
                original_stream="payment_events",
                original_message_id="1729074200000-0",
                event_type="CIRCUIT_BREAKER_TRIPPED",
                payload={"payment_id": pmts[6].id, "rail": "CARD", "failure_rate": 0.6},
                failure_reason="Circuit breaker OPEN for rail CARD. Fast-failing transaction after error rate exceeded 50%.",
                retry_count=0,
                resolved=True,
                resolved_at=now - timedelta(minutes=15),
                created_at=now - timedelta(hours=6)
            )
        ]
        db.add_all(dlqs)
        await db.commit()
        print("Successfully seeded ExceptionCases and DlqEvents!")

if __name__ == "__main__":
    asyncio.run(seed_data())
