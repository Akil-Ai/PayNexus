"""Message translation playground API endpoint."""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from app.api.v1.auth import get_current_user
from app.models import User
from app.services.translation_service import (
    translate_message, serialize_pain_001, serialize_pacs_008,
    CanonicalPaymentMessage
)

router = APIRouter(prefix="/messages", tags=["messages"])


class TranslateRequest(BaseModel):
    format_type: str = "AUTO"  # AUTO, PAIN_001, ISO_8583, SWIFT_MT103, CSV, JSON
    content: str


class SerializeRequest(BaseModel):
    target_format: str = "PAIN_001"  # PAIN_001, PACS_008
    canonical_message: CanonicalPaymentMessage


@router.post("/translate")
async def translate_incoming_message(
    payload: TranslateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Translates any incoming payment message (ISO 20022 pain.001 XML, ISO 8583 JSON,
    SWIFT MT103, or legacy CSV) into the canonical ISO 20022 internal model.
    """
    try:
        canonical = translate_message(payload.content, payload.format_type)
        return {
            "success": len(canonical.validation_errors) == 0,
            "detected_format": canonical.raw_format,
            "canonical_model": canonical.model_dump(),
            "validation_errors": canonical.validation_errors
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "validation_errors": [str(exc)]
        }


@router.post("/serialize")
async def serialize_canonical_message(
    payload: SerializeRequest,
    current_user: User = Depends(get_current_user)
):
    """Serializes canonical model into requested ISO 20022 XML format."""
    fmt = payload.target_format.upper()
    if fmt == "PAIN_001":
        xml_out = serialize_pain_001(payload.canonical_message)
        return {"format": "PAIN_001_XML", "xml": xml_out}
    elif fmt == "PACS_008":
        xml_out = serialize_pacs_008(payload.canonical_message)
        return {"format": "PACS_008_XML", "xml": xml_out}
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported target format: {fmt}")
