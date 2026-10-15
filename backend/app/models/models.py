"""All SQLAlchemy ORM models for PayNexus."""
import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, Enum, ForeignKey,
    Index, Integer, Numeric, String, Text, UniqueConstraint, JSON, LargeBinary,
    func, text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB

# Cross-dialect types that compile cleanly to PostgreSQL in production and SQLite in local dev
JSONB = JSON().with_variant(PG_JSONB(), "postgresql")
UUID = String(36).with_variant(PG_UUID(as_uuid=False), "postgresql")
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class PaymentState(str, enum.Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SCREENING = "SCREENING"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"
    AUTHORISED = "AUTHORISED"
    SUBMITTED = "SUBMITTED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERATIONS = "OPERATIONS"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    AUDITOR = "AUDITOR"
    MERCHANT = "MERCHANT"
    API_CLIENT = "API_CLIENT"


class KycStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class KycLevel(str, enum.Enum):
    NONE = "NONE"
    BASIC = "BASIC"
    STANDARD = "STANDARD"
    ENHANCED = "ENHANCED"


class ScreeningResult(str, enum.Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"


class FraudDecision(str, enum.Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class LedgerEntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class ExceptionType(str, enum.Enum):
    MISSING_AT_RAIL = "MISSING_AT_RAIL"
    MISSING_INTERNALLY = "MISSING_INTERNALLY"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DUPLICATE = "DUPLICATE"
    STATUS_MISMATCH = "STATUS_MISMATCH"
    TIMING_MISMATCH = "TIMING_MISMATCH"
    FEE_MISMATCH = "FEE_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"


class ExceptionStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class ReconStatus(str, enum.Enum):
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"
    PARTIAL = "PARTIAL"
    EXCEPTION = "EXCEPTION"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class WebhookEventType(str, enum.Enum):
    PAYMENT_CREATED = "payment.created"
    PAYMENT_SETTLED = "payment.settled"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_BLOCKED = "payment.blocked"
    PAYMENT_CANCELLED = "payment.cancelled"
    FRAUD_DETECTED = "fraud.detected"
    EXCEPTION_CREATED = "exception.created"


# ─── Users & Auth ────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    api_clients: Mapped[List["ApiClient"]] = relationship(back_populates="user")
    approvals: Mapped[List["Approval"]] = relationship(back_populates="user", foreign_keys="Approval.user_id")


class ApiClient(Base):
    __tablename__ = "api_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    api_key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    allowed_ips: Mapped[Optional[str]] = mapped_column(Text)  # comma-separated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="api_clients")


# ─── Customers & KYC ─────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    date_of_birth: Mapped[Optional[str]] = mapped_column(String(20))  # YYYY-MM-DD, non-PII display
    nationality: Mapped[Optional[str]] = mapped_column(String(3))  # ISO 3166-1 alpha-3
    country_of_residence: Mapped[Optional[str]] = mapped_column(String(3))
    kyc_status: Mapped[KycStatus] = mapped_column(Enum(KycStatus), default=KycStatus.PENDING)
    kyc_level: Mapped[KycLevel] = mapped_column(Enum(KycLevel), default=KycLevel.NONE)
    risk_rating: Mapped[Optional[str]] = mapped_column(String(20))  # LOW, MEDIUM, HIGH
    is_pep: Mapped[bool] = mapped_column(Boolean, default=False)  # Politically Exposed Person
    is_sanctioned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    kyc_records: Mapped[List["KycRecord"]] = relationship(back_populates="customer")
    accounts: Mapped[List["Account"]] = relationship(back_populates="customer")
    beneficiaries: Mapped[List["Beneficiary"]] = relationship(
        back_populates="customer", foreign_keys="Beneficiary.customer_id"
    )

    __table_args__ = (
        Index("ix_customers_name_trgm", "full_name"),
    )


class KycRecord(Base):
    __tablename__ = "kyc_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_reference: Mapped[Optional[str]] = mapped_column(String(255))
    kyc_level: Mapped[KycLevel] = mapped_column(Enum(KycLevel), nullable=False)
    status: Mapped[KycStatus] = mapped_column(Enum(KycStatus), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="kyc_records")


# ─── Accounts & Beneficiaries ────────────────────────────────────────────────

class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    account_number_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet encrypted
    account_number_masked: Mapped[str] = mapped_column(String(20), nullable=False)  # last 4
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)  # SAVINGS, CURRENT, etc.
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    bank_code: Mapped[Optional[str]] = mapped_column(String(50))
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(20))
    swift_bic: Mapped[Optional[str]] = mapped_column(String(15))
    iban: Mapped[Optional[str]] = mapped_column(String(34))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="accounts")
    ledger_account: Mapped[Optional["LedgerAccount"]] = relationship(back_populates="account")

    __table_args__ = (
        CheckConstraint("length(currency) = 3", name="ck_accounts_currency_len"),
    )


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    account_number_masked: Mapped[str] = mapped_column(String(20), nullable=False)
    bank_name: Mapped[Optional[str]] = mapped_column(String(255))
    bank_code: Mapped[Optional[str]] = mapped_column(String(50))
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(20))
    swift_bic: Mapped[Optional[str]] = mapped_column(String(15))
    iban: Mapped[Optional[str]] = mapped_column(String(34))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(3))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)  # for fraud rules
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="beneficiaries", foreign_keys=[customer_id])


