"""Mock SWIFT Cross-Border Rail Simulator (:8103).
Simulates cross-border MT103 / pacs.008 payments and gpi tracking.
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

app = FastAPI(title="Mock SWIFT Rail Simulator", version="1.0.0")

chaos_state = {
    "latency_ms": int(os.getenv("DEFAULT_LATENCY_MS", "2000")),
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


class SwiftTransferRequest(BaseModel):
    bic: Optional[str] = None
    account_number: Optional[str] = None
    amount_minor: int
    currency: str = "USD"
    reference: str
    remittance_info: Optional[str] = None


@app.get("/healthz")
async def healthz():
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="SWIFT gateway down")
    return {"status": "ok", "rail": "SWIFT"}


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
@app.post("/pacs008/submit")
async def initiate_swift_transfer(req: dict):
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="SWIFT gateway down")

    ref = req.get("reference") or req.get("msgId") or req.get("endToEndId") or f"SWIFT-{uuid.uuid4().hex[:8]}"
    amt = req.get("amount_minor") or req.get("amount", 0)
    curr = req.get("currency", "USD")

    if chaos_state["latency_ms"] > 0:
        await asyncio.sleep(chaos_state["latency_ms"] / 1000.0)

    if chaos_state["error_rate"] > 0 and random.random() < chaos_state["error_rate"]:
        raise HTTPException(status_code=500, detail="SWIFT Alliance Gateway: NAK received")

    uetr = str(uuid.uuid4())
    record = {
        "uetr": uetr,
        "txId": uetr,
        "msgId": ref,
        "reference": ref,
        "amount_minor": amt,
        "currency": curr,
        "status": "ACSC",
        "txSts": "ACSC",
        "gpi_status": "ACSP",  # Accepted Settlement in Process
        "settled_at": datetime.now(timezone.utc).isoformat()
    }
    transactions[ref] = record
    transactions[uetr] = record

    if chaos_state["drop_response_rate"] > 0 and random.random() < chaos_state["drop_response_rate"]:
        raise HTTPException(status_code=504, detail="SWIFT ACK Timeout - Response dropped")

    return {
        "status": "ACSC",
        "rail_reference": uetr,
        "txId": uetr,
        "msgId": ref,
        "uetr": uetr,
        "gpi_status": record["gpi_status"],
        "message": "SWIFT payment accepted for settlement",
        "settled_at": record["settled_at"]
    }


@app.get("/status/{uetr}")
async def get_swift_status(uetr: str):
    if uetr in transactions:
        return transactions[uetr]
    return {"status": "NOT_FOUND", "uetr": uetr}


@app.post("/pacs002/status")
async def post_swift_status(req: dict):
    tx_id = req.get("txId") or req.get("uetr")
    if tx_id and tx_id in transactions:
        return transactions[tx_id]
    return {
        "txId": tx_id,
        "txSts": "ACSC",
        "status": "ACSC",
        "stsRsnInf": "Settlement confirmed"
    }


@app.post("/camt056/cancel")
async def post_swift_cancel(req: dict):
    return {"status": "CANCELLED", "txId": req.get("txId")}


@app.get("/settlement-file", response_class=PlainTextResponse)
async def get_settlement_file():
    lines = ["reference,uetr,amount_minor,currency,direction,counterparty_name,counterparty_account"]
    for ref, txn in transactions.items():
        if ref == txn["reference"]:
            lines.append(f"{ref},{txn['uetr']},{txn['amount_minor']},{txn['currency']},CREDIT,Global Beneficiary Ltd,US123456789")
    return "\n".join(lines)
