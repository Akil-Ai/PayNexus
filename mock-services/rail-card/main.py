"""Mock Card Rail Simulator (:8104).
Simulates Card Authorize, Capture, Refund, and tokenization.
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

app = FastAPI(title="Mock Card Rail Simulator", version="1.0.0")

chaos_state = {
    "latency_ms": int(os.getenv("DEFAULT_LATENCY_MS", "300")),
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


class CardAuthRequest(BaseModel):
    token: Optional[str] = None
    pan_masked: Optional[str] = None
    amount_minor: int
    currency: str = "INR"
    reference: str


@app.get("/healthz")
async def healthz():
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="Card switch down")
    return {"status": "ok", "rail": "CARD"}


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
@app.post("/authorize")
async def authorize_card(req: dict):
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="Card network down")

    ref = req.get("reference") or req.get("orderId") or f"CARD-{uuid.uuid4().hex[:8]}"
    amt = req.get("amount_minor") or req.get("amount", 0)
    curr = req.get("currency", "INR")
    token = req.get("token") or req.get("cardToken") or f"tok_{uuid.uuid4().hex[:16]}"

    if chaos_state["latency_ms"] > 0:
        await asyncio.sleep(chaos_state["latency_ms"] / 1000.0)

    if chaos_state["error_rate"] > 0 and random.random() < chaos_state["error_rate"]:
        raise HTTPException(status_code=500, detail="Card Network Decline: 05_DO_NOT_HONOR")

    auth_code = f"AUTH{random.randint(100000, 999999)}"
    record = {
        "auth_code": auth_code,
        "authCode": auth_code,
        "reference": ref,
        "amount_minor": amt,
        "currency": curr,
        "status": "SETTLED",
        "card_token": token,
        "settled_at": datetime.now(timezone.utc).isoformat()
    }
    transactions[ref] = record
    transactions[auth_code] = record

    if chaos_state["drop_response_rate"] > 0 and random.random() < chaos_state["drop_response_rate"]:
        raise HTTPException(status_code=504, detail="Response dropped after Card auth")

    return {
        "status": "SUCCESS",
        "rail_reference": auth_code,
        "auth_code": auth_code,
        "authCode": auth_code,
        "card_token": record["card_token"],
        "message": "Card authorized successfully",
        "settled_at": record["settled_at"]
    }


@app.post("/capture")
async def capture_card(req: dict):
    auth_code = req.get("authCode") or req.get("auth_code")
    settle_id = f"SETTLE-{uuid.uuid4().hex[:10].upper()}"
    return {
        "status": "CAPTURED",
        "settleId": settle_id,
        "authCode": auth_code,
        "message": "Card capture settled successfully"
    }


@app.post("/status")
async def post_card_status(req: dict):
    return {
        "status": "CAPTURED",
        "settleId": req.get("settleId", "SETTLE-OK"),
        "message": "Card payment captured"
    }


@app.post("/void")
async def void_card(req: dict):
    return {"status": "VOIDED", "message": "Card voided"}


@app.get("/status/{auth_code}")
async def get_card_status(auth_code: str):
    if auth_code in transactions:
        return transactions[auth_code]
    return {"status": "NOT_FOUND", "auth_code": auth_code}


@app.get("/settlement-file", response_class=PlainTextResponse)
async def get_settlement_file():
    lines = ["reference,auth_code,amount_minor,currency,direction,counterparty_name,counterparty_account"]
    for ref, txn in transactions.items():
        if ref == txn["reference"]:
            lines.append(f"{ref},{txn['auth_code']},{txn['amount_minor']},{txn['currency']},CREDIT,Card Acquirer,411111XXXXXX1111")
    return "\n".join(lines)