# ─── Rails & Routing ──────────────────────────────────────────────────────────

class Rail(Base):
    __tablename__ = "rails"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # UPI, NEFT, SWIFT, CARD
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_backoff_base: Mapped[float] = mapped_column(Numeric(10, 4), default=1.5)
    circuit_breaker_threshold: Mapped[int] = mapped_column(Integer, default=5)
    circuit_breaker_timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    supported_currencies: Mapped[Optional[str]] = mapped_column(Text)  # comma-sep
    min_amount_minor: Mapped[int] = mapped_column(BigInteger, default=1)
    max_amount_minor: Mapped[int] = mapped_column(BigInteger, default=10000000000)
    settlement_hours: Mapped[int] = mapped_column(Integer, default=0)
    fee_fixed_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    fee_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    routing_rules: Mapped[List["RoutingRule"]] = relationship(back_populates="rail")


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    rail_id: Mapped[str] = mapped_column(ForeignKey("rails.id"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    country_sender: Mapped[Optional[str]] = mapped_column(String(3))
    country_receiver: Mapped[Optional[str]] = mapped_column(String(3))
    min_amount_minor: Mapped[Optional[int]] = mapped_column(BigInteger)
    max_amount_minor: Mapped[Optional[int]] = mapped_column(BigInteger)
    payment_type: Mapped[Optional[str]] = mapped_column(String(50))  # INSTANT, BATCH, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    rail: Mapped["Rail"] = relationship(back_populates="routing_rules")


# ─── Payments ────────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    beneficiary_id: Mapped[Optional[str]] = mapped_column(ForeignKey("beneficiaries.id"))
    sender_account_id: Mapped[Optional[str]] = mapped_column(ForeignKey("accounts.id"))
    rail_id: Mapped[Optional[str]] = mapped_column(ForeignKey("rails.id"))

    # Money (integer minor units + ISO 4217 currency)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fee_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    amount_settled_minor: Mapped[Optional[int]] = mapped_column(BigInteger)

    # State machine
    state: Mapped[PaymentState] = mapped_column(Enum(PaymentState), default=PaymentState.CREATED, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # optimistic locking

    # Metadata
    payment_type: Mapped[str] = mapped_column(String(50), default="CREDIT_TRANSFER")
    urgency: Mapped[str] = mapped_column(String(20), default="NORMAL")  # INSTANT, NORMAL, BULK
    description: Mapped[Optional[str]] = mapped_column(Text)
    end_to_end_id: Mapped[Optional[str]] = mapped_column(String(100))
    rail_reference: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Compliance
    screening_status: Mapped[Optional[ScreeningResult]] = mapped_column(Enum(ScreeningResult))
    fraud_decision: Mapped[Optional[FraudDecision]] = mapped_column(Enum(FraudDecision))
    fraud_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100

    # Reversal/Refund tracking
    parent_payment_id: Mapped[Optional[str]] = mapped_column(ForeignKey("payments.id"))
    refunded_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)

    # Timestamps
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    customer: Mapped["Customer"] = relationship(foreign_keys=[customer_id])
    beneficiary: Mapped[Optional["Beneficiary"]] = relationship(foreign_keys=[beneficiary_id])
    sender_account: Mapped[Optional["Account"]] = relationship(foreign_keys=[sender_account_id])
    rail: Mapped[Optional["Rail"]] = relationship(foreign_keys=[rail_id])
    state_history: Mapped[List["PaymentStateHistory"]] = relationship(back_populates="payment", order_by="PaymentStateHistory.created_at")
    messages: Mapped[List["PaymentMessage"]] = relationship(back_populates="payment")
    fraud_decisions: Mapped[List["FraudDecisionRecord"]] = relationship(back_populates="payment")
    screening_results: Mapped[List["ScreeningResultRecord"]] = relationship(back_populates="payment")
    ledger_entries: Mapped[List["LedgerEntry"]] = relationship(back_populates="payment")
    holds: Mapped[List["Hold"]] = relationship(back_populates="payment")
    fees: Mapped[List["Fee"]] = relationship(back_populates="payment")
    refunds: Mapped[List["Payment"]] = relationship(foreign_keys=[parent_payment_id])
    parent: Mapped[Optional["Payment"]] = relationship(foreign_keys=[parent_payment_id], remote_side=[id], overlaps="refunds")

    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_payments_amount_positive"),
        CheckConstraint("fee_minor >= 0", name="ck_payments_fee_nonneg"),
        CheckConstraint("length(currency) = 3", name="ck_payments_currency_len"),
        CheckConstraint("version > 0", name="ck_payments_version_positive"),
        Index("ix_payments_state_created", "state", "created_at"),
        Index("ix_payments_customer_state", "customer_id", "state"),
    )


class PaymentStateHistory(Base):
    __tablename__ = "payment_state_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    from_state: Mapped[Optional[PaymentState]] = mapped_column(Enum(PaymentState))
    to_state: Mapped[PaymentState] = mapped_column(Enum(PaymentState), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36))
    actor_type: Mapped[str] = mapped_column(String(50), default="SYSTEM")  # USER, SYSTEM, WORKER
    reason: Mapped[Optional[str]] = mapped_column(Text)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36))
    meta: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payment: Mapped["Payment"] = relationship(back_populates="state_history")


