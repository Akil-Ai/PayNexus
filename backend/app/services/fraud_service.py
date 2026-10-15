"""Fraud engine: JSON-logic rules from DB + Isolation Forest ML model."""
import json
import os
import pickle
from datetime import datetime, timedelta, timezone
from typing import Optional, List

import numpy as np

def jsonLogic(rule, data):
    """Robust built-in JSON-logic evaluator supporting var, and, or, >, >=, <, <=, ==, !=, in_hours."""
    if not isinstance(rule, dict):
        return rule
    if not rule:
        return True

    op = next(iter(rule))
    values = rule[op]

    if op == "var":
        if isinstance(values, list):
            var_name = values[0] if values else ""
            default = values[1] if len(values) > 1 else None
        else:
            var_name = values
            default = None
        if isinstance(data, dict):
            return data.get(var_name, default)
        return getattr(data, var_name, default)

    if op == "and":
        if not isinstance(values, list):
            values = [values]
        return all(bool(jsonLogic(v, data)) for v in values)

    if op == "or":
        if not isinstance(values, list):
            values = [values]
        return any(bool(jsonLogic(v, data)) for v in values)

    if op == ">":
        a = jsonLogic(values[0], data) if isinstance(values[0], dict) else values[0]
        b = jsonLogic(values[1], data) if isinstance(values[1], dict) else values[1]
        try:
            return float(a) > float(b)
        except (ValueError, TypeError):
            return False

    if op == ">=":
        a = jsonLogic(values[0], data) if isinstance(values[0], dict) else values[0]
        b = jsonLogic(values[1], data) if isinstance(values[1], dict) else values[1]
        try:
            return float(a) >= float(b)
        except (ValueError, TypeError):
            return False

    if op == "<":
        a = jsonLogic(values[0], data) if isinstance(values[0], dict) else values[0]
        b = jsonLogic(values[1], data) if isinstance(values[1], dict) else values[1]
        try:
            return float(a) < float(b)
        except (ValueError, TypeError):
            return False

    if op == "<=":
        a = jsonLogic(values[0], data) if isinstance(values[0], dict) else values[0]
        b = jsonLogic(values[1], data) if isinstance(values[1], dict) else values[1]
        try:
            return float(a) <= float(b)
        except (ValueError, TypeError):
            return False

    if op in ("==", "==="):
        a = jsonLogic(values[0], data) if isinstance(values[0], dict) else values[0]
        b = jsonLogic(values[1], data) if isinstance(values[1], dict) else values[1]
        return a == b

    if op in ("!=", "!=="):
        a = jsonLogic(values[0], data) if isinstance(values[0], dict) else values[0]
        b = jsonLogic(values[1], data) if isinstance(values[1], dict) else values[1]
        return a != b

    if op == "in_hours":
        # values: [start_hour, end_hour]
        start_h, end_h = values[0], values[1]
        current_h = datetime.now(timezone.utc).hour
        if start_h <= end_h:
            return start_h <= current_h <= end_h
        return current_h >= start_h or current_h <= end_h

    return False

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import fraud_decisions_total
from app.models import (
    FraudRule, FraudDecisionRecord, FraudDecision,
    Payment, PaymentState, SystemSetting, Customer,
)

settings = get_settings()
logger = get_logger(__name__)

# Model cache
_fraud_model = None
_model_loaded = False


def load_fraud_model():
    """Load Isolation Forest model from disk."""
    global _fraud_model, _model_loaded
    if _model_loaded:
        return _fraud_model
    try:
        candidates = [
            settings.fraud_model_path,
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models/fraud_model.pkl")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models/fraud_model.pkl")),
            "/app/models/fraud_model.pkl",
        ]
        found_path = None
        for p in candidates:
            if p and os.path.exists(p):
                found_path = p
                break

        if found_path:
            with open(found_path, "rb") as f:
                _fraud_model = pickle.load(f)
            logger.info("Fraud model loaded", extra={"path": found_path})
        else:
            logger.warning("Fraud model not found, ML scoring disabled")
    except Exception as e:
        logger.error("Failed to load fraud model", extra={"error": str(e)})
    _model_loaded = True
    return _fraud_model


async def _get_setting(db: AsyncSession, key: str, default: str) -> str:
    result = await db.execute(
        select(SystemSetting.value).where(SystemSetting.key == key)
    )
    val = result.scalar_one_or_none()
    return val if val is not None else default


async def _get_velocity_context(
    db: AsyncSession,
    customer_id: str,
    amount_minor: int,
    currency: str,
    window_minutes: int = 60,
) -> dict:
    """Compute velocity features for the current payment."""
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    result = await db.execute(
        select(
            func.count(Payment.id).label("count"),
            func.coalesce(func.sum(Payment.amount_minor), 0).label("total_amount"),
            func.avg(Payment.amount_minor).label("avg_amount"),
        ).where(
            Payment.customer_id == customer_id,
            Payment.created_at >= since,
            Payment.state.notin_([PaymentState.CANCELLED, PaymentState.FAILED]),
        )
    )
    row = result.one()

    # 90-day average
    since_90d = datetime.now(timezone.utc) - timedelta(days=90)
    avg_result = await db.execute(
        select(func.avg(Payment.amount_minor)).where(
            Payment.customer_id == customer_id,
            Payment.created_at >= since_90d,
            Payment.currency == currency,
        )
    )
    avg_90d = avg_result.scalar() or 0

    return {
        "velocity_count": row.count or 0,
        "velocity_total_minor": int(row.total_amount or 0),
        "velocity_avg_minor": float(row.avg_amount or 0),
        "historical_avg_minor": float(avg_90d),
        "amount_minor": amount_minor,
        "amount_vs_avg_ratio": (amount_minor / float(avg_90d)) if avg_90d > 0 else 0.0,
    }


