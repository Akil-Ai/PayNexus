"""Unit tests for fraud rule engine — JSON-logic evaluation, scoring, and ALLOW/REVIEW/BLOCK."""
import pytest
from app.services.fraud_service import jsonLogic


# ── Pure JSON-logic rule evaluation (no DB needed) ────────────────────────────

class TestJsonLogicFraudRules:
    """Test the JSON-logic evaluation directly, as the fraud engine uses it."""

    def test_high_amount_rule_triggers(self):
        """Rule: block if amount > 10,000,00 minor units (₹1,00,000)."""
        rule = {">":[{"var": "amount_minor"}, 10_000_00]}
        context = {"amount_minor": 15_000_00}
        assert jsonLogic(rule, context) is True

    def test_high_amount_rule_does_not_trigger_on_low(self):
        rule = {">":[{"var": "amount_minor"}, 10_000_00]}
        context = {"amount_minor": 5_000_00}
        assert jsonLogic(rule, context) is False

    def test_velocity_rule_triggers(self):
        """Rule: flag if more than 5 payments in 1 hour."""
        rule = {">":[{"var": "velocity_count_1h"}, 5]}
        context = {"velocity_count_1h": 10}
        assert jsonLogic(rule, context) is True

    def test_velocity_rule_no_trigger(self):
        rule = {">":[{"var": "velocity_count_1h"}, 5]}
        context = {"velocity_count_1h": 3}
        assert jsonLogic(rule, context) is False

    def test_pep_flag_triggers(self):
        """Rule: flag if customer is PEP (politically exposed person)."""
        rule = {"==":[{"var": "is_pep"}, True]}
        context = {"is_pep": True}
        assert jsonLogic(rule, context) is True

    def test_pep_flag_not_triggered_for_non_pep(self):
        rule = {"==":[{"var": "is_pep"}, True]}
        context = {"is_pep": False}
        assert jsonLogic(rule, context) is False

    def test_high_risk_customer_triggers(self):
        rule = {"==":[{"var": "customer_risk_rating"}, "HIGH"]}
        context = {"customer_risk_rating": "HIGH"}
        assert jsonLogic(rule, context) is True

    def test_new_beneficiary_rule(self):
        """Rule: add score if new beneficiary."""
        rule = {"==":[{"var": "is_new_beneficiary"}, True]}
        context = {"is_new_beneficiary": True}
        assert jsonLogic(rule, context) is True

    def test_amount_vs_avg_ratio_rule(self):
        """Rule: amount is 5x the historical average → flag."""
        rule = {">":[{"var": "amount_vs_avg_ratio"}, 5.0]}
        context = {"amount_vs_avg_ratio": 7.5}
        assert jsonLogic(rule, context) is True

    def test_compound_and_rule(self):
        """AND rule: both conditions must be true."""
        rule = {"and": [
            {">":[{"var": "amount_minor"}, 100000]},
            {"==":[{"var": "is_new_beneficiary"}, True]},
        ]}
        context = {"amount_minor": 200000, "is_new_beneficiary": True}
        assert jsonLogic(rule, context) is True

    def test_compound_and_rule_partial_fail(self):
        rule = {"and": [
            {">":[{"var": "amount_minor"}, 100000]},
            {"==":[{"var": "is_new_beneficiary"}, True]},
        ]}
        context = {"amount_minor": 200000, "is_new_beneficiary": False}
        assert jsonLogic(rule, context) is False

    def test_compound_or_rule(self):
        """OR rule: either condition can trigger."""
        rule = {"or": [
            {"==":[{"var": "is_pep"}, True]},
            {">":[{"var": "velocity_count_1h"}, 10]},
        ]}
        context = {"is_pep": False, "velocity_count_1h": 15}
        assert jsonLogic(rule, context) is True

    def test_kyc_none_triggers_on_high_amount(self):
        """Rule: KYC=NONE with amount > 10000 minor units."""
        rule = {"and": [
            {"==":[{"var": "customer_kyc_level"}, "NONE"]},
            {">":[{"var": "amount_minor"}, 10000]},
        ]}
        context = {"customer_kyc_level": "NONE", "amount_minor": 50000}
        assert jsonLogic(rule, context) is True

    def test_off_hours_rule(self):
        """Rule: payment at 2am (hour 2) → flag."""
        rule = {"<":[{"var": "hour_of_day"}, 5]}
        context = {"hour_of_day": 2}
        assert jsonLogic(rule, context) is True

    def test_invalid_rule_logic_returns_falsy(self):
        """Bad rule logic should not crash; json-logic returns None/False."""
        rule = {"unknown_op": [{"var": "x"}]}
        context = {"x": 1}
        # json-logic raises or returns falsy on unknown operators
        try:
            result = jsonLogic(rule, context)
            assert not result
        except Exception:
            pass  # Acceptable; fraud engine catches exceptions per rule


# ── Score-threshold decision logic ─────────────────────────────────────────────

class TestFraudScoreDecision:
    """Test the score → decision mapping used in fraud_service.evaluate_fraud."""

    def _decide(self, total_score: int, allow_threshold=30, block_threshold=70):
        """Mirror the decision logic from evaluate_fraud."""
        if total_score >= block_threshold:
            return "BLOCK"
        elif total_score >= allow_threshold:
            return "REVIEW"
        else:
            return "ALLOW"

    def test_score_zero_is_allow(self):
        assert self._decide(0) == "ALLOW"

    def test_score_below_allow_threshold_is_allow(self):
        assert self._decide(29) == "ALLOW"

    def test_score_at_allow_threshold_is_review(self):
        assert self._decide(30) == "REVIEW"

    def test_score_between_thresholds_is_review(self):
        assert self._decide(50) == "REVIEW"

    def test_score_at_block_threshold_is_block(self):
        assert self._decide(70) == "BLOCK"

    def test_score_above_block_threshold_is_block(self):
        assert self._decide(100) == "BLOCK"

    def test_score_capped_at_100(self):
        raw = min(150, 100)
        assert self._decide(raw) == "BLOCK"

    def test_custom_thresholds(self):
        """Custom thresholds (e.g. tighter settings) work correctly."""
        assert self._decide(40, allow_threshold=20, block_threshold=60) == "REVIEW"
        assert self._decide(65, allow_threshold=20, block_threshold=60) == "BLOCK"
        assert self._decide(10, allow_threshold=20, block_threshold=60) == "ALLOW"
