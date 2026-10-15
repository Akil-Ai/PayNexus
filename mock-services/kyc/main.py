"""Mock KYC Provider Simulator (:8202).
Simulates identity verification, KYC levels, and document validation.
"""
import asyncio
import os
import random
import uuid
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Mock KYC Provider Simulator", version="1.0.0")

chaos_state = {
    "latency_ms": int(os.getenv("DEFAULT_LATENCY_MS", "300")),
    "is_down": False
}


class VerifyRequest(BaseModel):
    customer_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    country: str = "IN"


@app.get("/healthz")
async def healthz():
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="KYC provider down")
    return {"status": "ok", "service": "kyc-provider-sim"}


@app.get("/chaos")
async def get_chaos():
    return chaos_state


@app.post("/chaos")
async def update_chaos(cfg: Dict[str, Any]):
    chaos_state["latency_ms"] = cfg.get("latency_ms", chaos_state["latency_ms"])
    chaos_state["is_down"] = cfg.get("is_down", chaos_state["is_down"])
    return chaos_state


@app.post("/verify")
async def verify_identity(req: VerifyRequest):
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="KYC provider down")

    if chaos_state["latency_ms"] > 0:
        await asyncio.sleep(chaos_state["latency_ms"] / 1000.0)

    # Deterministic or high-confidence verification
    verification_id = f"KYC-VER-{uuid.uuid4().hex[:10].upper()}"
    return {
        "verification_id": verification_id,
        "customer_id": req.customer_id,
        "name": req.name,
        "status": "VERIFIED",
        "level": "STANDARD",
        "document_type": "NATIONAL_ID",
        "document_number_masked": "XXXX-XXXX-8921",
        "verified_at": "2026-10-15T00:00:00Z"
    }
