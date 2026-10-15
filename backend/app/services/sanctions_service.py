"""Sanctions/AML screening service using RapidFuzz + external provider."""
import asyncio
import unicodedata
from typing import Optional

import httpx
from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import sanctions_hits_total
from app.models import (
    ScreeningResultRecord, ScreeningResult, WatchlistEntry,
    SystemSetting, Payment,
)

settings = get_settings()
logger = get_logger(__name__)

# These thresholds are read from system_settings at runtime
DEFAULT_BLOCK_THRESHOLD = 90.0
DEFAULT_REVIEW_THRESHOLD = 75.0
FAIL_OPEN = True  # On provider outage, pass (configurable in system_settings)


def _normalize_name(name: str) -> str:
    """Normalize name: lowercase, strip accents, collapse whitespace."""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    return " ".join(name.lower().split())


async def _get_setting(db: AsyncSession, key: str, default: str) -> str:
    result = await db.execute(
        select(SystemSetting.value).where(SystemSetting.key == key)
    )
    val = result.scalar_one_or_none()
    return val if val is not None else default


async def screen_name(
    db: AsyncSession,
    payment: Payment,
    name: str,
    subject_type: str,  # PAYER or PAYEE
) -> ScreeningResult:
    """
    Screen a name against the watchlist.
    1. Call external provider (sanctions-provider-sim)
    2. Also do local fuzzy match against DB watchlist entries
    3. Return the more conservative result
    """
    # Get thresholds from DB settings (runtime-editable)
    block_threshold = float(await _get_setting(
        db, "sanctions.block_threshold", str(DEFAULT_BLOCK_THRESHOLD)
    ))
    review_threshold = float(await _get_setting(
        db, "sanctions.review_threshold", str(DEFAULT_REVIEW_THRESHOLD)
    ))
    fail_open_str = await _get_setting(db, "sanctions.fail_open", "true")
    fail_open = fail_open_str.lower() == "true"

    # External provider call
    provider_result = await _call_provider(name, block_threshold, review_threshold)
    if provider_result is None:
        # Provider outage: apply fail-open/fail-closed policy
        if fail_open:
            provider_result = {"result": "PASS", "score": 0.0, "matched_name": None, "matched_id": None}
        else:
            provider_result = {"result": "BLOCKED", "score": 100.0, "matched_name": None, "matched_id": None}
        logger.warning("Sanctions provider outage", extra={"fail_open": fail_open, "name": name})

    # Local fuzzy match (belt-and-suspenders)
    local_result = await _local_fuzzy_match(db, name, block_threshold, review_threshold)

    # Take most conservative result
    results_rank = {"PASS": 0, "REVIEW": 1, "BLOCKED": 2}
    final_result_str = max(
        provider_result["result"],
        local_result["result"],
        key=lambda r: results_rank.get(r, 0),
    )
    final_result = ScreeningResult(final_result_str)

    # Use the higher score/match
    best = provider_result if (
        results_rank.get(provider_result["result"], 0) >=
        results_rank.get(local_result["result"], 0)
    ) else local_result

    # Persist screening result
    record = ScreeningResultRecord(
        payment_id=payment.id,
        screening_type="SANCTIONS",
        subject_type=subject_type,
        subject_name=name,
        result=final_result,
        score=best.get("score"),
        matched_entry_id=best.get("matched_id"),
        matched_name=best.get("matched_name"),
        threshold_used=block_threshold,
        provider="sanctions-provider-sim",
        raw_response=provider_result,
    )
    db.add(record)
    await db.flush()

    sanctions_hits_total.labels(result=final_result.value).inc()
    logger.info("Sanctions screening result", extra={
        "name": name,
        "result": final_result.value,
        "score": best.get("score"),
    })
    return final_result