class PaymentMessage(Base):
    __tablename__ = "payment_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # INBOUND, OUTBOUND
    format: Mapped[str] = mapped_column(String(50), nullable=False)  # pain.001, pacs.008, CSV, etc.
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_content: Mapped[Optional[dict]] = mapped_column(JSONB)
    validation_errors: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payment: Mapped["Payment"] = relationship(back_populates="messages")


# ─── Idempotency ─────────────────────────────────────────────────────────────

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    response_status: Mapped[Optional[int]] = mapped_column(Integer)
    response_body: Mapped[Optional[dict]] = mapped_column(JSONB)
    payment_id: Mapped[Optional[str]] = mapped_column(String(36))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("key", "endpoint", name="uq_idempotency_keys_key_endpoint"),
        Index("ix_idempotency_keys_expires", "expires_at"),
    )


# ─── Ledger ──────────────────────────────────────────────────────────────────

class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    account_id: Mapped[Optional[str]] = mapped_column(ForeignKey("accounts.id"), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ASSET, LIABILITY, INCOME, EXPENSE
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # system accounts (fees, suspense, etc.)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    account: Mapped[Optional["Account"]] = relationship(back_populates="ledger_account")
    debit_entries: Mapped[List["LedgerEntry"]] = relationship(
        back_populates="debit_account", foreign_keys="LedgerEntry.debit_account_id"
    )
    credit_entries: Mapped[List["LedgerEntry"]] = relationship(
        back_populates="credit_account", foreign_keys="LedgerEntry.credit_account_id"
    )


class LedgerEntry(Base):
    """Double-entry ledger. Each row is one debit-credit pair; sum(debit)==sum(credit) enforced by constraint."""
    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    debit_account_id: Mapped[str] = mapped_column(ForeignKey("ledger_accounts.id"), nullable=False)
    credit_account_id: Mapped[str] = mapped_column(ForeignKey("ledger_accounts.id"), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(50), nullable=False)  # HOLD, SETTLE, REVERSE, FEE
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payment: Mapped["Payment"] = relationship(back_populates="ledger_entries")
    debit_account: Mapped["LedgerAccount"] = relationship(
        back_populates="debit_entries", foreign_keys=[debit_account_id]
    )
    credit_account: Mapped["LedgerAccount"] = relationship(
        back_populates="credit_entries", foreign_keys=[credit_account_id]
    )

    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_ledger_entries_amount_positive"),
        CheckConstraint("debit_account_id != credit_account_id", name="ck_ledger_entries_no_self"),
    )


