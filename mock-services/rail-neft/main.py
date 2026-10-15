"""Mock NEFT / RTGS Rail Simulator (:8102).
Simulates batch clearance and statement file generation.
"""
import asyncio
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Mock NEFT Rail Simulator", version="1.0.0")

chaos_state = {
    "latency_ms": int(os.getenv("DEFAULT_LATENCY_MS", "500")),
    "error_rate": float(os.getenv("DEFAULT_ERROR_RATE", "0.0")),
    "drop_response_rate": 0.0,
    "is_down": False
}

transactions: Dict[str, Dict[str, Any]] = {}


class ChaosConfig(BaseModel):
    latency_ms: int = Field(0, ge=0, le=10000)
    error_rate: float = Field(0.0, ge=0.0, le=1.0)
    drop_response_rate: float = Field(0.0, ge=0.0, le=1.0)
    is_down: bool = False


class NeftTransferRequest(BaseModel):
    beneficiary_account: Optional[str] = None
    beneficiary_ifsc: Optional[str] = None
    amount_minor: int
    currency: str = "INR"
    reference: str
    remittance_info: Optional[str] = None


@app.get("/healthz")
async def healthz():
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="NEFT rail simulator down")
    return {"status": "ok", "rail": "NEFT"}


@app.get("/chaos")
async def get_chaos():
    return chaos_state


@app.post("/chaos")
async def update_chaos(cfg: ChaosConfig):
    chaos_state["latency_ms"] = cfg.latency_ms
    chaos_state["error_rate"] = cfg.error_rate
    chaos_state["drop_response_rate"] = cfg.drop_response_rate
    chaos_state["is_down"] = cfg.is_down
    return chaos_state


@app.post("/transfer")
async def initiate_neft_transfer(req: NeftTransferRequest):
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="NEFT rail down")

    if chaos_state["latency_ms"] > 0:
        await asyncio.sleep(chaos_state["latency_ms"] / 1000.0)

    if chaos_state["error_rate"] > 0 and random.random() < chaos_state["error_rate"]:
        raise HTTPException(status_code=500, detail="RBI NEFT Gateway Error: TIMEOUT")

    utr = f"NEFT{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
    record = {
        "utr": utr,
        "reference": req.reference,
        "amount_minor": req.amount_minor,
        "currency": req.currency,
        "status": "SETTLED",
        "batch_id": f"B{datetime.now().strftime('%H%M')}",
        "settled_at": datetime.now(timezone.utc).isoformat()
    }
    transactions[req.reference] = record
    transactions[utr] = record

    if chaos_state["drop_response_rate"] > 0 and random.random() < chaos_state["drop_response_rate"]:
        raise HTTPException(status_code=504, detail="Response dropped after NEFT processing")

    return {
        "status": "SUCCESS",
        "rail_reference": utr,
        "utr": utr,
        "batch_id": record["batch_id"],
        "message": "NEFT transfer queued/settled",
        "settled_at": record["settled_at"]
    }


@app.get("/status/{utr}")
async def get_neft_status(utr: str):
    if utr in transactions:
        return transactions[utr]
    return {"status": "NOT_FOUND", "utr": utr}


@app.get("/settlement-file", response_class=PlainTextResponse)
async def get_settlement_file():
    lines = ["reference,utr,amount_minor,currency,direction,counterparty_name,counterparty_account"]
    for ref, txn in transactions.items():
        if ref == txn["reference"]:
            lines.append(f"{ref},{txn['utr']},{txn['amount_minor']},{txn['currency']},CREDIT,NEFT Beneficiary,1234567890")
    return "\n".join(lines)
