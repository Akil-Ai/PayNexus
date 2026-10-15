"""Mock Sanctions / AML Provider Simulator (:8201).
Serves fuzzy matching against OFAC / UN / EU style watchlists with RapidFuzz.
"""
import asyncio
import os
import random
import unicodedata
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

app = FastAPI(title="Mock Sanctions Provider Simulator", version="1.0.0")

chaos_state = {
    "latency_ms": int(os.getenv("DEFAULT_LATENCY_MS", "200")),
    "is_down": False
}

# Embedded Sanctions Watchlist
WATCHLIST = [
    {"id": "OFAC-001", "name": "Viktor Anatolyevich Bout", "category": "INDIVIDUAL", "country": "RU", "aliases": ["Victor Bout", "Boris Bout"]},
    {"id": "OFAC-002", "name": "Dawood Ibrahim Kaskar", "category": "INDIVIDUAL", "country": "IN", "aliases": ["Dawood Ebrahim", "Haji Dawood"]},
    {"id": "OFAC-003", "name": "Hafiz Muhammad Saeed", "category": "INDIVIDUAL", "country": "PK", "aliases": ["Hafiz Saeed", "Muhammad Saeed"]},
    {"id": "OFAC-004", "name": "Al-Furqan Foundation", "category": "ENTITY", "country": "SY", "aliases": ["Furqan Media"]},
    {"id": "OFAC-005", "name": "Rosoboronexport", "category": "ENTITY", "country": "RU", "aliases": ["JSC Rosoboronexport"]},
    {"id": "OFAC-006", "name": "Semion Yudkovich Mogilevich", "category": "INDIVIDUAL", "country": "UA", "aliases": ["Seva Mogilevich"]},
    {"id": "OFAC-007", "name": "Qasem Soleimani", "category": "INDIVIDUAL", "country": "IR", "aliases": ["Ghasem Soleymani"]},
    {"id": "OFAC-008", "name": "Bank Melli Iran", "category": "ENTITY", "country": "IR", "aliases": ["National Bank of Iran"]},
    {"id": "OFAC-009", "name": "Jocelyn Wildenstein Holdings", "category": "ENTITY", "country": "CH", "aliases": []},
    {"id": "OFAC-010", "name": "North Korean Munitions Industry", "category": "ENTITY", "country": "KP", "aliases": ["MID"]}
]


class ScreenRequest(BaseModel):
    name: str
    country: Optional[str] = None
    threshold: float = 70.0


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
    return text.strip().lower()


@app.get("/healthz")
async def healthz():
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="Sanctions simulator down")
    return {"status": "ok", "service": "sanctions-provider-sim"}


@app.get("/chaos")
async def get_chaos():
    return chaos_state


@app.post("/chaos")
async def update_chaos(cfg: Dict[str, Any]):
    chaos_state["latency_ms"] = cfg.get("latency_ms", chaos_state["latency_ms"])
    chaos_state["is_down"] = cfg.get("is_down", chaos_state["is_down"])
    return chaos_state


@app.get("/watchlist")
async def list_watchlist():
    return WATCHLIST


@app.post("/screen")
async def screen_entity(req: ScreenRequest):
    if chaos_state["is_down"]:
        raise HTTPException(status_code=503, detail="Sanctions simulator down")

    if chaos_state["latency_ms"] > 0:
        await asyncio.sleep(chaos_state["latency_ms"] / 1000.0)

    target = normalize_text(req.name)
    best_score = 0.0
    matched_entry = None

    for entry in WATCHLIST:
        names_to_check = [entry["name"]] + (entry.get("aliases") or [])
        for n in names_to_check:
            clean_n = normalize_text(n)
            # Token set ratio handles word permutations and near-misses
            score = fuzz.token_set_ratio(target, clean_n)
            if score > best_score:
                best_score = float(score)
                matched_entry = entry

    # Classification: > 85 BLOCKED, 70-85 REVIEW, < 70 PASS
    if best_score >= 85.0:
        decision = "BLOCKED"
    elif best_score >= req.threshold:
        decision = "REVIEW"
    else:
        decision = "PASS"

    return {
        "query_name": req.name,
        "decision": decision,
        "match_score": round(best_score, 1),
        "matched_entry": matched_entry if decision != "PASS" else None
    }
