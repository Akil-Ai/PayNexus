"""Mock UPI Rail Simulator (:8101).
Supports instant UPI transfer, status inquiry, chaos controls, and statement generation.
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

app = FastAPI(title="Mock UPI Rail Simulator", version="1.0.0")

# Runtime configurable chaos parameters
chaos_state = {
    "latency_ms": int(os.getenv("DEFAULT_LATENCY_MS", "150")),
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


class UpiTransferRequest(BaseModel):
    payer_vpa: Optional[str] = None
    payee_vpa: Optional[str] = None
    amount_minor: int
    currency: str = "INR"
    reference: str
    remarks: Optional[str] = None


@app.get("/healthz")
async def healthz():
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="UPI rail is currently down (chaos injected)")
    return {"status": "ok", "rail": "UPI"}


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
async def initiate_upi_transfer(req: UpiTransferRequest):
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="UPI rail down")

    # Injected latency
    if chaos_state["latency_ms"] > 0:
        await asyncio.sleep(chaos_state["latency_ms"] / 1000.0)

    # Injected error rate
    if chaos_state["error_rate"] > 0 and random.random() < chaos_state["error_rate"]:
        raise HTTPException(status_code=500, detail="NPCI UPI Gateway Error: PSP_TIMEOUT")

    # Injected drop response (processes internally but drops response to test idempotency)
    txn_id = f"UPI{uuid.uuid4().hex[:12].upper()}"
    record = {
        "txn_id": txn_id,
        "reference": req.reference,
        "amount_minor": req.amount_minor,
        "currency": req.currency,
        "status": "SETTLED",
        "rrn": f"10{random.randint(1000000000, 9999999999)}",
        "settled_at": datetime.now(timezone.utc).isoformat()
    }
    transactions[req.reference] = record
    transactions[txn_id] = record

    if chaos_state["drop_response_rate"] > 0 and random.random() < chaos_state["drop_response_rate"]:
        raise HTTPException(status_code=504, detail="Gateway Timeout - Response dropped after processing")

    return {
        "status": "SUCCESS",
        "rail_reference": txn_id,
        "rrn": record["rrn"],
        "message": "UPI transaction processed successfully",
        "settled_at": record["settled_at"]
    }


@app.get("/status/{reference}")
async def get_upi_status(reference: str):
    if reference in transactions:
        return transactions[reference]
    return {
        "status": "NOT_FOUND",
        "reference": reference,
        "message": "Transaction not found on UPI switch"
    }


@app.get("/settlement-file", response_class=PlainTextResponse)
async def get_settlement_file():
    """Generates statement CSV of transactions processed today."""
    lines = ["reference,txn_id,amount_minor,currency,direction,counterparty_name,counterparty_account"]
    for ref, txn in transactions.items():
        if ref == txn["reference"]:
            lines.append(f"{ref},{txn['txn_id']},{txn['amount_minor']},{txn['currency']},CREDIT,UPI Merchant,9876543210@upi")
    return "\n".join(lines)
