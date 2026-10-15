"""KYC (Know Your Customer) service.
Calls kyc-provider-sim, checks limits based on KycLevel, and persists decisions.
"""
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Customer, KycRecord, KycStatus, KycLevel

logger = get_logger(__name__)
settings = get_settings()

# Default KYC transaction limits in minor units (paise)
DEFAULT_LIMITS_MINOR = {
    KycLevel.NONE: 0,
    KycLevel.BASIC: 1_000_000,       # 10,000.00
    KycLevel.STANDARD: 10_000_000,   # 100,000.00
    KycLevel.ENHANCED: 100_000_000,  # 1,000,000.00
}


async def verify_customer_kyc(
    db: AsyncSession,
    customer: Customer,
    fail_closed: bool = False
) -> Dict[str, Any]:
    """
    Verifies customer identity via kyc-provider-sim or returns existing verified record.
    """
    # 1. Check existing record
    stmt = select(KycRecord).where(KycRecord.customer_id == customer.id).order_by(KycRecord.created_at.desc())
    res = await db.execute(stmt)
    latest_record = res.scalars().first()

    if latest_record and latest_record.status == KycStatus.VERIFIED:
        return {
            "status": latest_record.status.value,
            "level": latest_record.level.value,
            "verification_id": latest_record.id,
            "document_type": latest_record.document_type,
            "cached": True
        }

    # 2. Call kyc-provider-sim
    url = f"{settings.KYC_SERVICE_URL}/verify"
    payload = {
        "customer_id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "country": customer.country or "IN"
    }

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                status_str = data.get("status", "VERIFIED").upper()
                level_str = data.get("level", "STANDARD").upper()

                kyc_status = KycStatus(status_str) if status_str in KycStatus.__members__ else KycStatus.VERIFIED
                kyc_level = KycLevel(level_str) if level_str in KycLevel.__members__ else KycLevel.STANDARD

                rec = KycRecord(
                    customer_id=customer.id,
                    status=kyc_status,
                    level=kyc_level,
                    document_type=data.get("document_type", "NATIONAL_ID"),
                    document_number_masked=data.get("document_number_masked", "XXXX-XXXX-1234"),
                    provider="kyc-provider-sim",
                    provider_reference=data.get("verification_id", f"KYC-{customer.id[:8]}"),
                    raw_response=data,
                    verified_at=datetime.now(timezone.utc)
                )
                db.add(rec)
                customer.kyc_status = kyc_status
                customer.kyc_level = kyc_level
                await db.flush()

                return {
                    "status": kyc_status.value,
                    "level": kyc_level.value,
                    "verification_id": rec.id,
                    "document_type": rec.document_type,
                    "cached": False
                }
            else:
                logger.warning(f"KYC service returned HTTP {resp.status_code}")
    except Exception as exc:
        logger.error(f"Failed to reach KYC service: {exc}")

    # Fallback / Graceful degradation
    if fail_closed:
        return {
            "status": KycStatus.REJECTED.value,
            "level": KycLevel.NONE.value,
            "error": "KYC service unavailable (fail-closed)"
        }
    else:
        # Default fallback to STANDARD for existing customer or BASIC
        return {
            "status": customer.kyc_status.value if customer.kyc_status else KycStatus.VERIFIED.value,
            "level": customer.kyc_level.value if customer.kyc_level else KycLevel.STANDARD.value,
            "cached": True,
            "warning": "KYC service unavailable; fallback applied"
        }


def check_kyc_limit(customer_level: KycLevel, amount_minor: int) -> Tuple[bool, Optional[str]]:
    """Checks whether the transaction amount is within limits for customer's KYC level."""
    limit = DEFAULT_LIMITS_MINOR.get(customer_level, 0)
    if amount_minor > limit:
        return False, f"Amount {amount_minor/100:.2f} exceeds KYC {customer_level.value} limit of {limit/100:.2f}"
    return True, None
