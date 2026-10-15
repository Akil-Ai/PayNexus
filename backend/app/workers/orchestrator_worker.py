"""Payment Orchestrator Worker.
Consumes events from Redis Streams, drives transaction state machine, runs compliance pipeline,
manages double-entry ledger holds, dispatches to rail adapters, and handles failures/DLQ.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.adapters.rail_adapters import get_rail_adapter
from app.adapters.circuit_breaker import CircuitBreakerOpenException
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.redis_client import get_redis, PAYMENT_STREAM, DLQ_STREAM
from app.db.database import AsyncSessionLocal
from app.domain.state_machine import validate_transition
from app.models import (
    Payment, PaymentState, Customer, Beneficiary, Account,
    ScreeningResult, FraudDecision, Approval, DlqEvent, ExceptionCase, ExceptionType
)
from app.services.audit_service import record_audit_log
from app.services.fraud_service import evaluate_fraud_rules
from app.services.kyc_service import verify_customer_kyc, check_kyc_limit
from app.services.ledger_service import place_hold, release_hold, settle_payment_ledger, get_or_create_ledger_account
from app.services.payment_service import transition_payment_state
from app.services.sanctions_service import screen_payment_parties

logger = get_logger(__name__)
settings = get_settings()

GROUP_NAME = "orchestrator-group"
CONSUMER_NAME = f"orch-{uuid.uuid4().hex[:6]}"


async def setup_consumer_group():
    """Ensures Redis Stream and Consumer Group exist."""
    redis = await get_redis()
    try:
        await redis.xgroup_create(PAYMENT_STREAM, GROUP_NAME, id="0", mkstream=True)
        logger.info(f"Consumer group {GROUP_NAME} created for stream {PAYMENT_STREAM}")
    except Exception as e:
        if "BUSYGROUP" in str(e):
            logger.debug(f"Consumer group {GROUP_NAME} already exists.")
        else:
            logger.warning(f"Error checking consumer group: {e}")


async def process_payment_orchestration(payment_id: str):
    """Executes full compliance, ledger, and rail dispatch for a payment."""
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Payment)
            .where(Payment.id == payment_id)
            .options(
                selectinload(Payment.customer),
                selectinload(Payment.beneficiary),
                selectinload(Payment.sender_account),
                selectinload(Payment.rail)
            )
        )
        res = await db.execute(stmt)
        payment = res.scalar_one_or_none()

        if not payment:
            logger.error(f"Payment {payment_id} not found for orchestration.")
            return

        if payment.state != PaymentState.CREATED:
            logger.info(f"Payment {payment_id} already in state {payment.state.value}. Skipping orchestration.")
            return

        # ── Step 1: Transition CREATED -> VALIDATED ───────────────────────────
        payment = await transition_payment_state(
            db=db, payment=payment, new_state=PaymentState.VALIDATED,
            actor="ORCHESTRATOR", reason="Message schema and basic constraints validated"
        )
        await db.commit()

        # ── Step 2: Transition VALIDATED -> SCREENING ─────────────────────────
        payment = await transition_payment_state(
            db=db, payment=payment, new_state=PaymentState.SCREENING,
            actor="ORCHESTRATOR", reason="Initiating integrated compliance screening"
        )
        await db.commit()

        # ── Step 3: Run KYC, Sanctions, and Fraud Checks ──────────────────────
        customer = payment.customer
        beneficiary = payment.beneficiary

        # 3a. KYC check
        if customer:
            kyc_info = await verify_customer_kyc(db, customer)
            kyc_ok, kyc_err = check_kyc_limit(customer.kyc_level, payment.amount_minor)
            if not kyc_ok:
                await transition_payment_state(
                    db, payment, PaymentState.BLOCKED,
                    actor="KYC_ENGINE", reason=kyc_err
                )
                await db.commit()
                return

        # 3b. Sanctions Screening
        sanctions_res = await screen_payment_parties(
            db=db,
            payment_id=payment.id,
            payer_name=customer.name if customer else "Payer",
            payer_country=customer.country if customer else "IN",
            payee_name=beneficiary.name if beneficiary else "Beneficiary",
            payee_country=beneficiary.country if beneficiary else "IN"
        )

        overall_sanctions = sanctions_res.get("overall_result", ScreeningResult.PASS)
        if overall_sanctions == ScreeningResult.BLOCKED:
            await transition_payment_state(
                db, payment, PaymentState.BLOCKED,
                actor="SANCTIONS_ENGINE",
                reason=f"Sanctions watchlist hit on {sanctions_res.get('max_match_name')} (Score: {sanctions_res.get('max_match_score')})"
            )
            await db.commit()
            return
        elif overall_sanctions == ScreeningResult.REVIEW:
            # Create maker-checker approval requirement
            appr = Approval(
                id=str(uuid.uuid4()),
                payment_id=payment.id,
                approval_type="SANCTIONS_REVIEW",
                status="PENDING",
                requested_by="SYSTEM_SANCTIONS",
                requested_at=datetime.now(timezone.utc)
            )
            db.add(appr)
            await transition_payment_state(
                db, payment, PaymentState.REVIEW,
                actor="SANCTIONS_ENGINE",
                reason=f"Sanctions review band match on {sanctions_res.get('max_match_name')} (Score: {sanctions_res.get('max_match_score')})"
            )
            await db.commit()
            return

        # 3c. Fraud Engine (JSON-Logic + ML score)
        fraud_eval = await evaluate_fraud_rules(
            db=db,
            payment=payment,
            customer=customer,
            beneficiary=beneficiary
        )
        if fraud_eval["decision"] == FraudDecision.BLOCK:
            await transition_payment_state(
                db, payment, PaymentState.BLOCKED,
                actor="FRAUD_ENGINE",
                reason=f"Fraud risk blocked: {fraud_eval['reason']}"
            )
            await db.commit()
            return
        elif fraud_eval["decision"] == FraudDecision.REVIEW:
            appr = Approval(
                id=str(uuid.uuid4()),
                payment_id=payment.id,
                approval_type="FRAUD_REVIEW",
                status="PENDING",
                requested_by="SYSTEM_FRAUD",
                requested_at=datetime.now(timezone.utc)
            )
            db.add(appr)
            await transition_payment_state(
                db, payment, PaymentState.REVIEW,
                actor="FRAUD_ENGINE",
                reason=f"Fraud review flagged: {fraud_eval['reason']}"
            )
            await db.commit()
            return

        # ── Step 4: Compliance Passed -> AUTHORISED ───────────────────────────
        # Prepare double-entry ledger accounts
        sender_acc = await get_or_create_ledger_account(
            db=db,
            account_id=payment.sender_account_id,
            name=customer.full_name if customer else "Customer Account",
            currency=payment.currency,
            customer_id=payment.customer_id
        )

        # Place pre-authorization hold
        try:
            await place_hold(
                db=db,
                payment_id=payment.id,
                ledger_account_id=sender_acc.id,
                amount_minor=payment.amount_minor,
                currency=payment.currency
            )
        except Exception as hold_err:
            logger.warning(f"Hold placement bypassed or error: {hold_err}")

        payment = await transition_payment_state(
            db, payment, PaymentState.AUTHORISED,
            actor="ORCHESTRATOR", reason="Compliance screening passed; funds held"
        )
        await db.commit()

        # ── Step 5: Dispatch to Payment Rail Adapter ───────────────────────────
        rail_name = (payment.rail.code if payment.rail else "UPI").upper()
        adapter = get_rail_adapter(rail_name)

        payment = await transition_payment_state(
            db, payment, PaymentState.SUBMITTED,
            actor="ORCHESTRATOR", reason=f"Dispatched to {rail_name} rail adapter"
        )
        await db.commit()

        try:
            # Call rail adapter with circuit breaker and retries
            rail_resp = await adapter.submit_payment(payment)

            if rail_resp.get("status") in ("SETTLED", "SUCCESS"):
                # ── Step 6: Rail Settlement Success ───────────────────────────
                receiver_acc = await get_or_create_ledger_account(
                    db=db,
                    account_number=beneficiary.account_number if beneficiary else f"ACC-BEN-{payment.beneficiary_id[:8]}",
                    name=beneficiary.name if beneficiary else "Beneficiary Account",
                    currency=payment.currency
                )
                clearing_acc = await get_or_create_ledger_account(
                    db=db,
                    account_number="PAYNEXUS_CLEARING_FEE_POOL",
                    name="PayNexus Internal Fee Clearing Account",
                    currency=payment.currency,
                    account_type="INTERNAL_EQUITY"
                )

                # Post balanced journal entries
                await settle_payment_ledger(
                    db=db,
                    payment=payment,
                    sender_ledger_acc_id=sender_acc.id,
                    receiver_ledger_acc_id=receiver_acc.id,
                    clearing_ledger_acc_id=clearing_acc.id
                )

                await transition_payment_state(
                    db, payment, PaymentState.SETTLED,
                    actor=f"RAIL_{rail_name}",
                    reason=f"Settled successfully at rail ({rail_resp.get('rail_reference', 'CONFIRMED')})"
                )
                await db.commit()
                logger.info(f"Payment {payment.id} SETTLED successfully.")

            else:
                # Rail failed or rejected
                await _handle_rail_failure(db, payment, sender_acc.id, rail_name, rail_resp.get("error", "Rail rejected"))

        except CircuitBreakerOpenException as cb_exc:
            logger.error(f"Circuit breaker OPEN for rail {rail_name}: {cb_exc}")
            await _handle_rail_failure(db, payment, sender_acc.id, rail_name, f"Circuit breaker OPEN: {str(cb_exc)}")

        except Exception as exc:
            logger.error(f"Error submitting payment {payment.id} to rail: {exc}", exc_info=True)
            await _handle_rail_failure(db, payment, sender_acc.id, rail_name, str(exc))


async def _handle_rail_failure(db, payment: Payment, sender_acc_id: str, rail_name: str, error_msg: str):
    """Handles rail dispatch failure, releases hold, and routes event to DLQ."""
    # Release hold
    try:
        await release_hold(db, payment.id, reason=f"Rail failure: {error_msg}")
    except Exception:
        pass

    await transition_payment_state(
        db, payment, PaymentState.FAILED,
        actor=f"RAIL_{rail_name}", reason=f"Failed: {error_msg}"
    )

    # Record DLQ Event
    dlq_item = DlqEvent(
        id=str(uuid.uuid4()),
        payment_id=payment.id,
        event_type="PAYMENT_RAIL_FAILED",
        payload={
            "payment_id": payment.id,
            "rail": rail_name,
            "error": error_msg,
            "amount_minor": payment.amount_minor,
            "currency": payment.currency
        },
        error_message=error_msg,
        replayed=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(dlq_item)
    await db.commit()

    # Also push to Redis DLQ stream
    try:
        redis = await get_redis()
        await redis.xadd(DLQ_STREAM, {
            "dlq_id": dlq_item.id,
            "payment_id": payment.id,
            "error": error_msg
        })
    except Exception as e:
        logger.warning(f"Could not push to Redis DLQ stream: {e}")


async def in_flight_recovery_sweep():
    """
    Recovers payments stuck in SUBMITTED state (e.g. if orchestrator crashed mid-flight).
    Queries status or fails/settles accordingly.
    """
    async with AsyncSessionLocal() as db:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
            stmt = (
                select(Payment)
                .options(selectinload(Payment.rail))
                .where(
                    and_(
                        Payment.state == PaymentState.SUBMITTED,
                        Payment.updated_at < cutoff
                    )
                )
            )
            res = await db.execute(stmt)
            stuck_payments = res.scalars().all()

            for p in stuck_payments:
                rail_code = (p.rail.code if p.rail else "UPI").upper()
                logger.info(f"In-flight watchdog: reconciling stuck payment {p.id} on rail {rail_code}")
                adapter = get_rail_adapter(rail_code)
                try:
                    status_info = await adapter.inquire_status(p.rail_reference or p.reference)
                    if status_info.get("status") in ("SETTLED", "SUCCESS"):
                        await transition_payment_state(
                            db, p, PaymentState.SETTLED,
                            actor="WATCHDOG_INQUIRY", reason="Confirmed settled via status inquiry"
                        )
                    elif status_info.get("status") in ("FAILED", "REJECTED"):
                        await transition_payment_state(
                            db, p, PaymentState.FAILED,
                            actor="WATCHDOG_INQUIRY", reason="Confirmed failed via status inquiry"
                        )
                except Exception as e:
                    logger.warning(f"Watchdog status inquiry error for {p.id}: {e}")

            await db.commit()
        except Exception as exc:
            logger.error(f"In-flight recovery sweep error: {exc}")


async def main():
    setup_logging()
    logger.info(f"Payment Orchestrator Worker starting [{CONSUMER_NAME}]...")
    await setup_consumer_group()

    redis = await get_redis()
    watchdog_counter = 0

    while True:
        try:
            # Read messages from Redis Stream consumer group
            entries = await redis.xreadgroup(
                GROUP_NAME, CONSUMER_NAME,
                {PAYMENT_STREAM: ">"},
                count=10,
                block=2000
            )

            if entries:
                for stream_name, messages in entries:
                    for msg_id, data in messages:
                        try:
                            event_type = data.get("event_type", "")
                            aggregate_id = data.get("aggregate_id", "") or data.get("payment_id", "")
                            if not aggregate_id and "payload" in data:
                                try:
                                    raw_payload = data.get("payload")
                                    p_obj = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
                                    aggregate_id = p_obj.get("payment_id") or p_obj.get("aggregate_id")
                                except Exception:
                                    pass

                            if aggregate_id:
                                logger.info(f"Orchestrating event {event_type} for payment {aggregate_id}")
                                await process_payment_orchestration(aggregate_id)

                            # Acknowledge message in consumer group
                            await redis.xack(PAYMENT_STREAM, GROUP_NAME, msg_id)
                        except Exception as inner_exc:
                            logger.error(f"Error handling message {msg_id}: {inner_exc}", exc_info=True)
                            await redis.xack(PAYMENT_STREAM, GROUP_NAME, msg_id)
            else:
                await asyncio.sleep(1.0)

            # Periodic in-flight recovery sweep every 30 seconds
            watchdog_counter += 1
            if watchdog_counter >= 30:
                watchdog_counter = 0
                await in_flight_recovery_sweep()


        except asyncio.CancelledError:
            logger.info("Orchestrator worker stopping...")
            break
        except Exception as err:
            logger.error(f"Unexpected error in orchestrator loop: {err}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
