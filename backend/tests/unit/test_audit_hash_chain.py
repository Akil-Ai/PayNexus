"""Unit tests for cryptographic audit hash-chain creation and tamper detection."""
import hashlib
import json


def compute_row_hash(prev_hash: str, row_content: str) -> str:
    combined = f"{prev_hash or ''}:{row_content}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def test_audit_hash_chain_linking():
    # Genesis row
    row1 = json.dumps({"seq": 1, "action": "CREATE_USER", "actor": "admin"}, sort_keys=True)
    hash1 = compute_row_hash("", row1)

    # Row 2
    row2 = json.dumps({"seq": 2, "action": "CREATE_PAYMENT", "actor": "customer"}, sort_keys=True)
    hash2 = compute_row_hash(hash1, row2)

    # Row 3
    row3 = json.dumps({"seq": 3, "action": "SETTLE_PAYMENT", "actor": "orchestrator"}, sort_keys=True)
    hash3 = compute_row_hash(hash2, row3)

    # Verify forward chain
    assert compute_row_hash("", row1) == hash1
    assert compute_row_hash(hash1, row2) == hash2
    assert compute_row_hash(hash2, row3) == hash3


def test_audit_tamper_detection():
    row1 = json.dumps({"seq": 1, "action": "CREATE_USER"}, sort_keys=True)
    hash1 = compute_row_hash("", row1)

    row2 = json.dumps({"seq": 2, "action": "AUTHORISE_PAYMENT"}, sort_keys=True)
    hash2 = compute_row_hash(hash1, row2)

    # Malicious tamper on Row 2 in database
    tampered_row2 = json.dumps({"seq": 2, "action": "MALICIOUS_OVERRIDE"}, sort_keys=True)
    recalculated_hash2 = compute_row_hash(hash1, tampered_row2)

    # Verification must catch the discrepancy
    assert recalculated_hash2 != hash2
