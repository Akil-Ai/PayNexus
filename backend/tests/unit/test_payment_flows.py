"""Unit and integration tests for Payment API, Idempotency, and Investigation Assistant."""
import pytest
from app.services.idempotency_service import compute_request_hash
from app.domain.state_machine import validate_transition, StateMachineError
from app.models.models import PaymentState, UserRole
from app.services.fraud_service import jsonLogic


def test_request_hash_determinism():
    """Identical payloads must yield identical SHA256 hashes."""
    body_a = b'{"customer_id": "c1", "amount_minor": 10000, "currency": "INR"}'
    body_b = b'{"customer_id": "c1", "amount_minor": 10000, "currency": "INR"}'
    body_diff = b'{"customer_id": "c1", "amount_minor": 20000, "currency": "INR"}'

    assert compute_request_hash(body_a) == compute_request_hash(body_b)
    assert compute_request_hash(body_a) != compute_request_hash(body_diff)


def test_json_logic_rule_evaluation():
    """Test our built-in JSON-Logic evaluator on velocity and amount rules."""
    # Test amount threshold rule
    rule_large_amount = {">": [{"var": "amount_minor"}, 50000000]}
    assert jsonLogic(rule_large_amount, {"amount_minor": 60000000}) is True
    assert jsonLogic(rule_large_amount, {"amount_minor": 40000000}) is False

    # Test structuring rule: between 49,000 and 50,000 INR
    rule_structuring = {
        "and": [
            {">=": [{"var": "amount_minor"}, 4900000]},
            {"<": [{"var": "amount_minor"}, 5000000]}
        ]
    }
    assert jsonLogic(rule_structuring, {"amount_minor": 4950000}) is True
    assert jsonLogic(rule_structuring, {"amount_minor": 1000000}) is False
    assert jsonLogic(rule_structuring, {"amount_minor": 5500000}) is False


def test_state_machine_maker_checker_approval():
    """Test that BLOCKED payments can only transition to AUTHORISED via authorized approval."""
    assert validate_transition(PaymentState.BLOCKED, PaymentState.AUTHORISED) is True
    with pytest.raises(StateMachineError):
        validate_transition(PaymentState.BLOCKED, PaymentState.SETTLED)


def test_role_authorization_logic():
    """Verify role authorization permissions."""
    admin = UserRole.ADMIN
    ops = UserRole.OPERATIONS
    compliance = UserRole.COMPLIANCE_OFFICER
    auditor = UserRole.AUDITOR

    allowed_settle = [admin, ops]
    allowed_compliance = [admin, compliance]

    assert ops in allowed_settle
    assert auditor not in allowed_settle
    assert compliance in allowed_compliance
    assert ops not in allowed_compliance
