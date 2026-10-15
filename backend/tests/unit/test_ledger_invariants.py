"""Unit tests for double-entry ledger balance invariants."""
import pytest
from app.services.ledger_service import LedgerInvariantViolation


def check_balanced_entries(entries):
    debits = sum(e["amount_minor"] for e in entries if e["entry_type"] == "DEBIT")
    credits = sum(e["amount_minor"] for e in entries if e["entry_type"] == "CREDIT")
    if debits != credits:
        raise LedgerInvariantViolation(f"Debits ({debits}) != Credits ({credits})")
    return True


def test_balanced_transaction_passes():
    entries = [
        {"entry_type": "DEBIT", "amount_minor": 10000},
        {"entry_type": "CREDIT", "amount_minor": 10000},
    ]
    assert check_balanced_entries(entries) is True


def test_multi_leg_balanced_transaction_with_fee():
    entries = [
        {"entry_type": "DEBIT", "amount_minor": 10250},   # Total from customer
        {"entry_type": "CREDIT", "amount_minor": 10000},  # To merchant
        {"entry_type": "CREDIT", "amount_minor": 250},    # To fee pool
    ]
    assert check_balanced_entries(entries) is True


def test_unbalanced_transaction_raises_invariant_violation():
    entries = [
        {"entry_type": "DEBIT", "amount_minor": 10000},
        {"entry_type": "CREDIT", "amount_minor": 9000},
    ]
    with pytest.raises(LedgerInvariantViolation):
        check_balanced_entries(entries)
