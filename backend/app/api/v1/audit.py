"""Audit API: query logs, cryptographic hash chain verification, and tamper detection demo."""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_roles
from app.db.database import get_db
from app.models import User, UserRole, AuditLog
from app.services.audit_service import (
    verify_audit_hash_chain, tamper_audit_row_for_demo
)

router = APIRouter(prefix="/audit", tags=["audit"])


class TamperDemoRequest(BaseModel):
    row_sequence: Optional[int] = None
    corrupted_action: str = "TAMPERED_ACTION_MALICIOUS_OVERRIDE"


@router.get("/")
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Query audit logs with optional filters."""
    query = select(AuditLog).order_by(desc(AuditLog.sequence))
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type.upper())
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)

    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    entries = res.scalars().all()
    return entries


@router.post("/verify")
async def verify_integrity(
    start_sequence: Optional[int] = Query(None),
    end_sequence: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.AUDITOR, UserRole.ADMIN, UserRole.COMPLIANCE_OFFICER]))
):
    """
    Cryptographically verifies the SHA-256 hash chain of the audit log.
    Reports:
    - is_valid (True/False)
    - total_rows_checked
    - corrupted_sequence (if tampered)
    - expected_hash vs actual_hash
    """
    result = await verify_audit_hash_chain(db, start_sequence, end_sequence)
    return result


@router.post("/tamper-demo")
async def execute_tamper_demo(
    payload: TamperDemoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Deliberately alters an audit log row's action to demonstrate cryptographic tamper detection.
    This demonstrates the immutability verification mechanism required in the specification.
    """
    corrupted_seq = await tamper_audit_row_for_demo(
        db=db,
        sequence=payload.row_sequence,
        new_action=payload.corrupted_action
    )
    return {
        "message": "Audit row successfully tampered for demonstration.",
        "tampered_sequence": corrupted_seq,
        "instructions": "Call POST /api/v1/audit/verify to observe the verification failure and pinpoint the exact tampered row."
    }
