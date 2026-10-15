"""Unit tests for the payment transaction state machine."""
import pytest
from app.domain.state_machine import (
    validate_transition, is_terminal_state, StateMachineError
)
from app.models.models import PaymentState


def test_valid_forward_transitions():
    """Verify happy-path state transitions."""
    assert validate_transition(PaymentState.CREATED, PaymentState.VALIDATED) is True
    assert validate_transition(PaymentState.VALIDATED, PaymentState.SCREENING) is True
    assert validate_transition(PaymentState.SCREENING, PaymentState.AUTHORISED) is True
    assert validate_transition(PaymentState.AUTHORISED, PaymentState.SUBMITTED) is True
    assert validate_transition(PaymentState.SUBMITTED, PaymentState.SETTLED) is True


def test_compliance_branch_transitions():
    """Verify screening review and blocked states."""
    assert validate_transition(PaymentState.SCREENING, PaymentState.REVIEW) is True
    assert validate_transition(PaymentState.SCREENING, PaymentState.BLOCKED) is True
    assert validate_transition(PaymentState.REVIEW, PaymentState.AUTHORISED) is True
    assert validate_transition(PaymentState.REVIEW, PaymentState.BLOCKED) is True


def test_illegal_transitions_raise_error():
    """Verify invalid transitions raise StateMachineError."""
    with pytest.raises(StateMachineError):
        validate_transition(PaymentState.CREATED, PaymentState.SETTLED)

    with pytest.raises(StateMachineError):
        validate_transition(PaymentState.SETTLED, PaymentState.CREATED)

    with pytest.raises(StateMachineError):
        validate_transition(PaymentState.BLOCKED, PaymentState.SETTLED)


def test_terminal_states():
    """Verify terminal state detection."""
    assert is_terminal_state(PaymentState.SETTLED) is True
    assert is_terminal_state(PaymentState.CANCELLED) is True
    assert is_terminal_state(PaymentState.EXPIRED) is True
    assert is_terminal_state(PaymentState.CREATED) is False
    assert is_terminal_state(PaymentState.SUBMITTED) is False