async def _call_provider(name: str, block_threshold: float, review_threshold: float) -> Optional[dict]:
    """Call the external sanctions provider sim."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.sanctions_url}/screen",
                json={
                    "name": name,
                    "block_threshold": block_threshold,
                    "review_threshold": review_threshold,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Sanctions provider call failed", extra={"error": str(e)})
        return None


async def _local_fuzzy_match(
    db: AsyncSession,
    name: str,
    block_threshold: float,
    review_threshold: float,
) -> dict:
    """Fuzzy match name against local watchlist DB using RapidFuzz."""
    norm_name = _normalize_name(name)

    # Load active watchlist entries
    result = await db.execute(
        select(WatchlistEntry).where(WatchlistEntry.is_active == True)
    )
    entries = result.scalars().all()

    if not entries:
        return {"result": "PASS", "score": 0.0, "matched_name": None, "matched_id": None}

    best_score = 0.0
    best_match = None
    best_entry = None

    for entry in entries:
        names_to_check = [entry.name]
        if entry.aliases:
            names_to_check.extend(entry.aliases.split("|"))

        for candidate in names_to_check:
            norm_candidate = _normalize_name(candidate)
            score = fuzz.token_set_ratio(norm_name, norm_candidate)
            if score > best_score:
                best_score = score
                best_match = candidate
                best_entry = entry

    if best_score >= block_threshold:
        return {
            "result": "BLOCKED",
            "score": best_score,
            "matched_name": best_match,
            "matched_id": best_entry.id if best_entry else None,
        }
    elif best_score >= review_threshold:
        return {
            "result": "REVIEW",
            "score": best_score,
            "matched_name": best_match,
            "matched_id": best_entry.id if best_entry else None,
        }
    else:
        return {"result": "PASS", "score": best_score, "matched_name": None, "matched_id": None}


async def screen_payment_parties(
    db: AsyncSession,
    payment_id: str,
    payer_name: str,
    payer_country: str = "IN",
    payee_name: str = "Beneficiary",
    payee_country: str = "IN",
) -> dict:
    """Screen both payer and payee for sanctions and AML compliance."""
    block_threshold = float(await _get_setting(
        db, "SANCTIONS_BLOCK_THRESHOLD", str(DEFAULT_BLOCK_THRESHOLD)
    ))
    review_threshold = float(await _get_setting(
        db, "SANCTIONS_REVIEW_THRESHOLD", str(DEFAULT_REVIEW_THRESHOLD)
    ))

    # Match payer
    payer_match = await _local_fuzzy_match(db, payer_name, block_threshold, review_threshold)
    # Match payee
    payee_match = await _local_fuzzy_match(db, payee_name, block_threshold, review_threshold)

    # Persist ScreeningResultRecords
    payer_rec = ScreeningResultRecord(
        payment_id=payment_id,
        screening_type="SANCTIONS",
        subject_type="PAYER",
        subject_name=payer_name,
        result=ScreeningResult[payer_match["result"]],
        score=payer_match["score"],
        matched_entry_id=payer_match.get("matched_id"),
        matched_name=payer_match.get("matched_name"),
        threshold_used=review_threshold,
        provider="LOCAL_RAPIDFUZZ",
        raw_response=payer_match
    )
    payee_rec = ScreeningResultRecord(
        payment_id=payment_id,
        screening_type="SANCTIONS",
        subject_type="PAYEE",
        subject_name=payee_name,
        result=ScreeningResult[payee_match["result"]],
        score=payee_match["score"],
        matched_entry_id=payee_match.get("matched_id"),
        matched_name=payee_match.get("matched_name"),
        threshold_used=review_threshold,
        provider="LOCAL_RAPIDFUZZ",
        raw_response=payee_match
    )
    db.add_all([payer_rec, payee_rec])
    await db.flush()

    # Determine overall result
    scores = [payer_match["score"], payee_match["score"]]
    max_score = max(scores)
    max_match = payer_match if payer_match["score"] >= payee_match["score"] else payee_match

    if payer_match["result"] == "BLOCKED" or payee_match["result"] == "BLOCKED":
        overall = ScreeningResult.BLOCKED
    elif payer_match["result"] == "REVIEW" or payee_match["result"] == "REVIEW":
        overall = ScreeningResult.REVIEW
    else:
        overall = ScreeningResult.PASS

    return {
        "overall_result": overall,
        "max_match_score": max_score,
        "max_match_name": max_match.get("matched_name"),
        "payer_result": payer_match,
        "payee_result": payee_match
    }

