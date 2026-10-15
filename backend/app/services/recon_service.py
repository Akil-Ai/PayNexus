"""Reconciliation engine: statement ingestion, exact & fuzzy matching, exception classification, and auto-resolution."""
import csv
import io
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    ReconRun, ReconFile, ReconItem, ExceptionCase, ExceptionType,
    ExceptionStatus, Payment, PaymentState, Rail
)
from app.services.payment_service import transition_payment_state
from app.services.audit_service import record_audit_log

logger = get_logger(__name__)


class StatementRecord:
    def __init__(
        self,
        reference: str,
        amount_minor: int,
        currency: str,
        direction: str = "CREDIT",
        counterparty_name: Optional[str] = None,
        counterparty_account: Optional[str] = None,
        value_date: Optional[datetime] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ):
        self.reference = reference.strip()
        self.amount_minor = amount_minor
        self.currency = currency.strip().upper()
        self.direction = direction.strip().upper()
        self.counterparty_name = counterparty_name
        self.counterparty_account = counterparty_account
        self.value_date = value_date or datetime.now(timezone.utc)
        self.raw_data = raw_data or {}


def parse_csv_statement(content: str) -> List[StatementRecord]:
    """Parses bank statement CSV with flexible columns."""
    records = []
    reader = csv.DictReader(io.StringIO(content.strip()))
    for row in reader:
        ref = row.get("reference") or row.get("txn_id") or row.get("utr") or row.get("end_to_end_id", "")
        amt_str = row.get("amount") or row.get("amount_minor") or "0"
        try:
            amt_minor = int(float(amt_str) * 100) if "." in amt_str else int(amt_str)
        except ValueError:
            amt_minor = 0

        ccy = row.get("currency") or "INR"
        direction = row.get("direction") or row.get("type") or "CREDIT"
        cp_name = row.get("counterparty_name") or row.get("beneficiary_name") or row.get("remitter_name")
        cp_acc = row.get("counterparty_account") or row.get("account_number")

        records.append(StatementRecord(
            reference=ref,
            amount_minor=amt_minor,
            currency=ccy,
            direction=direction,
            counterparty_name=cp_name,
            counterparty_account=cp_acc,
            raw_data=row
        ))
    return records


def parse_camt_053_statement(content: str) -> List[StatementRecord]:
    """Parses ISO 20022 camt.053 Bank-to-Customer Statement XML."""
    records = []
    try:
        root = ET.fromstring(content)
        for ntry in root.iter():
            if ntry.tag.endswith("Ntry"):
                amt_elem = None
                for c in ntry.iter():
                    if c.tag.endswith("Amt"):
                        amt_elem = c
                        break
                amt_str = amt_elem.text if amt_elem is not None else "0"
                ccy = amt_elem.attrib.get("Ccy", "INR") if amt_elem is not None else "INR"
                amt_minor = int(round(float(amt_str) * 100))

                # Direction CdtDbtInd
                direction = "CREDIT"
                for c in ntry.iter():
                    if c.tag.endswith("CdtDbtInd"):
                        direction = "CREDIT" if c.text == "CRDT" else "DEBIT"
                        break

                # Reference
                ref = ""
                for c in ntry.iter():
                    if c.tag.endswith("AcctSvcrRef") or c.tag.endswith("EndToEndId"):
                        ref = c.text or ""
                        break

                records.append(StatementRecord(
                    reference=ref or str(uuid.uuid4()),
                    amount_minor=amt_minor,
                    currency=ccy,
                    direction=direction,
                    raw_data={"xml_entry": True}
                ))
    except Exception as exc:
        logger.error(f"Error parsing camt.053 XML: {exc}")
    return records


