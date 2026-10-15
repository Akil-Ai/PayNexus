"""Initial schema - all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-10-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Install pg_trgm for fuzzy name search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ── Enums ──────────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE paymentstate AS ENUM ('CREATED','VALIDATED','SCREENING','REVIEW','BLOCKED','AUTHORISED','SUBMITTED','SETTLED','FAILED','REVERSED','REFUNDED','PARTIALLY_REFUNDED','CANCELLED','EXPIRED')")
    op.execute("CREATE TYPE userrole AS ENUM ('ADMIN','OPERATIONS','COMPLIANCE_OFFICER','AUDITOR','MERCHANT','API_CLIENT')")
    op.execute("CREATE TYPE kycstatus AS ENUM ('PENDING','VERIFIED','REJECTED','EXPIRED')")
    op.execute("CREATE TYPE kyclevel AS ENUM ('NONE','BASIC','STANDARD','ENHANCED')")
    op.execute("CREATE TYPE screeningresult AS ENUM ('PASS','REVIEW','BLOCKED')")
    op.execute("CREATE TYPE frauddecision AS ENUM ('ALLOW','REVIEW','BLOCK')")
    op.execute("CREATE TYPE ledgerentrytype AS ENUM ('DEBIT','CREDIT')")
    op.execute("CREATE TYPE exceptiontype AS ENUM ('MISSING_AT_RAIL','MISSING_INTERNALLY','AMOUNT_MISMATCH','DUPLICATE','STATUS_MISMATCH','TIMING_MISMATCH','FEE_MISMATCH','CURRENCY_MISMATCH')")
    op.execute("CREATE TYPE exceptionstatus AS ENUM ('OPEN','IN_REVIEW','RESOLVED','ESCALATED')")
    op.execute("CREATE TYPE reconconstatus AS ENUM ('MATCHED','UNMATCHED','PARTIAL','EXCEPTION')")
    op.execute("CREATE TYPE approvalstatus AS ENUM ('PENDING','APPROVED','REJECTED')")

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("ADMIN","OPERATIONS","COMPLIANCE_OFFICER","AUDITOR","MERCHANT","API_CLIENT", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── api_clients ────────────────────────────────────────────────────────────
    op.create_table(
        "api_clients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("api_key_hash", sa.String(255), nullable=False),
        sa.Column("api_key_prefix", sa.String(12), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("rate_limit_per_minute", sa.Integer, server_default="60"),
        sa.Column("allowed_ips", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_api_clients_api_key_hash", "api_clients", ["api_key_hash"], unique=True)

    # ── customers ──────────────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_id", sa.String(100)),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("date_of_birth", sa.String(20)),
        sa.Column("nationality", sa.String(3)),
        sa.Column("country_of_residence", sa.String(3)),
        sa.Column("kyc_status", sa.Enum("PENDING","VERIFIED","REJECTED","EXPIRED", name="kycstatus"), server_default="PENDING"),
        sa.Column("kyc_level", sa.Enum("NONE","BASIC","STANDARD","ENHANCED", name="kyclevel"), server_default="NONE"),
        sa.Column("risk_rating", sa.String(20)),
        sa.Column("is_pep", sa.Boolean, server_default="false"),
        sa.Column("is_sanctioned", sa.Boolean, server_default="false"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_customers_external_id", "customers", ["external_id"], unique=True)
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_index("ix_customers_name_trgm", "customers", ["full_name"], postgresql_using="gin",
                    postgresql_ops={"full_name": "gin_trgm_ops"})

    # ── kyc_records ────────────────────────────────────────────────────────────
    op.create_table(
        "kyc_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("provider_reference", sa.String(255)),
        sa.Column("kyc_level", sa.Enum("NONE","BASIC","STANDARD","ENHANCED", name="kyclevel"), nullable=False),
        sa.Column("status", sa.Enum("PENDING","VERIFIED","REJECTED","EXPIRED", name="kycstatus"), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("raw_response", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_kyc_records_customer_id", "kyc_records", ["customer_id"])

    # ── accounts ───────────────────────────────────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("account_number_encrypted", sa.Text, nullable=False),
        sa.Column("account_number_masked", sa.String(20), nullable=False),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("bank_code", sa.String(50)),
        sa.Column("ifsc_code", sa.String(20)),
        sa.Column("swift_bic", sa.String(15)),
        sa.Column("iban", sa.String(34)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("length(currency) = 3", name="ck_accounts_currency_len"),
    )
    op.create_index("ix_accounts_customer_id", "accounts", ["customer_id"])

    # ── beneficiaries ──────────────────────────────────────────────────────────
    op.create_table(
        "beneficiaries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("account_number_encrypted", sa.Text, nullable=False),
        sa.Column("account_number_masked", sa.String(20), nullable=False),
        sa.Column("bank_name", sa.String(255)),
        sa.Column("bank_code", sa.String(50)),
        sa.Column("ifsc_code", sa.String(20)),
        sa.Column("swift_bic", sa.String(15)),
        sa.Column("iban", sa.String(34)),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("country", sa.String(3)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_new", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_beneficiaries_customer_id", "beneficiaries", ["customer_id"])

    # ── rails ──────────────────────────────────────────────────────────────────
    op.create_table(
        "rails",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("timeout_seconds", sa.Integer, server_default="30"),
        sa.Column("max_retries", sa.Integer, server_default="3"),
        sa.Column("retry_backoff_base", sa.Numeric(10, 4), server_default="1.5"),
        sa.Column("circuit_breaker_threshold", sa.Integer, server_default="5"),
        sa.Column("circuit_breaker_timeout_seconds", sa.Integer, server_default="60"),
        sa.Column("supported_currencies", sa.Text),
        sa.Column("min_amount_minor", sa.BigInteger, server_default="1"),
        sa.Column("max_amount_minor", sa.BigInteger, server_default="10000000000"),
        sa.Column("settlement_hours", sa.Integer, server_default="0"),
        sa.Column("fee_fixed_minor", sa.BigInteger, server_default="0"),
        sa.Column("fee_percent", sa.Numeric(10, 6)),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── routing_rules ──────────────────────────────────────────────────────────
    op.create_table(
        "routing_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rail_id", sa.String(36), sa.ForeignKey("rails.id"), nullable=False),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("currency", sa.String(3)),
        sa.Column("country_sender", sa.String(3)),
        sa.Column("country_receiver", sa.String(3)),
        sa.Column("min_amount_minor", sa.BigInteger),
        sa.Column("max_amount_minor", sa.BigInteger),
        sa.Column("payment_type", sa.String(50)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── payments ───────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reference", sa.String(100), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(255)),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("beneficiary_id", sa.String(36), sa.ForeignKey("beneficiaries.id")),
        sa.Column("sender_account_id", sa.String(36), sa.ForeignKey("accounts.id")),
        sa.Column("rail_id", sa.String(36), sa.ForeignKey("rails.id")),
        sa.Column("amount_minor", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("fee_minor", sa.BigInteger, server_default="0"),
        sa.Column("amount_settled_minor", sa.BigInteger),
        sa.Column("state", sa.Enum("CREATED","VALIDATED","SCREENING","REVIEW","BLOCKED","AUTHORISED","SUBMITTED","SETTLED","FAILED","REVERSED","REFUNDED","PARTIALLY_REFUNDED","CANCELLED","EXPIRED", name="paymentstate"), nullable=False, server_default="CREATED"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("payment_type", sa.String(50), server_default="CREDIT_TRANSFER"),
        sa.Column("urgency", sa.String(20), server_default="NORMAL"),
        sa.Column("description", sa.Text),
        sa.Column("end_to_end_id", sa.String(100)),
        sa.Column("rail_reference", sa.String(255)),
        sa.Column("screening_status", sa.Enum("PASS","REVIEW","BLOCKED", name="screeningresult")),
        sa.Column("fraud_decision", sa.Enum("ALLOW","REVIEW","BLOCK", name="frauddecision")),
        sa.Column("fraud_score", sa.Integer),
        sa.Column("parent_payment_id", sa.String(36), sa.ForeignKey("payments.id")),
        sa.Column("refunded_amount_minor", sa.BigInteger, server_default="0"),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("settled_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("amount_minor > 0", name="ck_payments_amount_positive"),
        sa.CheckConstraint("fee_minor >= 0", name="ck_payments_fee_nonneg"),
        sa.CheckConstraint("length(currency) = 3", name="ck_payments_currency_len"),
        sa.CheckConstraint("version > 0", name="ck_payments_version_positive"),
    )
    op.create_index("ix_payments_reference", "payments", ["reference"], unique=True)
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"])
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"])
    op.create_index("ix_payments_state", "payments", ["state"])
    op.create_index("ix_payments_state_created", "payments", ["state", "created_at"])
    op.create_index("ix_payments_customer_state", "payments", ["customer_id", "state"])
    op.create_index("ix_payments_rail_reference", "payments", ["rail_reference"])

    # ── payment_state_history ──────────────────────────────────────────────────
    op.create_table(
        "payment_state_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("from_state", sa.Enum("CREATED","VALIDATED","SCREENING","REVIEW","BLOCKED","AUTHORISED","SUBMITTED","SETTLED","FAILED","REVERSED","REFUNDED","PARTIALLY_REFUNDED","CANCELLED","EXPIRED", name="paymentstate")),
        sa.Column("to_state", sa.Enum("CREATED","VALIDATED","SCREENING","REVIEW","BLOCKED","AUTHORISED","SUBMITTED","SETTLED","FAILED","REVERSED","REFUNDED","PARTIALLY_REFUNDED","CANCELLED","EXPIRED", name="paymentstate"), nullable=False),
        sa.Column("actor_id", sa.String(36)),
        sa.Column("actor_type", sa.String(50), server_default="SYSTEM"),
        sa.Column("reason", sa.Text),
        sa.Column("correlation_id", sa.String(36)),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_psh_payment_id", "payment_state_history", ["payment_id"])

    # ── payment_messages ───────────────────────────────────────────────────────
    op.create_table(
        "payment_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("format", sa.String(50), nullable=False),
        sa.Column("raw_content", sa.Text, nullable=False),
        sa.Column("canonical_content", postgresql.JSONB),
        sa.Column("validation_errors", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pm_payment_id", "payment_messages", ["payment_id"])

    # ── idempotency_keys ───────────────────────────────────────────────────────
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("response_status", sa.Integer),
        sa.Column("response_body", postgresql.JSONB),
        sa.Column("payment_id", sa.String(36)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("key", "endpoint", name="uq_idempotency_keys_key_endpoint"),
    )
    op.create_index("ix_idempotency_keys_expires", "idempotency_keys", ["expires_at"])

    # ── ledger_accounts ────────────────────────────────────────────────────────
    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("accounts.id"), unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_system", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── ledger_entries ─────────────────────────────────────────────────────────
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("debit_account_id", sa.String(36), sa.ForeignKey("ledger_accounts.id"), nullable=False),
        sa.Column("credit_account_id", sa.String(36), sa.ForeignKey("ledger_accounts.id"), nullable=False),
        sa.Column("amount_minor", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("entry_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("amount_minor > 0", name="ck_ledger_entries_amount_positive"),
        sa.CheckConstraint("debit_account_id != credit_account_id", name="ck_ledger_entries_no_self"),
    )
    op.create_index("ix_le_payment_id", "ledger_entries", ["payment_id"])

    # ── holds ──────────────────────────────────────────────────────────────────
    op.create_table(
        "holds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("ledger_account_id", sa.String(36), sa.ForeignKey("ledger_accounts.id"), nullable=False),
        sa.Column("amount_minor", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_released", sa.Boolean, server_default="false"),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_holds_payment_id", "holds", ["payment_id"])

    # ── fees ───────────────────────────────────────────────────────────────────
    op.create_table(
        "fees",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("fee_type", sa.String(50), nullable=False),
        sa.Column("amount_minor", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fees_payment_id", "fees", ["payment_id"])

    # ── watchlists ─────────────────────────────────────────────────────────────
    op.create_table(
        "watchlists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_updated", sa.DateTime(timezone=True)),
        sa.Column("entry_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── watchlist_entries ──────────────────────────────────────────────────────
    op.create_table(
        "watchlist_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("watchlist_id", sa.String(36), sa.ForeignKey("watchlists.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("aliases", sa.Text),
        sa.Column("date_of_birth", sa.String(20)),
        sa.Column("nationality", sa.String(3)),
        sa.Column("entity_type", sa.String(50), server_default="INDIVIDUAL"),
        sa.Column("reason", sa.Text),
        sa.Column("reference_id", sa.String(100)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_watchlist_entries_watchlist_id", "watchlist_entries", ["watchlist_id"])
    op.create_index("ix_watchlist_entries_name", "watchlist_entries", ["name"])
    op.create_index("ix_watchlist_entries_name_trgm", "watchlist_entries", ["name"],
                    postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"})

    # ── screening_results ──────────────────────────────────────────────────────
    op.create_table(
        "screening_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("screening_type", sa.String(50), nullable=False),
        sa.Column("subject_type", sa.String(20), nullable=False),
        sa.Column("subject_name", sa.String(255), nullable=False),
        sa.Column("result", sa.Enum("PASS","REVIEW","BLOCKED", name="screeningresult"), nullable=False),
        sa.Column("score", sa.Numeric(5, 2)),
        sa.Column("matched_entry_id", sa.String(36)),
        sa.Column("matched_name", sa.String(255)),
        sa.Column("threshold_used", sa.Numeric(5, 2)),
        sa.Column("provider", sa.String(100)),
        sa.Column("raw_response", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_screening_results_payment_id", "screening_results", ["payment_id"])

    # ── fraud_rules ────────────────────────────────────────────────────────────
    op.create_table(
        "fraud_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("rule_logic", postgresql.JSONB, nullable=False),
        sa.Column("score_contribution", sa.Integer, server_default="20"),
        sa.Column("decision", sa.Enum("ALLOW","REVIEW","BLOCK", name="frauddecision"), server_default="REVIEW"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("tags", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── fraud_decisions ────────────────────────────────────────────────────────
    op.create_table(
        "fraud_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("decision", sa.Enum("ALLOW","REVIEW","BLOCK", name="frauddecision"), nullable=False),
        sa.Column("total_score", sa.Integer, nullable=False),
        sa.Column("ml_score", sa.Numeric(5, 4)),
        sa.Column("triggered_rules", postgresql.JSONB),
        sa.Column("reasons", postgresql.JSONB),
        sa.Column("allow_threshold", sa.Integer, nullable=False),
        sa.Column("block_threshold", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fraud_decisions_payment_id", "fraud_decisions", ["payment_id"])

    # ── outbox_events ──────────────────────────────────────────────────────────
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("aggregate_type", sa.String(50), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("published", sa.Boolean, server_default="false"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("stream_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_outbox_events_published", "outbox_events", ["published", "created_at"])
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"])

    # ── dlq_events ─────────────────────────────────────────────────────────────
    op.create_table(
        "dlq_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("original_stream", sa.String(100), nullable=False),
        sa.Column("original_message_id", sa.String(255)),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("failure_reason", sa.Text, nullable=False),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("last_retry_at", sa.DateTime(timezone=True)),
        sa.Column("resolved", sa.Boolean, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── recon_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "recon_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rail_id", sa.String(36), sa.ForeignKey("rails.id")),
        sa.Column("run_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), server_default="RUNNING"),
        sa.Column("total_items", sa.Integer, server_default="0"),
        sa.Column("matched_count", sa.Integer, server_default="0"),
        sa.Column("unmatched_count", sa.Integer, server_default="0"),
        sa.Column("exception_count", sa.Integer, server_default="0"),
        sa.Column("matched_value_minor", sa.BigInteger, server_default="0"),
        sa.Column("total_value_minor", sa.BigInteger, server_default="0"),
        sa.Column("match_rate", sa.Numeric(5, 4)),
        sa.Column("duration_seconds", sa.Numeric(10, 2)),
        sa.Column("created_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    # ── recon_files ────────────────────────────────────────────────────────────
    op.create_table(
        "recon_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("recon_runs.id"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("format", sa.String(50), nullable=False),
        sa.Column("file_size_bytes", sa.Integer),
        sa.Column("row_count", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_recon_files_run_id", "recon_files", ["run_id"])

    # ── recon_items ────────────────────────────────────────────────────────────
    op.create_table(
        "recon_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("recon_runs.id"), nullable=False),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id")),
        sa.Column("rail_reference", sa.String(255)),
        sa.Column("internal_amount_minor", sa.BigInteger),
        sa.Column("rail_amount_minor", sa.BigInteger),
        sa.Column("currency", sa.String(3)),
        sa.Column("status", sa.Enum("MATCHED","UNMATCHED","PARTIAL","EXCEPTION", name="reconconstatus"), nullable=False),
        sa.Column("match_type", sa.String(50)),
        sa.Column("exception_type", sa.Enum("MISSING_AT_RAIL","MISSING_INTERNALLY","AMOUNT_MISMATCH","DUPLICATE","STATUS_MISMATCH","TIMING_MISMATCH","FEE_MISMATCH","CURRENCY_MISMATCH", name="exceptiontype")),
        sa.Column("exception_details", postgresql.JSONB),
        sa.Column("rail_record", postgresql.JSONB),
        sa.Column("auto_resolved", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_recon_items_run_id", "recon_items", ["run_id"])

    # ── exception_cases ────────────────────────────────────────────────────────
    op.create_table(
        "exception_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_number", sa.String(50), nullable=False, unique=True),
        sa.Column("exception_type", sa.Enum("MISSING_AT_RAIL","MISSING_INTERNALLY","AMOUNT_MISMATCH","DUPLICATE","STATUS_MISMATCH","TIMING_MISMATCH","FEE_MISMATCH","CURRENCY_MISMATCH", name="exceptiontype"), nullable=False),
        sa.Column("status", sa.Enum("OPEN","IN_REVIEW","RESOLVED","ESCALATED", name="exceptionstatus"), server_default="OPEN"),
        sa.Column("priority", sa.Integer, server_default="3"),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id")),
        sa.Column("recon_item_id", sa.String(36), sa.ForeignKey("recon_items.id")),
        sa.Column("dlq_event_id", sa.String(36), sa.ForeignKey("dlq_events.id")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("assigned_to", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("resolution_code", sa.String(100)),
        sa.Column("resolution_notes", sa.Text),
        sa.Column("sla_deadline", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_exception_cases_status", "exception_cases", ["status"])
    op.create_index("ix_exception_cases_type", "exception_cases", ["exception_type"])

    # ── case_comments ──────────────────────────────────────────────────────────
    op.create_table(
        "case_comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("exception_cases.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("comment", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_case_comments_case_id", "case_comments", ["case_id"])

    # ── approvals ──────────────────────────────────────────────────────────────
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("exception_cases.id")),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id")),
        sa.Column("approval_type", sa.String(50), nullable=False),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("status", sa.Enum("PENDING","APPROVED","REJECTED", name="approvalstatus"), server_default="PENDING"),
        sa.Column("notes", sa.Text),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── webhook_subscriptions ──────────────────────────────────────────────────
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("events", sa.Text, nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── webhook_deliveries ─────────────────────────────────────────────────────
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subscription_id", sa.String(36), sa.ForeignKey("webhook_subscriptions.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("http_status", sa.Integer),
        sa.Column("attempt_count", sa.Integer, server_default="1"),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_webhook_deliveries_subscription_id", "webhook_deliveries", ["subscription_id"])

    # ── audit_log ──────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sequence", sa.BigInteger, nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("actor_id", sa.String(36)),
        sa.Column("actor_type", sa.String(50), server_default="SYSTEM"),
        sa.Column("correlation_id", sa.String(36)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("old_values", postgresql.JSONB),
        sa.Column("new_values", postgresql.JSONB),
        sa.Column("prev_hash", sa.String(64)),
        sa.Column("row_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_log_sequence", "audit_log", ["sequence"])
    op.create_index("ix_audit_log_created", "audit_log", ["created_at"])

    # ── system_settings ────────────────────────────────────────────────────────
    op.create_table(
        "system_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(255), nullable=False, unique=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("value_type", sa.String(50), server_default="string"),
        sa.Column("is_secret", sa.Boolean, server_default="false"),
        sa.Column("updated_by", sa.String(36)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Audit log immutability trigger ─────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Modification of audit_log is not permitted: immutable audit trail';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_log_immutable
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
    """)

    # ── Audit sequence ─────────────────────────────────────────────────────────
    op.execute("CREATE SEQUENCE IF NOT EXISTS audit_log_seq START 1")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_modification()")
    op.execute("DROP SEQUENCE IF EXISTS audit_log_seq")

    tables = [
        "system_settings", "audit_log", "webhook_deliveries", "webhook_subscriptions",
        "approvals", "case_comments", "exception_cases", "recon_items", "recon_files",
        "recon_runs", "dlq_events", "outbox_events", "fraud_decisions", "fraud_rules",
        "screening_results", "watchlist_entries", "watchlists", "fees", "holds",
        "ledger_entries", "ledger_accounts", "idempotency_keys", "payment_messages",
        "payment_state_history", "payments", "routing_rules", "rails",
        "beneficiaries", "accounts", "kyc_records", "customers", "api_clients", "users",
    ]
    for table in tables:
        op.drop_table(table)

    for enum_name in [
        "paymentstate", "userrole", "kycstatus", "kyclevel", "screeningresult",
        "frauddecision", "ledgerentrytype", "exceptiontype", "exceptionstatus",
        "reconconstatus", "approvalstatus",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
