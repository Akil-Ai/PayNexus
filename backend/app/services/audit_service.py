"""Audit log service with hash chain integrity."""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


def _build_row_content(data: dict) -> str:
    """Deterministic string for hashing."""
    fields = ["sequence", "entity_type", "entity_id", "action",
              "actor_id", "actor_type", "correlation_id", "created_at"]
    content = {k: str(data.get(k, "")) for k in fields}
    return json.dumps(content, sort_keys=True)


def _compute_hash(prev_hash: Optional[str], row_content: str) -> str:
    data = (prev_hash or "") + row_content
    return hashlib.sha256(data.encode()).hexdigest()


async def write_audit_entry(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor_id: Optional[str] = None,
    actor_type: str = "SYSTEM",
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
) -> str:
    """Write an immutable audit log entry with hash chain. Returns entry ID."""
    import uuid

    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Get next sequence number (atomic in PG, fallback for SQLite)
    try:
        seq_result = await db.execute(text("SELECT nextval('audit_log_seq')"))
        sequence = seq_result.scalar()
    except Exception:
        seq_result = await db.execute(text("SELECT coalesce(max(sequence), 0) + 1 FROM audit_log"))
        sequence = seq_result.scalar()

    # Get previous hash (last row in sequence order)
    prev_result = await db.execute(
        text("SELECT row_hash FROM audit_log ORDER BY sequence DESC LIMIT 1")
    )
    prev_hash = prev_result.scalar()

    # Build row content for hashing (deterministic)
    row_data = {
        "sequence": sequence,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "actor_id": actor_id or "",
        "actor_type": actor_type,
        "correlation_id": correlation_id or "",
        "created_at": now.isoformat(),
    }
    row_content = _build_row_content(row_data)
    row_hash = _compute_hash(prev_hash, row_content)

    await db.execute(
        text("""
            INSERT INTO audit_log (
                id, sequence, entity_type, entity_id, action,
                actor_id, actor_type, correlation_id, ip_address, user_agent,
                old_values, new_values, prev_hash, row_hash, created_at
            ) VALUES (
                :id, :sequence, :entity_type, :entity_id, :action,
                :actor_id, :actor_type, :correlation_id, :ip_address, :user_agent,
                :old_values, :new_values, :prev_hash, :row_hash, :created_at
            )
        """),
        {
            "id": entry_id,
            "sequence": sequence,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "correlation_id": correlation_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "old_values": json.dumps(old_values) if old_values else None,
            "new_values": json.dumps(new_values) if new_values else None,
            "prev_hash": prev_hash,
            "row_hash": row_hash,
            "created_at": now,
        }
    )
    return entry_id


async def verify_audit_chain(db: AsyncSession) -> dict:
    """Recompute the entire hash chain and report any tampering."""
    result = await db.execute(
        text("SELECT id, sequence, entity_type, entity_id, action, actor_id, actor_type, "
             "correlation_id, created_at, prev_hash, row_hash FROM audit_log ORDER BY sequence ASC")
    )
    rows = result.fetchall()

    if not rows:
        return {"valid": True, "total_entries": 0, "tampered_entries": []}

    tampered = []
    prev_hash = None

    for row in rows:
        row_data = {
            "sequence": row.sequence,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "action": row.action,
            "actor_id": row.actor_id or "",
            "actor_type": row.actor_type,
            "correlation_id": row.correlation_id or "",
            "created_at": row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
        }
        row_content = _build_row_content(row_data)
        expected_hash = _compute_hash(prev_hash, row_content)

        if expected_hash != row.row_hash:
            tampered.append({
                "id": row.id,
                "sequence": row.sequence,
                "expected_hash": expected_hash,
                "actual_hash": row.row_hash,
            })

        prev_hash = row.row_hash

    return {
        "valid": len(tampered) == 0,
        "total_entries": len(rows),
        "tampered_entries": tampered,
    }


async def tamper_audit_entry(db: AsyncSession, entry_id: str) -> None:
    """DEMO ONLY: Directly tamper with an audit log entry to show detection."""
    # Bypass the trigger by using direct SQL update on the internal table
    # In production this would require superuser; here we simulate it
    await db.execute(
        text("""
            UPDATE audit_log
            SET action = action || '_TAMPERED'
            WHERE id = :id
        """),
        {"id": entry_id}
    )
    await db.commit()


# Alias for backward compatibility across modules
record_audit_log = write_audit_entry


async def verify_audit_hash_chain(
    db: AsyncSession,
    start_sequence: Optional[int] = None,
    end_sequence: Optional[int] = None
) -> dict:
    res = await verify_audit_chain(db)
    return {
        "is_valid": res["valid"],
        "total_rows_checked": res["total_entries"],
        "tampered_entries": res["tampered_entries"],
        "corrupted_sequence": res["tampered_entries"][0]["sequence"] if res["tampered_entries"] else None,
    }


async def tamper_audit_row_for_demo(
    db: AsyncSession,
    sequence: Optional[int] = None,
    new_action: str = "TAMPERED_ACTION_MALICIOUS_OVERRIDE"
) -> int:
    if sequence is None:
        row = (await db.execute(text("SELECT sequence FROM audit_log ORDER BY sequence DESC LIMIT 1"))).scalar()
        if not row:
            await write_audit_entry(
                db,
                entity_type="SYSTEM",
                entity_id="tamper-demo",
                action="INITIAL_SEED_DEMO"
            )
            await db.commit()
            row = (await db.execute(text("SELECT sequence FROM audit_log ORDER BY sequence DESC LIMIT 1"))).scalar()
        sequence = row

    await db.execute(
        text("UPDATE audit_log SET action = :new_action WHERE sequence = :sequence"),
        {"new_action": new_action, "sequence": sequence}
    )
    await db.commit()
    return sequence