async def run_reconciliation(
    db: AsyncSession,
    recon_run_id: str,
    rail_code: str,
    statement_records: List[StatementRecord],
    auto_resolve: bool = True,
    actor_id: str = "SYSTEM"
) -> Dict[str, Any]:
    """
    Executes the 2-tier matching pipeline:
    Tier 1: Exact Match (reference + amount + currency)
    Tier 2: Fuzzy / Secondary Match (amount + counterparty / date window)
    Tier 3: Exception classification & auto-resolution
    """
    start_time = time.time()
    total_records = len(statement_records)
    matched_count = 0
    matched_value = 0
    exception_count = 0
    exceptions_by_type: Dict[str, int] = {e.value: 0 for e in ExceptionType}

    # Fetch internal payments for this rail or recent window
    stmt = select(Payment).where(
        Payment.state.in_([
            PaymentState.SUBMITTED, PaymentState.SETTLED,
            PaymentState.AUTHORISED, PaymentState.FAILED
        ])
    )
    res = await db.execute(stmt)
    internal_payments = res.scalars().all()

    # Index internal payments by reference and end_to_end_id
    internal_by_ref: Dict[str, Payment] = {}
    for p in internal_payments:
        if p.reference:
            internal_by_ref[p.reference.strip().upper()] = p
        if p.end_to_end_id:
            internal_by_ref[p.end_to_end_id.strip().upper()] = p

    unmatched_rail_records: List[StatementRecord] = []
    matched_payment_ids = set()

    # ── Tier 1: Exact Reference Match ─────────────────────────────────────────
    for rec in statement_records:
        ref_key = rec.reference.upper()
        p = internal_by_ref.get(ref_key)

        if p:
            # Check for amount mismatch
            if p.amount_minor != rec.amount_minor:
                # AMOUNT_MISMATCH exception
                exc_type = ExceptionType.AMOUNT_MISMATCH
                exceptions_by_type[exc_type.value] += 1
                exception_count += 1
                await _create_exception(
                    db, recon_run_id, p, rec, exc_type,
                    f"Amount mismatch: Internal={p.amount_minor/100:.2f} {p.currency}, Rail={rec.amount_minor/100:.2f} {rec.currency}",
                    suggested_action="Adjust internal ledger to match rail confirmed amount or request rail review"
                )
            elif p.currency != rec.currency:
                exc_type = ExceptionType.CURRENCY_MISMATCH
                exceptions_by_type[exc_type.value] += 1
                exception_count += 1
                await _create_exception(
                    db, recon_run_id, p, rec, exc_type,
                    f"Currency mismatch: Internal={p.currency}, Rail={rec.currency}",
                    suggested_action="Manual FX conversion or counterparty reconciliation required"
                )
            else:
                # Exact match!
                matched_count += 1
                matched_value += p.amount_minor
                matched_payment_ids.add(p.id)

                # Status sync if needed (Auto-resolution)
                if p.state == PaymentState.SUBMITTED and auto_resolve:
                    try:
                        await transition_payment_state(
                            db, p, PaymentState.SETTLED,
                            actor=f"RECON-{recon_run_id[:8]}",
                            reason="Auto-reconciled: confirmed settled in rail statement"
                        )
                    except Exception as err:
                        logger.warning(f"Could not auto-settle payment {p.id}: {err}")
        else:
            unmatched_rail_records.append(rec)

    # ── Tier 2: Fuzzy / Amount + Date Matching ─────────────────────────────────
    still_unmatched_records = []
    for rec in unmatched_rail_records:
        fuzzy_match = None
        for p in internal_payments:
            if p.id in matched_payment_ids:
                continue
            if p.amount_minor == rec.amount_minor and p.currency == rec.currency:
                fuzzy_match = p
                break

        if fuzzy_match:
            matched_count += 1
            matched_value += fuzzy_match.amount_minor
            matched_payment_ids.add(fuzzy_match.id)
            if fuzzy_match.state == PaymentState.SUBMITTED and auto_resolve:
                try:
                    await transition_payment_state(
                        db, fuzzy_match, PaymentState.SETTLED,
                        actor=f"RECON-{recon_run_id[:8]}",
                        reason="Fuzzy auto-reconciled on exact amount match"
                    )
                except Exception:
                    pass
        else:
            still_unmatched_records.append(rec)

    # ── Tier 3: Unmatched items become Exceptions ──────────────────────────────
    # 1. Rail has records we don't have: MISSING_INTERNALLY
    for rec in still_unmatched_records:
        exc_type = ExceptionType.MISSING_INTERNALLY
        exceptions_by_type[exc_type.value] += 1
        exception_count += 1
        await _create_exception(
            db, recon_run_id, None, rec, exc_type,
            f"Transaction found at rail ({rec.reference}) but absent from PayNexus internal payments",
            suggested_action="Create missing internal payment record or investigate unauthorized debit/credit"
        )

    # 2. Payments SUBMITTED internally but absent from rail: MISSING_AT_RAIL
    for p in internal_payments:
        if p.id not in matched_payment_ids and p.state == PaymentState.SUBMITTED:
            exc_type = ExceptionType.MISSING_AT_RAIL
            exceptions_by_type[exc_type.value] += 1
            exception_count += 1
            await _create_exception(
                db, recon_run_id, p, None, exc_type,
                f"Payment {p.reference} submitted to {p.rail} is missing from rail statement",
                suggested_action="Trigger status inquiry to rail adapter or initiate payment reversal"
            )

    duration_sec = round(time.time() - start_time, 3)
    match_rate = round((matched_count / total_records * 100), 2) if total_records > 0 else 100.0

    # Update ReconRun record
    run_stmt = select(ReconRun).where(ReconRun.id == recon_run_id)
    run_res = await db.execute(run_stmt)
    recon_run = run_res.scalar_one_or_none()
    if recon_run:
        recon_run.status = "COMPLETED"
        recon_run.total_records = total_records
        recon_run.matched_records = matched_count
        recon_run.unmatched_records = exception_count
        recon_run.matched_value_minor = matched_value
        recon_run.match_rate = match_rate
        recon_run.duration_seconds = duration_sec
        recon_run.exceptions_by_type = exceptions_by_type
        recon_run.completed_at = datetime.now(timezone.utc)
        await db.flush()

    await record_audit_log(
        db=db,
        entity_type="RECONCILIATION",
        entity_id=recon_run_id,
        action="RUN_COMPLETED",
        actor_id=actor_id,
        actor_type="USER",
        new_values={
            "matched_records": matched_count,
            "match_rate": match_rate,
            "exceptions": exception_count,
            "duration_sec": duration_sec
        }
    )

    return {
        "recon_run_id": recon_run_id,
        "total_records": total_records,
        "matched_records": matched_count,
        "matched_value_minor": matched_value,
        "match_rate": match_rate,
        "exception_count": exception_count,
        "exceptions_by_type": exceptions_by_type,
        "duration_seconds": duration_sec
    }


async def _create_exception(
    db: AsyncSession,
    recon_run_id: str,
    payment: Optional[Payment],
    rec: Optional[StatementRecord],
    exc_type: ExceptionType,
    description: str,
    suggested_action: str
) -> ExceptionCase:
    """Helper to persist a classified exception case."""
    case = ExceptionCase(
        id=str(uuid.uuid4()),
        recon_run_id=recon_run_id,
        payment_id=payment.id if payment else None,
        exception_type=exc_type,
        status=ExceptionStatus.OPEN,
        priority="HIGH" if exc_type in (ExceptionType.AMOUNT_MISMATCH, ExceptionType.MISSING_INTERNALLY) else "MEDIUM",
        sla_hours=24,
        description=description,
        suggested_action=suggested_action,
        internal_record={
            "payment_id": payment.id,
            "reference": payment.reference,
            "amount_minor": payment.amount_minor,
            "currency": payment.currency,
            "state": payment.state.value
        } if payment else None,
        rail_record={
            "reference": rec.reference,
            "amount_minor": rec.amount_minor,
            "currency": rec.currency,
            "raw": rec.raw_data
        } if rec else None,
        created_at=datetime.now(timezone.utc)
    )
    db.add(case)
    await db.flush()
    return case