class Hold(Base):
    __tablename__ = "holds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    ledger_account_id: Mapped[str] = mapped_column(ForeignKey("ledger_accounts.id"), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_released: Mapped[bool] = mapped_column(Boolean, default=False)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payment: Mapped["Payment"] = relationship(back_populates="holds")


class Fee(Base):
    __tablename__ = "fees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    fee_type: Mapped[str] = mapped_column(String(50), nullable=False)  # RAIL_FEE, SERVICE_FEE, etc.
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payment: Mapped["Payment"] = relationship(back_populates="fees")


# ─── Compliance ──────────────────────────────────────────────────────────────

class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # OFAC, UN, EU, CUSTOM
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    entries: Mapped[List["WatchlistEntry"]] = relationship(back_populates="watchlist")


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    watchlist_id: Mapped[str] = mapped_column(ForeignKey("watchlists.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[Optional[str]] = mapped_column(Text)  # pipe-separated
    date_of_birth: Mapped[Optional[str]] = mapped_column(String(20))
    nationality: Mapped[Optional[str]] = mapped_column(String(3))
    entity_type: Mapped[str] = mapped_column(String(50), default="INDIVIDUAL")  # INDIVIDUAL, ENTITY, VESSEL
    reason: Mapped[Optional[str]] = mapped_column(Text)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100))  # OFAC SDN ID, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    watchlist: Mapped["Watchlist"] = relationship(back_populates="entries")

    __table_args__ = (
        Index("ix_watchlist_entries_name", "name"),
    )


class ScreeningResultRecord(Base):
    __tablename__ = "screening_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    screening_type: Mapped[str] = mapped_column(String(50), nullable=False)  # SANCTIONS, KYC
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PAYER, PAYEE
    subject_name: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[ScreeningResult] = mapped_column(Enum(ScreeningResult), nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    matched_entry_id: Mapped[Optional[str]] = mapped_column(String(36))
    matched_name: Mapped[Optional[str]] = mapped_column(String(255))
    threshold_used: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    provider: Mapped[Optional[str]] = mapped_column(String(100))
    raw_response: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payment: Mapped["Payment"] = relationship(back_populates="screening_results")


class FraudRule(Base):
    __tablename__ = "fraud_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    rule_logic: Mapped[dict] = mapped_column(JSONB, nullable=False)  # JSON Logic expression
    score_contribution: Mapped[int] = mapped_column(Integer, default=20)  # points to add
    decision: Mapped[FraudDecision] = mapped_column(Enum(FraudDecision), default=FraudDecision.REVIEW)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    tags: Mapped[Optional[str]] = mapped_column(Text)  # comma-separated: VELOCITY, AMOUNT, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FraudDecisionRecord(Base):
    __tablename__ = "fraud_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    decision: Mapped[FraudDecision] = mapped_column(Enum(FraudDecision), nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    ml_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))  # Isolation Forest anomaly score
    triggered_rules: Mapped[Optional[dict]] = mapped_column(JSONB)  # [{rule_id, name, score_contribution}]
    reasons: Mapped[Optional[dict]] = mapped_column(JSONB)  # human-readable reasons
    allow_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    block_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payment: Mapped["Payment"] = relationship(back_populates="fraud_decisions")


# ─── Events & Outbox ─────────────────────────────────────────────────────────

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)  # PAYMENT
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    stream_id: Mapped[Optional[str]] = mapped_column(String(255))  # Redis Stream message ID
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_outbox_events_published", "published", "created_at"),
    )


class DlqEvent(Base):
    __tablename__ = "dlq_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    original_stream: Mapped[str] = mapped_column(String(100), nullable=False)
    original_message_id: Mapped[Optional[str]] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[str]] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ─── Reconciliation ──────────────────────────────────────────────────────────

class ReconRun(Base):
    __tablename__ = "recon_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    rail_id: Mapped[Optional[str]] = mapped_column(ForeignKey("rails.id"))
    run_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING")  # RUNNING, COMPLETED, FAILED
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_count: Mapped[int] = mapped_column(Integer, default=0)
    exception_count: Mapped[int] = mapped_column(Integer, default=0)
    matched_value_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    total_value_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    match_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    duration_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    created_by: Mapped[Optional[str]] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    rail: Mapped[Optional["Rail"]] = relationship()
    files: Mapped[List["ReconFile"]] = relationship(back_populates="run")
    items: Mapped[List["ReconItem"]] = relationship(back_populates="run")