async def evaluate_fraud(
    db: AsyncSession,
    payment: Payment,
    customer: Customer,
    is_new_beneficiary: bool = False,
) -> FraudDecision:
    """
    Evaluate fraud risk for a payment.
    Returns FraudDecision (ALLOW / REVIEW / BLOCK).
    """
    # Get thresholds from system settings
    allow_threshold = int(await _get_setting(db, "fraud.allow_threshold", "30"))
    block_threshold = int(await _get_setting(db, "fraud.block_threshold", "70"))
    fail_open_str = await _get_setting(db, "fraud.fail_open", "true")
    fail_open = fail_open_str.lower() == "true"

    velocity = await _get_velocity_context(
        db, payment.customer_id, payment.amount_minor, payment.currency
    )

    # Context for JSON-logic rules
    context = {
        "amount_minor": payment.amount_minor,
        "currency": payment.currency,
        "payment_type": payment.payment_type,
        "urgency": payment.urgency,
        "velocity_count_1h": velocity["velocity_count"],
        "velocity_total_1h": velocity["velocity_total_minor"],
        "amount_vs_avg_ratio": velocity["amount_vs_avg_ratio"],
        "is_new_beneficiary": is_new_beneficiary,
        "customer_kyc_level": customer.kyc_level.value if customer.kyc_level else "NONE",
        "customer_risk_rating": customer.risk_rating or "LOW",
        "is_pep": customer.is_pep,
        "hour_of_day": datetime.now(timezone.utc).hour,
        "historical_avg_minor": velocity["historical_avg_minor"],
    }

    # Evaluate active rules from DB
    result = await db.execute(
        select(FraudRule).where(FraudRule.is_active == True).order_by(FraudRule.priority)
    )
    rules = result.scalars().all()

    total_score = 0
    triggered_rules = []
    reasons = []
    final_decision_override = None

    for rule in rules:
        try:
            triggered = jsonLogic(rule.rule_logic, context)
        except Exception as e:
            logger.warning("Fraud rule evaluation error", extra={
                "rule_id": rule.id, "rule_name": rule.name, "error": str(e)
            })
            triggered = False

        if triggered:
            total_score += rule.score_contribution
            triggered_rules.append({
                "rule_id": rule.id,
                "name": rule.name,
                "score_contribution": rule.score_contribution,
            })
            reasons.append(f"{rule.name}: +{rule.score_contribution} points")
            # Rule-level decision override (BLOCK immediately)
            if rule.decision == FraudDecision.BLOCK and total_score >= block_threshold:
                final_decision_override = FraudDecision.BLOCK

    # ML Isolation Forest score
    ml_score = None
    model = load_fraud_model()
    if model is not None:
        try:
            features = np.array([[
                payment.amount_minor / 100.0,
                velocity["velocity_count"],
            ]])
            raw_score = model.decision_function(features)[0]
            # Normalize: anomaly score closer to -1 = more anomalous
            # Map to 0-1 where 1 = highly anomalous
            ml_score = max(0.0, min(1.0, (0.5 - raw_score)))
            ml_score_contribution = int(ml_score * 30)  # max +30 from ML
            total_score += ml_score_contribution
            if ml_score > 0.7:
                reasons.append(f"ML anomaly score: {ml_score:.2f} (+{ml_score_contribution})")
        except Exception as e:
            logger.warning("ML fraud scoring failed", extra={"error": str(e)})

    # Cap at 100
    total_score = min(total_score, 100)

    # Final decision
    if final_decision_override == FraudDecision.BLOCK:
        decision = FraudDecision.BLOCK
    elif total_score >= block_threshold:
        decision = FraudDecision.BLOCK
    elif total_score >= allow_threshold:
        decision = FraudDecision.REVIEW
    else:
        decision = FraudDecision.ALLOW

    # Persist
    record = FraudDecisionRecord(
        payment_id=payment.id,
        decision=decision,
        total_score=total_score,
        ml_score=ml_score,
        triggered_rules=triggered_rules,
        reasons=reasons,
        allow_threshold=allow_threshold,
        block_threshold=block_threshold,
    )
    db.add(record)
    await db.flush()

    # Update payment fields
    payment.fraud_decision = decision
    payment.fraud_score = total_score

    fraud_decisions_total.labels(decision=decision.value).inc()
    logger.info("Fraud evaluation", extra={
        "payment_id": payment.id,
        "decision": decision.value,
        "total_score": total_score,
        "triggered_rules": len(triggered_rules),
    })
    return decision


# Alias for backward compatibility
evaluate_fraud_rules = evaluate_fraud

