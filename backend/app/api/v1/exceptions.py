"""Unified Exception Queue and Dead-Letter Queue (DLQ) management API."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_roles
from app.core.logging import get_logger
from app.core.redis_client import get_redis, DLQ_STREAM, PAYMENT_STREAM

logger = get_logger(__name__)
from app.db.database import get_db
from app.models import (
    User, UserRole, ExceptionCase, ExceptionStatus, ExceptionType,
    DlqEvent, Payment, PaymentState
)
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/exceptions", tags=["exceptions"])


class AssignCaseRequest(BaseModel):
    assigned_to: str


class AddCommentRequest(BaseModel):
    comment: str


class ReplayDlqRequest(BaseModel):
    event_ids: List[str]


@router.get("/")
async def list_exceptions(
    status_filter: Optional[str] = Query(None, description="OPEN, IN_REVIEW, RESOLVED"),
    type_filter: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List exception cases with SLA ageing and filtering."""
    query = select(ExceptionCase).order_by(desc(ExceptionCase.created_at))
    if status_filter:
        query = query.where(ExceptionCase.status == status_filter.upper())
    if type_filter:
        query = query.where(ExceptionCase.exception_type == type_filter.upper())

    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    cases = res.scalars().all()

    output = []
    for c in cases:
        sla_hours = 4
        if c.sla_deadline and c.created_at:
            delta = c.sla_deadline - c.created_at
            sla_hours = max(1, int(delta.total_seconds() // 3600))

        priority_label = "HIGH" if c.priority <= 2 else ("MEDIUM" if c.priority == 3 else "LOW")
        suggested = c.resolution_notes or c.resolution_code or "Review settlement ledger and re-dispatch or manual repair."

        output.append({
            "id": c.id,
            "case_number": c.case_number,
            "exception_type": str(c.exception_type.value if hasattr(c.exception_type, "value") else c.exception_type),
            "description": c.description or c.title,
            "priority": priority_label,
            "status": str(c.status.value if hasattr(c.status, "value") else c.status),
            "sla_hours": sla_hours,
            "suggested_action": suggested,
            "assigned_to": c.assigned_to,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })
    return output


@router.post("/{case_id}/assign")
async def assign_exception(
    case_id: str,
    payload: AssignCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATIONS, UserRole.ADMIN]))
):
    """Assigns an exception case to an operator."""
    stmt = select(ExceptionCase).where(ExceptionCase.id == case_id)
    res = await db.execute(stmt)
    case = res.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Exception not found")

    case.assigned_to = payload.assigned_to
    case.status = ExceptionStatus.IN_REVIEW
    await db.commit()
    return {"message": "Case assigned", "case_id": case.id, "assigned_to": payload.assigned_to}


# ── Dead-Letter Queue (DLQ) Management ────────────────────────────────────────

@router.get("/dlq")
async def list_dlq_events(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List events sent to Dead-Letter Queue from failed worker runs."""
    stmt = select(DlqEvent).order_by(desc(DlqEvent.created_at)).limit(limit).offset(offset)
    res = await db.execute(stmt)
    items = res.scalars().all()

    output = []
    for item in items:
        payment_id = None
        if isinstance(item.payload, dict):
            payment_id = item.payload.get("payment_id")

        output.append({
            "id": item.id,
            "payment_id": payment_id,
            "event_type": item.event_type,
            "error_message": item.failure_reason,
            "replayed": bool(item.resolved),
            "payload": item.payload,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })
    return output


@router.post("/dlq/replay")
async def replay_dlq_events(
    payload: ReplayDlqRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATIONS, UserRole.ADMIN]))
):
    """Replays failed events from DLQ back into main payment orchestrator stream."""
    redis = await get_redis()
    replayed = []

    for event_id in payload.event_ids:
        stmt = select(DlqEvent).where(DlqEvent.id == event_id)
        res = await db.execute(stmt)
        event = res.scalar_one_or_none()
        if event and not event.resolved:
            payment_id = (event.payload or {}).get("payment_id") if isinstance(event.payload, dict) else ""
            # Re-enqueue to main stream
            try:
                await redis.xadd(
                    PAYMENT_STREAM,
                    {
                        "payment_id": str(payment_id or ""),
                        "event_type": event.event_type or "REPLAY",
                        "payload": json.dumps(event.payload or {}),
                        "replayed_from_dlq": "true"
                    }
                )
            except Exception as e:
                logger.warning(f"Could not push to redis during replay: {e}")

            event.resolved = True
            event.resolved_at = datetime.now(timezone.utc)
            event.resolved_by = current_user.id
            replayed.append(event.id)

    await db.commit()

    await record_audit_log(
        db=db,
        entity_type="DLQ",
        entity_id="BULK",
        action="REPLAY",
        actor_id=current_user.id,
        actor_type="USER",
        new_values={"replayed_event_ids": replayed}
    )

    return {"message": f"Successfully replayed {len(replayed)} events", "replayed_ids": replayed}