class ReconFile(Base):
    __tablename__ = "recon_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("recon_runs.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False)  # CAMT053, CSV, MT940
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    row_count: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped["ReconRun"] = relationship(back_populates="files")


class ReconItem(Base):
    __tablename__ = "recon_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("recon_runs.id"), nullable=False, index=True)
    payment_id: Mapped[Optional[str]] = mapped_column(ForeignKey("payments.id"))
    rail_reference: Mapped[Optional[str]] = mapped_column(String(255))
    internal_amount_minor: Mapped[Optional[int]] = mapped_column(BigInteger)
    rail_amount_minor: Mapped[Optional[int]] = mapped_column(BigInteger)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    status: Mapped[ReconStatus] = mapped_column(Enum(ReconStatus), nullable=False)
    match_type: Mapped[Optional[str]] = mapped_column(String(50))  # EXACT, FUZZY
    exception_type: Mapped[Optional[ExceptionType]] = mapped_column(Enum(ExceptionType))
    exception_details: Mapped[Optional[dict]] = mapped_column(JSONB)
    rail_record: Mapped[Optional[dict]] = mapped_column(JSONB)
    auto_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped["ReconRun"] = relationship(back_populates="items")
    payment: Mapped[Optional["Payment"]] = relationship()


# ─── Exceptions ──────────────────────────────────────────────────────────────

class ExceptionCase(Base):
    __tablename__ = "exception_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    exception_type: Mapped[ExceptionType] = mapped_column(Enum(ExceptionType), nullable=False, index=True)
    status: Mapped[ExceptionStatus] = mapped_column(Enum(ExceptionStatus), default=ExceptionStatus.OPEN, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3)  # 1=critical, 5=low
    payment_id: Mapped[Optional[str]] = mapped_column(ForeignKey("payments.id"))
    recon_item_id: Mapped[Optional[str]] = mapped_column(ForeignKey("recon_items.id"))
    dlq_event_id: Mapped[Optional[str]] = mapped_column(ForeignKey("dlq_events.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    assigned_to: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    resolution_code: Mapped[Optional[str]] = mapped_column(String(100))
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    payment: Mapped[Optional["Payment"]] = relationship()
    comments: Mapped[List["CaseComment"]] = relationship(back_populates="case")
    approvals: Mapped[List["Approval"]] = relationship(back_populates="case")


class CaseComment(Base):
    __tablename__ = "case_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("exception_cases.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["ExceptionCase"] = relationship(back_populates="comments")


class Approval(Base):
    """Four-eyes approval for releasing blocked payments, high-value overrides, etc."""
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_id: Mapped[Optional[str]] = mapped_column(ForeignKey("exception_cases.id"))
    payment_id: Mapped[Optional[str]] = mapped_column(ForeignKey("payments.id"))
    approval_type: Mapped[str] = mapped_column(String(50), nullable=False)  # RELEASE_PAYMENT, MANUAL_OVERRIDE
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))  # approver (different from requester)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped[Optional["ExceptionCase"]] = relationship(back_populates="approvals")
    user: Mapped[Optional["User"]] = relationship(foreign_keys=[user_id], back_populates="approvals")


# ─── Webhooks ─────────────────────────────────────────────────────────────────

class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    events: Mapped[str] = mapped_column(Text, nullable=False)  # comma-sep event types
    secret: Mapped[str] = mapped_column(String(255), nullable=False)  # HMAC signing secret
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    deliveries: Mapped[List["WebhookDelivery"]] = relationship(back_populates="subscription")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    subscription_id: Mapped[str] = mapped_column(ForeignKey("webhook_subscriptions.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    http_status: Mapped[Optional[int]] = mapped_column(Integer)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    subscription: Mapped["WebhookSubscription"] = relationship(back_populates="deliveries")


# ─── Audit ────────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """Append-only. UPDATE and DELETE blocked by DB trigger. Hash chain integrity."""
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)  # monotonically increasing
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36))
    actor_type: Mapped[str] = mapped_column(String(50), default="SYSTEM")
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    prev_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA256 of previous row
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256(prev_hash + this row content)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_audit_log_sequence", "sequence"),
        Index("ix_audit_log_created", "created_at"),
    )


# ─── System Settings ──────────────────────────────────────────────────────────

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(50), default="string")  # string, int, float, bool, json
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
