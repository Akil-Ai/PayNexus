"""Compliance router: Sanctions queue, Watchlists CRUD, Fraud Rules CRUD & Dry-Run, and Approvals."""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models import (
    User, UserRole, Watchlist, WatchlistEntry, ScreeningResultRecord,
    FraudRule, FraudDecisionRecord, Approval, Payment, PaymentState
)
from app.services.audit_service import record_audit_log
from app.services.fraud_service import evaluate_fraud_rules
from app.services.payment_service import transition_payment_state

router = APIRouter(prefix="/compliance", tags=["compliance"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class WatchlistEntryCreate(BaseModel):
    name: str
    category: str = "INDIVIDUAL"
    country: Optional[str] = None
    aliases: Optional[List[str]] = None
    remarks: Optional[str] = None


class FraudRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str = "VELOCITY"
    rule_logic: Dict[str, Any]
    risk_score_impact: int = Field(20, ge=1, le=100)
    decision_action: str = Field("REVIEW", pattern="^(ALLOW|REVIEW|BLOCK)$")
    is_active: bool = True


class ApprovalAction(BaseModel):
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    notes: Optional[str] = None


# ── Sanctions Screening Endpoints ─────────────────────────────────────────────

@router.get("/screening-queue")
async def get_screening_queue(
    result_filter: Optional[str] = Query(None, description="BLOCKED, REVIEW, PASS"),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMPLIANCE_OFFICER, UserRole.ADMIN, UserRole.OPERATIONS, UserRole.AUDITOR]))
):
    """List screening hits requiring compliance attention."""
    query = select(ScreeningResultRecord).order_by(desc(ScreeningResultRecord.created_at))
    if result_filter:
        query = query.where(ScreeningResultRecord.result == result_filter.upper())
    query = query.limit(limit).offset(offset)

    res = await db.execute(query)
    records = res.scalars().all()
    return [{
        "id": r.id,
        "payment_id": r.payment_id,
        "entity_type": r.entity_type,
        "entity_name": r.entity_name,
        "result": r.result.value,
        "match_score": r.match_score,
        "matched_entry_name": r.matched_entry_name,
        "match_details": r.match_details,
        "status": r.status,
        "reviewed_by": r.reviewed_by,
        "created_at": r.created_at.isoformat() if r.created_at else None
    } for r in records]


# ── Watchlist Management Endpoints ───────────────────────────────────────────

@router.get("/watchlists")
async def list_watchlists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all sanctions watchlists."""
    stmt = select(Watchlist).order_by(Watchlist.name)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/watchlists/{watchlist_id}/entries")
async def add_watchlist_entry(
    watchlist_id: str,
    entry: WatchlistEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMPLIANCE_OFFICER, UserRole.ADMIN]))
):
    """Add an entry to a sanctions watchlist."""
    item = WatchlistEntry(
        id=str(uuid.uuid4()),
        watchlist_id=watchlist_id,
        name=entry.name,
        category=entry.category,
        country=entry.country,
        aliases=entry.aliases or [],
        remarks=entry.remarks,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(item)
    await db.commit()

    await record_audit_log(
        db=db,
        entity_type="WATCHLIST_ENTRY",
        entity_id=item.id,
        action="CREATE",
        actor_id=current_user.id,
        actor_type="USER",
        new_values={"name": entry.name, "watchlist_id": watchlist_id}
    )
    return {"message": "Watchlist entry created", "id": item.id}


# ── Fraud Rules CRUD & Dry-Run ───────────────────────────────────────────────

@router.get("/fraud-rules")
async def list_fraud_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all configurable fraud detection rules."""
    stmt = select(FraudRule).order_by(FraudRule.priority.asc(), FraudRule.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/fraud-rules")
async def create_fraud_rule(
    rule: FraudRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMPLIANCE_OFFICER, UserRole.ADMIN]))
):
    """Create a new fraud detection rule."""
    item = FraudRule(
        id=str(uuid.uuid4()),
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        rule_logic=rule.rule_logic,
        risk_score_impact=rule.risk_score_impact,
        decision_action=rule.decision_action,
        is_active=rule.is_active,
        created_at=datetime.now(timezone.utc)
    )
    db.add(item)
    await db.commit()

    await record_audit_log(
        db=db,
        entity_type="FRAUD_RULE",
        entity_id=item.id,
        action="CREATE",
        actor_id=current_user.id,
        actor_type="USER",
        new_values={"name": rule.name, "decision_action": rule.decision_action}
    )
    return {"message": "Fraud rule created", "id": item.id}


@router.patch("/fraud-rules/{rule_id}/toggle")
async def toggle_fraud_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMPLIANCE_OFFICER, UserRole.ADMIN]))
):
    """Enable or disable a fraud rule at runtime."""
    stmt = select(FraudRule).where(FraudRule.id == rule_id)
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Fraud rule not found")

    old_state = rule.is_active
    rule.is_active = not old_state
    await db.commit()

    await record_audit_log(
        db=db,
        entity_type="FRAUD_RULE",
        entity_id=rule.id,
        action="TOGGLE_STATUS",
        actor_id=current_user.id,
        actor_type="USER",
        old_values={"is_active": old_state},
        new_values={"is_active": rule.is_active}
    )
    return {"id": rule.id, "is_active": rule.is_active}


# ── Four-Eyes Maker-Checker Approvals ──────────────────────────────────────────

@router.post("/approvals/{approval_id}")
async def process_maker_checker_approval(
    approval_id: str,
    action: ApprovalAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.COMPLIANCE_OFFICER, UserRole.ADMIN]))
):
    """
    Four-eyes approval for releasing BLOCKED/REVIEW payments.
    Requires two distinct users:
    - User 1 (Maker): Requests or submits payment
    - User 2 (Checker): Approves via this endpoint
    Enforced: current_user != maker
    """
    stmt = select(Approval).where(Approval.id == approval_id)
    res = await db.execute(stmt)
    approval = res.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Approval already in state {approval.status}")

    # Enforce Maker-Checker separation of duties: Checker cannot be the Maker!
    if approval.requested_by == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Four-eyes principle violation: Checker cannot be the Maker who requested the approval."
        )

    now = datetime.now(timezone.utc)
    approval.status = "APPROVED" if action.action == "APPROVE" else "REJECTED"
    approval.decided_by = current_user.id
    approval.decided_at = now
    approval.notes = action.notes

    # Update associated payment if approved
    if approval.payment_id:
        p_stmt = select(Payment).where(Payment.id == approval.payment_id)
        p_res = await db.execute(p_stmt)
        payment = p_res.scalar_one_or_none()
        if payment:
            target_state = PaymentState.AUTHORISED if action.action == "APPROVE" else PaymentState.BLOCKED
            await transition_payment_state(
                db=db,
                payment=payment,
                new_state=target_state,
                actor=f"{current_user.email} (Four-Eyes Checker)",
                reason=f"Four-eyes approval decision: {action.action}. Notes: {action.notes or 'None'}"
            )

    await db.commit()

    await record_audit_log(
        db=db,
        entity_type="APPROVAL",
        entity_id=approval.id,
        action=f"FOUR_EYES_{action.action}",
        actor_id=current_user.id,
        actor_type="USER",
        new_values={"status": approval.status, "notes": action.notes}
    )

    return {
        "approval_id": approval.id,
        "status": approval.status,
        "decided_by": current_user.email,
        "payment_id": approval.payment_id
    }
