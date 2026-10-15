"""Rails configuration and Chaos Lab control API."""
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_roles
from app.adapters.circuit_breaker import get_circuit_breaker
from app.adapters.rail_adapters import get_rail_adapter
from app.core.config import get_settings
from app.db.database import get_db
from app.models import User, UserRole, Rail, RoutingRule
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/rails", tags=["rails"])
settings = get_settings()

RAIL_URL_MAP = {
    "UPI": settings.RAIL_UPI_URL,
    "NEFT": settings.RAIL_NEFT_URL,
    "SWIFT": settings.RAIL_SWIFT_URL,
    "CARD": settings.RAIL_CARD_URL,
}


class ChaosConfigRequest(BaseModel):
    latency_ms: int = Field(0, ge=0, le=10000)
    error_rate: float = Field(0.0, ge=0.0, le=1.0)
    drop_response_rate: float = Field(0.0, ge=0.0, le=1.0)
    is_down: bool = False


class RailRecommendationRequest(BaseModel):
    amount_minor: int
    currency: str = "INR"
    urgency: str = "NORMAL"  # INSTANT, NORMAL, BULK
    destination_country: str = "IN"


@router.get("/")
async def list_rails(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all configured payment rails with live circuit breaker and health states."""
    stmt = select(Rail).order_by(Rail.code)
    res = await db.execute(stmt)
    rails = res.scalars().all()

    output = []
    for r in rails:
        cb = get_circuit_breaker(r.code)
        cb_stats = cb.get_stats() if cb else {"state": "CLOSED", "failure_count": 0}
        output.append({
            "code": r.code,
            "name": r.name,
            "rail_type": getattr(r, "rail_type", getattr(r, "code", "UNKNOWN")),
            "is_active": r.is_active,
            "supported_currencies": r.supported_currencies,
            "min_amount_minor": r.min_amount_minor,
            "max_amount_minor": r.max_amount_minor,
            "base_fee_minor": getattr(r, "base_fee_minor", getattr(r, "fee_fixed_minor", 0)),
            "variable_fee_bps": getattr(r, "variable_fee_bps", 0),
            "cutoff_time": getattr(r, "cutoff_time", None),
            "settlement_window": getattr(r, "settlement_window", getattr(r, "settlement_hours", 0)),
            "circuit_breaker": cb_stats
        })
    return output


@router.post("/recommend")
async def recommend_rail(
    req: RailRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes rail recommendations (cheapest vs fastest) based on amount, currency, urgency, and live health.
    """
    stmt = select(Rail).where(Rail.is_active == True)
    res = await db.execute(stmt)
    active_rails = res.scalars().all()

    recommendations = []
    for r in active_rails:
        if req.currency.upper() not in (r.supported_currencies or []):
            continue
        if req.amount_minor < r.min_amount_minor or (r.max_amount_minor and req.amount_minor > r.max_amount_minor):
            continue

        # Check circuit breaker
        cb = get_circuit_breaker(r.code)
        cb_state = cb.state.value if cb else "CLOSED"
        if cb_state == "OPEN":
            continue  # Rail currently tripped

        # Calculate fee
        variable_fee = int(round(req.amount_minor * (r.variable_fee_bps / 10000)))
        total_fee_minor = r.base_fee_minor + variable_fee

        # Estimated latency / ETA
        eta_desc = "Instant (< 5s)" if r.code == "UPI" else (
            "T+2 Hours" if r.code == "NEFT" else (
                "Instant Auth (Capture T+1)" if r.code == "CARD" else "T+2 Days (SWIFT)"
            )
        )
        latency_score = 1 if r.code in ("UPI", "CARD") else (2 if r.code == "NEFT" else 3)

        recommendations.append({
            "rail_code": r.code,
            "rail_name": r.name,
            "total_fee_minor": total_fee_minor,
            "fee_formatted": f"{total_fee_minor / 100:.2f} {req.currency}",
            "eta_description": eta_desc,
            "latency_score": latency_score,
            "circuit_breaker_state": cb_state
        })

    if not recommendations:
        return {"cheapest": None, "fastest": None, "all_options": []}

    cheapest = min(recommendations, key=lambda x: x["total_fee_minor"])
    fastest = min(recommendations, key=lambda x: x["latency_score"])

    return {
        "cheapest": cheapest,
        "fastest": fastest,
        "all_options": recommendations
    }


# ── Chaos Lab Controls ────────────────────────────────────────────────────────

@router.get("/{rail_code}/chaos")
async def get_rail_chaos(
    rail_code: str,
    current_user: User = Depends(get_current_user)
):
    """Fetches live chaos parameters from the mock rail service."""
    base_url = RAIL_URL_MAP.get(rail_code.upper())
    if not base_url:
        raise HTTPException(status_code=404, detail="Rail mock service not configured")

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/chaos")
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Status {resp.status_code}"}
    except Exception as exc:
        return {"error": str(exc), "status": "Mock service offline"}


@router.post("/{rail_code}/chaos")
async def configure_rail_chaos(
    rail_code: str,
    payload: ChaosConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATIONS, UserRole.ADMIN]))
):
    """Injects chaos (latency, errors, drop response, downtime) into a mock rail container."""
    base_url = RAIL_URL_MAP.get(rail_code.upper())
    if not base_url:
        raise HTTPException(status_code=404, detail="Rail mock service not configured")

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(f"{base_url}/chaos", json=payload.model_dump())
            if resp.status_code == 200:
                await record_audit_log(
                    db=db,
                    entity_type="RAIL_CHAOS",
                    entity_id=rail_code.upper(),
                    action="UPDATE_CHAOS",
                    actor_id=current_user.id,
                    actor_type="USER",
                    new_values=payload.model_dump()
                )
                await db.commit()
                return {"message": f"Chaos injected into {rail_code}", "config": resp.json()}
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with {rail_code} sim: {exc}")


@router.post("/{rail_code}/circuit-breaker/reset")
async def reset_rail_circuit_breaker(
    rail_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.OPERATIONS, UserRole.ADMIN]))
):
    """Manually resets the circuit breaker for a payment rail."""
    cb = get_circuit_breaker(rail_code.upper())
    if cb:
        cb.reset()
    await record_audit_log(
        db=db,
        entity_type="CIRCUIT_BREAKER",
        entity_id=rail_code.upper(),
        action="MANUAL_RESET",
        actor_id=current_user.id,
        actor_type="USER"
    )
    await db.commit()
    return {"message": f"Circuit breaker for {rail_code} reset to CLOSED"}
