"""Payment state machine with allowed transitions stored in DB/config."""
from typing import Dict, Set, Optional

from app.models import PaymentState

# Transition table: {from_state: {valid_to_states}}
# This is the canonical definition; it's also written to system_settings
# so operators can view it (though changing it requires a deployment).
ALLOWED_TRANSITIONS: Dict[PaymentState, Set[PaymentState]] = {
    PaymentState.CREATED: {
        PaymentState.VALIDATED,
        PaymentState.CANCELLED,
        PaymentState.FAILED,
    },
    PaymentState.VALIDATED: {
        PaymentState.SCREENING,
        PaymentState.CANCELLED,
        PaymentState.FAILED,
    },
    PaymentState.SCREENING: {
        PaymentState.REVIEW,
        PaymentState.BLOCKED,
        PaymentState.AUTHORISED,
        PaymentState.FAILED,
    },
    PaymentState.REVIEW: {
        PaymentState.AUTHORISED,
        PaymentState.BLOCKED,
        PaymentState.CANCELLED,
        PaymentState.FAILED,
    },
    PaymentState.BLOCKED: {
        PaymentState.AUTHORISED,  # After maker-checker approval
        PaymentState.CANCELLED,
    },
    PaymentState.AUTHORISED: {
        PaymentState.SUBMITTED,
        PaymentState.CANCELLED,
        PaymentState.FAILED,
    },
    PaymentState.SUBMITTED: {
        PaymentState.SETTLED,
        PaymentState.FAILED,
        PaymentState.EXPIRED,
    },
    PaymentState.SETTLED: {
        PaymentState.REVERSED,
        PaymentState.REFUNDED,
        PaymentState.PARTIALLY_REFUNDED,
    },
    PaymentState.FAILED: {
        PaymentState.REVERSED,  # Recovery path
    },
    PaymentState.REVERSED: set(),
    PaymentState.REFUNDED: set(),
    PaymentState.PARTIALLY_REFUNDED: {
        PaymentState.REFUNDED,  # Can be fully refunded after partial
    },
    PaymentState.CANCELLED: set(),
    PaymentState.EXPIRED: set(),
}

# Terminal states (no further transitions)
TERMINAL_STATES: Set[PaymentState] = {
    PaymentState.SETTLED,
    PaymentState.REVERSED,
    PaymentState.REFUNDED,
    PaymentState.CANCELLED,
    PaymentState.EXPIRED,
}

# States where payment is active / needs processing
ACTIVE_STATES: Set[PaymentState] = {
    PaymentState.CREATED,
    PaymentState.VALIDATED,
    PaymentState.SCREENING,
    PaymentState.AUTHORISED,
    PaymentState.SUBMITTED,
}

# States requiring compliance review
COMPLIANCE_HOLD_STATES: Set[PaymentState] = {
    PaymentState.REVIEW,
    PaymentState.BLOCKED,
}


class StateMachineError(Exception):
    """Raised when an illegal state transition is attempted."""
    def __init__(self, from_state: PaymentState, to_state: PaymentState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Illegal transition: {from_state.value} -> {to_state.value}. "
            f"Allowed from {from_state.value}: "
            f"{[s.value for s in ALLOWED_TRANSITIONS.get(from_state, set())]}"
        )


def validate_transition(from_state: PaymentState, to_state: PaymentState) -> bool:
    """Raise StateMachineError if transition is not allowed. Return True if valid."""
    allowed = ALLOWED_TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        raise StateMachineError(from_state, to_state)
    return True


def is_terminal(state: PaymentState) -> bool:
    return state in TERMINAL_STATES


# Alias for compatibility
is_terminal_state = is_terminal


def get_allowed_next_states(state: PaymentState) -> Set[PaymentState]:
    return ALLOWED_TRANSITIONS.get(state, set())


def get_transition_table() -> dict:
    """Return serializable transition table for UI and settings."""
    return {
        state.value: [s.value for s in nexts]
        for state, nexts in ALLOWED_TRANSITIONS.items()
    }
