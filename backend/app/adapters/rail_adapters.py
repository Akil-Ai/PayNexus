"""Rail adapters: UPI, NEFT, SWIFT, CARD - hexagonal adapter pattern."""
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Any, Dict, Type

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import rail_requests_total, rail_latency
from app.adapters.circuit_breaker import CircuitBreaker, call_with_retry, RailException

settings = get_settings()
logger = get_logger(__name__)


class RailResponse:
    def __init__(
        self,
        success: bool,
        rail_reference: Optional[str],
        status: str,
        message: str,
        raw_response: Optional[dict] = None,
        settlement_time: Optional[datetime] = None,
    ):
        self.success = success
        self.rail_reference = rail_reference
        self.status = status
        self.message = message
        self.raw_response = raw_response
        self.settlement_time = settlement_time

    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        if self.raw_response and isinstance(self.raw_response, dict) and key in self.raw_response:
            return self.raw_response[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            val = getattr(self, key)
            return val if val is not None else default
        if self.raw_response and isinstance(self.raw_response, dict):
            return self.raw_response.get(key, default)
        return default


class BaseRailAdapter(ABC):
    """Ports-and-adapters interface for all payment rails."""

    rail_code: str
    base_url: str

    def _normalize_payload(self, payment_payload: Any) -> dict:
        if isinstance(payment_payload, dict):
            return payment_payload
        # If it's a Payment model or object
        return {
            "payment_id": getattr(payment_payload, "id", str(uuid.uuid4())),
            "amount_minor": getattr(payment_payload, "amount_minor", 0),
            "currency": getattr(payment_payload, "currency", "INR"),
            "description": getattr(payment_payload, "description", ""),
            "end_to_end_id": getattr(payment_payload, "reference", str(uuid.uuid4())),
            "sender_account_id": getattr(payment_payload, "sender_account_id", None),
            "beneficiary_id": getattr(payment_payload, "beneficiary_id", None),
        }

    @abstractmethod
    async def submit_payment(self, payment_payload: Any) -> RailResponse:
        pass

    @abstractmethod
    async def query_status(self, rail_reference: str) -> RailResponse:
        pass

    @abstractmethod
    async def cancel_payment(self, rail_reference: str) -> RailResponse:
        pass

    async def inquire_status(self, rail_reference: str) -> dict:
        """Convenience method returning status dict."""
        resp = await self.query_status(rail_reference)
        return {
            "status": resp.status,
            "success": resp.success,
            "message": resp.message,
            "rail_reference": resp.rail_reference,
            "raw_response": resp.raw_response,
        }

    def _cb(self) -> CircuitBreaker:
        return CircuitBreaker.for_rail(self.rail_code)


    async def _post(self, path: str, body: dict) -> dict:
        """HTTP POST with circuit breaker and retry."""
        async def _do_post():
            start = datetime.now(timezone.utc)
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(f"{self.base_url}{path}", json=body)
                    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
                    rail_latency.labels(rail=self.rail_code).observe(elapsed)
                    if resp.status_code >= 500:
                        rail_requests_total.labels(rail=self.rail_code, result="FAILURE").inc()
                        raise RailException(self.rail_code, resp.status_code, resp.text)
                    rail_requests_total.labels(rail=self.rail_code, result="SUCCESS").inc()
                    return resp.json()
            except httpx.TimeoutException:
                rail_requests_total.labels(rail=self.rail_code, result="TIMEOUT").inc()
                raise RailException(self.rail_code, 504, "Rail timeout")
            except RailException:
                raise
            except Exception as e:
                rail_requests_total.labels(rail=self.rail_code, result="FAILURE").inc()
                raise RailException(self.rail_code, 500, str(e))

        return await call_with_retry(_do_post, rail_code=self.rail_code, circuit_breaker=self._cb())


class UPIAdapter(BaseRailAdapter):
    rail_code = "UPI"

    def __init__(self):
        self.base_url = settings.rail_upi_url

    async def submit_payment(self, payment_payload: Any) -> RailResponse:
        payment_payload = self._normalize_payload(payment_payload)
        body = {
            "txnId": payment_payload["payment_id"],
            "amount": payment_payload["amount_minor"],
            "currency": payment_payload["currency"],
            "payerVpa": payment_payload.get("sender_vpa", "sender@upi"),
            "payeeVpa": payment_payload.get("beneficiary_vpa", "payee@upi"),
            "description": payment_payload.get("description", ""),
            "endToEndId": payment_payload.get("end_to_end_id", str(uuid.uuid4())),
        }
        try:
            resp = await self._post("/payment/initiate", body)
            return RailResponse(
                success=resp.get("status") == "SUCCESS",
                rail_reference=resp.get("rrn") or resp.get("txnId"),
                status=resp.get("status", "UNKNOWN"),
                message=resp.get("message", ""),
                raw_response=resp,
            )
        except RailException as e:
            return RailResponse(False, None, "FAILED", str(e), None)

    async def query_status(self, rail_reference: str) -> RailResponse:
        resp = await self._post("/payment/status", {"rrn": rail_reference})
        return RailResponse(
            success=resp.get("status") == "SUCCESS",
            rail_reference=rail_reference,
            status=resp.get("status", "UNKNOWN"),
            message=resp.get("message", ""),
            raw_response=resp,
        )

    async def cancel_payment(self, rail_reference: str) -> RailResponse:
        resp = await self._post("/payment/cancel", {"rrn": rail_reference})
        return RailResponse(
            success=resp.get("status") == "CANCELLED",
            rail_reference=rail_reference,
            status=resp.get("status", "UNKNOWN"),
            message=resp.get("message", ""),
            raw_response=resp,
        )


class NEFTAdapter(BaseRailAdapter):
    rail_code = "NEFT"

    def __init__(self):
        self.base_url = settings.rail_neft_url

    async def submit_payment(self, payment_payload: Any) -> RailResponse:
        payment_payload = self._normalize_payload(payment_payload)
        body = {
            "txnId": payment_payload["payment_id"],
            "amount": payment_payload["amount_minor"],
            "currency": payment_payload["currency"],
            "senderIfsc": payment_payload.get("sender_ifsc", "DEMO0001"),
            "senderAccount": payment_payload.get("sender_account_masked", "****1234"),
            "beneficiaryIfsc": payment_payload.get("beneficiary_ifsc", "DEMO0002"),
            "beneficiaryAccount": payment_payload.get("beneficiary_account_masked", "****5678"),
            "beneficiaryName": payment_payload.get("beneficiary_name", "Payee"),
            "description": payment_payload.get("description", ""),
        }
        try:
            resp = await self._post("/neft/submit", body)
            return RailResponse(
                success=resp.get("status") in ("ACCEPTED", "PENDING", "SETTLED", "SUCCESS"),
                rail_reference=resp.get("utr") or resp.get("txnId"),
                status=resp.get("status", "UNKNOWN"),
                message=resp.get("message", ""),
                raw_response=resp,
            )
        except RailException as e:
            return RailResponse(False, None, "FAILED", str(e), None)

    async def query_status(self, rail_reference: str) -> RailResponse:
        resp = await self._post("/neft/status", {"utr": rail_reference})
        return RailResponse(
            success=resp.get("status") == "SETTLED",
            rail_reference=rail_reference,
            status=resp.get("status", "UNKNOWN"),
            message=resp.get("message", ""),
            raw_response=resp,
        )

    async def cancel_payment(self, rail_reference: str) -> RailResponse:
        resp = await self._post("/neft/cancel", {"utr": rail_reference})
        return RailResponse(
            success=True,
            rail_reference=rail_reference,
            status="CANCELLED",
            message="Cancelled",
            raw_response=resp,
        )


class SWIFTAdapter(BaseRailAdapter):
    rail_code = "SWIFT"

    def __init__(self):
        self.base_url = settings.rail_swift_url

    async def submit_payment(self, payment_payload: Any) -> RailResponse:
        payment_payload = self._normalize_payload(payment_payload)
        body = {
            "msgId": payment_payload["payment_id"],
            "amount": payment_payload["amount_minor"],
            "currency": payment_payload["currency"],
            "debtorIban": payment_payload.get("sender_iban", "GB00DEMO0000001"),
            "debtorBic": payment_payload.get("sender_bic", "DEMOXXXX"),
            "creditorIban": payment_payload.get("beneficiary_iban", "DE00DEMO0000001"),
            "creditorBic": payment_payload.get("beneficiary_bic", "DEMODEXX"),
            "creditorName": payment_payload.get("beneficiary_name", "Payee"),
            "remittanceInfo": payment_payload.get("description", ""),
            "endToEndId": payment_payload.get("end_to_end_id", str(uuid.uuid4())),
        }
        try:
            resp = await self._post("/pacs008/submit", body)
            return RailResponse(
                success=resp.get("status") in ("ACCP", "ACSC", "SETTLED", "SUCCESS"),
                rail_reference=resp.get("txId") or resp.get("msgId"),
                status=resp.get("status", "UNKNOWN"),
                message=resp.get("message", ""),
                raw_response=resp,
            )
        except RailException as e:
            return RailResponse(False, None, "FAILED", str(e), None)

    async def query_status(self, rail_reference: str) -> RailResponse:
        resp = await self._post("/pacs002/status", {"txId": rail_reference})
        return RailResponse(
            success=resp.get("txSts") == "ACSC",
            rail_reference=rail_reference,
            status=resp.get("txSts", "UNKNOWN"),
            message=resp.get("stsRsnInf", ""),
            raw_response=resp,
        )

    async def cancel_payment(self, rail_reference: str) -> RailResponse:
        resp = await self._post("/camt056/cancel", {"txId": rail_reference})
        return RailResponse(
            success=True,
            rail_reference=rail_reference,
            status="CANCELLED",
            message="Cancellation requested",
            raw_response=resp,
        )


class CARDAdapter(BaseRailAdapter):
    rail_code = "CARD"

    def __init__(self):
        self.base_url = settings.rail_card_url

    async def submit_payment(self, payment_payload: Any) -> RailResponse:
        payment_payload = self._normalize_payload(payment_payload)
        """Card uses auth + capture flow."""
        auth_body = {
            "merchantId": "PAYNEXUS_MERCHANT",
            "amount": payment_payload["amount_minor"],
            "currency": payment_payload["currency"],
            "cardToken": payment_payload.get("card_token", "tok_demo_visa"),
            "orderId": payment_payload["payment_id"],
            "description": payment_payload.get("description", ""),
        }
        try:
            auth_resp = await self._post("/authorize", auth_body)
            auth_code = auth_resp.get("authCode")
            if not auth_code:
                return RailResponse(False, None, "DECLINED", auth_resp.get("message", "Auth declined"), auth_resp)

            # Capture
            cap_resp = await self._post("/capture", {
                "authCode": auth_code,
                "amount": payment_payload["amount_minor"],
            })
            return RailResponse(
                success=cap_resp.get("status") == "CAPTURED",
                rail_reference=cap_resp.get("settleId") or auth_code,
                status=cap_resp.get("status", "UNKNOWN"),
                message=cap_resp.get("message", ""),
                raw_response=cap_resp,
            )
        except RailException as e:
            return RailResponse(False, None, "FAILED", str(e), None)

    async def query_status(self, rail_reference: str) -> RailResponse:
        resp = await self._post("/status", {"settleId": rail_reference})
        return RailResponse(
            success=resp.get("status") == "CAPTURED",
            rail_reference=rail_reference,
            status=resp.get("status", "UNKNOWN"),
            message=resp.get("message", ""),
            raw_response=resp,
        )

    async def cancel_payment(self, rail_reference: str) -> RailResponse:
        resp = await self._post("/void", {"settleId": rail_reference})
        return RailResponse(
            success=True,
            rail_reference=rail_reference,
            status="VOIDED",
            message="Voided",
            raw_response=resp,
        )


# Rail registry
RAIL_ADAPTERS: Dict[str, Type[BaseRailAdapter]] = {
    "UPI": UPIAdapter,
    "NEFT": NEFTAdapter,
    "SWIFT": SWIFTAdapter,
    "CARD": CARDAdapter,
}


def get_rail_adapter(rail_code: str) -> BaseRailAdapter:
    adapter_cls = RAIL_ADAPTERS.get(rail_code.upper())
    if not adapter_cls:
        raise ValueError(f"Unknown rail: {rail_code}")
    return adapter_cls()
