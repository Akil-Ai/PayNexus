"""Database seeder for PayNexus using Faker with fixed random seed (42).
Seeds users, rails, routing rules, watchlists, fraud rules, system settings,
customers, accounts, beneficiaries, and 12 months of synthetic payment history.
"""
import os
import sys
import random
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath("backend"))

from faker import Faker
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password, encrypt_field
from app.models.models import (
    Base, User, UserRole, Rail, RoutingRule, Watchlist, WatchlistEntry,
    FraudRule, FraudDecision, SystemSetting, Customer, Account, Beneficiary,
    KycRecord, KycStatus, KycLevel, Payment, PaymentState, PaymentStateHistory,
    LedgerAccount, LedgerEntry, LedgerEntryType, AuditLog, ScreeningResult
)

fake = Faker()
Faker.seed(42)
random.seed(42)

def get_sync_engine():
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url and "postgresql" in sync_url:
        try:
            eng = create_engine(sync_url)
            with eng.connect() as conn:
                pass
            return eng
        except Exception:
            pass
    db_file = os.path.abspath("paynexus.db").replace("\\", "/")
    return create_engine(f"sqlite:///{db_file}")

DEMO_PASSWORD = "Demo@PayNexus2026!"


def seed_database():
    engine = get_sync_engine()
    print(f"Connecting to database: {engine.url}...")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if already seeded
        existing_user = session.execute(select(User).limit(1)).scalar_one_or_none()
        if existing_user:
            print("Database already contains data. Skipping initial seeding.")
            return

        print("Seeding demo users...")
        users = [
            User(
                id=str(uuid.uuid4()),
                email="admin@paynexus.io",
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name="Alex Mercer (Admin)",
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            ),
            User(
                id=str(uuid.uuid4()),
                email="ops@paynexus.io",
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name="Sarah Chen (Operations)",
                role=UserRole.OPERATIONS,
                is_active=True,
                is_verified=True
            ),
            User(
                id=str(uuid.uuid4()),
                email="compliance@paynexus.io",
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name="Elena Rostova (Compliance)",
                role=UserRole.COMPLIANCE_OFFICER,
                is_active=True,
                is_verified=True
            ),
            User(
                id=str(uuid.uuid4()),
                email="auditor@paynexus.io",
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name="Marcus Vance (Auditor)",
                role=UserRole.AUDITOR,
                is_active=True,
                is_verified=True
            ),
            User(
                id=str(uuid.uuid4()),
                email="merchant@paynexus.io",
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name="Apex Commerce Corp (Merchant)",
                role=UserRole.MERCHANT,
                is_active=True,
                is_verified=True
            )
        ]
        session.add_all(users)
        session.flush()

        print("Seeding system ledger accounts...")
        sys_ledger = [
            LedgerAccount(id=str(uuid.uuid4()), name="Cash Clearing - UPI", account_type="ASSET", currency="INR", is_system=True),
            LedgerAccount(id=str(uuid.uuid4()), name="Cash Clearing - NEFT", account_type="ASSET", currency="INR", is_system=True),
            LedgerAccount(id=str(uuid.uuid4()), name="Cash Clearing - SWIFT", account_type="ASSET", currency="USD", is_system=True),
            LedgerAccount(id=str(uuid.uuid4()), name="Cash Clearing - CARD", account_type="ASSET", currency="INR", is_system=True),
            LedgerAccount(id=str(uuid.uuid4()), name="Fee Revenue", account_type="INCOME", currency="INR", is_system=True),
            LedgerAccount(id=str(uuid.uuid4()), name="Suspense Account", account_type="LIABILITY", currency="INR", is_system=True),
        ]
        session.add_all(sys_ledger)
        session.flush()

        print("Seeding payment rails...")
        upi_rail = Rail(
            id=str(uuid.uuid4()),
            code="UPI",
            name="Unified Payments Interface (NPCI)",
            description="Instant 24x7 payment network in India via VPA or account+IFSC",
            is_active=True,
            base_url="http://localhost:8101",
            timeout_seconds=15,
            max_retries=3,
            retry_backoff_base=Decimal("1.5"),
            circuit_breaker_threshold=5,
            circuit_breaker_timeout_seconds=60,
            supported_currencies="INR",
            min_amount_minor=100,        # 1.00 INR
            max_amount_minor=20000000,   # 200,000.00 INR
            settlement_hours=0,
            fee_fixed_minor=0,
            fee_percent=Decimal("0.0"),
            priority=10
        )
        neft_rail = Rail(
            id=str(uuid.uuid4()),
            code="NEFT",
            name="National Electronic Funds Transfer (RBI)",
            description="Hourly batch electronic funds transfer network",
            is_active=True,
            base_url="http://localhost:8102",
            timeout_seconds=30,
            max_retries=3,
            retry_backoff_base=Decimal("1.5"),
            circuit_breaker_threshold=5,
            circuit_breaker_timeout_seconds=60,
            supported_currencies="INR",
            min_amount_minor=100,
            max_amount_minor=5000000000, # 50,000,000 INR
            settlement_hours=1,
            fee_fixed_minor=250,          # 2.50 INR
            fee_percent=Decimal("0.0002"),
            priority=20
        )
        swift_rail = Rail(
            id=str(uuid.uuid4()),
            code="SWIFT",
            name="SWIFT Cross-Border gpi Network",
            description="International correspondent banking network with ISO 20022 and MT103",
            is_active=True,
            base_url="http://localhost:8103",
            timeout_seconds=45,
            max_retries=2,
            retry_backoff_base=Decimal("2.0"),
            circuit_breaker_threshold=3,
            circuit_breaker_timeout_seconds=120,
            supported_currencies="USD,EUR,GBP,INR",
            min_amount_minor=50000,      # $500
            max_amount_minor=100000000000,
            settlement_hours=48,
            fee_fixed_minor=150000,       # $15.00
            fee_percent=Decimal("0.0015"),
            priority=30
        )
        card_rail = Rail(
            id=str(uuid.uuid4()),
            code="CARD",
            name="Domestic & International Card Clearing",
            description="Visa, Mastercard, RuPay ISO 8583 payment gateway processing",
            is_active=True,
            base_url="http://localhost:8104",
            timeout_seconds=20,
            max_retries=3,
            retry_backoff_base=Decimal("1.5"),
            circuit_breaker_threshold=5,
            circuit_breaker_timeout_seconds=60,
            supported_currencies="INR,USD,EUR",
            min_amount_minor=100,
            max_amount_minor=50000000,
            settlement_hours=24,
            fee_fixed_minor=200,          # 2.00 INR
            fee_percent=Decimal("0.0175"),# 1.75% interchange
            priority=40
        )
        rails = [upi_rail, neft_rail, swift_rail, card_rail]
        session.add_all(rails)
        session.flush()

        print("Seeding routing rules...")
        routing_rules = [
            RoutingRule(
                id=str(uuid.uuid4()),
                rail_id=upi_rail.id,
                priority=10,
                currency="INR",
                min_amount_minor=100,
                max_amount_minor=20000000,
                payment_type="INSTANT",
                country_sender="IND",
                country_receiver="IND",
                is_active=True
            ),
            RoutingRule(
                id=str(uuid.uuid4()),
                rail_id=neft_rail.id,
                priority=20,
                currency="INR",
                min_amount_minor=100,
                max_amount_minor=5000000000,
                payment_type="BATCH",
                country_sender="IND",
                country_receiver="IND",
                is_active=True
            ),
            RoutingRule(
                id=str(uuid.uuid4()),
                rail_id=swift_rail.id,
                priority=30,
                currency="USD",
                min_amount_minor=50000,
                max_amount_minor=100000000000,
                payment_type="CROSS_BORDER",
                is_active=True
            ),
            RoutingRule(
                id=str(uuid.uuid4()),
                rail_id=card_rail.id,
                priority=40,
                currency="INR",
                min_amount_minor=100,
                max_amount_minor=50000000,
                payment_type="CARD",
                is_active=True
            )
        ]
        session.add_all(routing_rules)
        session.flush()

        print("Seeding sanctions watchlists...")
        watchlist = Watchlist(
            id=str(uuid.uuid4()),
            name="Global Consolidated Sanctions Watchlist (OFAC / UN / EU)",
            source="OFAC",
            is_active=True,
            entry_count=5,
            last_updated=datetime.now(timezone.utc)
        )
        session.add(watchlist)
        session.flush()

        watchlist_entries = [
            WatchlistEntry(
                id=str(uuid.uuid4()),
                watchlist_id=watchlist.id,
                name="Viktor Anatolyevich Bout",
                entity_type="INDIVIDUAL",
                nationality="RUS",
                aliases="Victor Bout|Boris Bout|Vadim Bout",
                reason="Arms trafficking / OFAC SDN list",
                is_active=True
            ),
            WatchlistEntry(
                id=str(uuid.uuid4()),
                watchlist_id=watchlist.id,
                name="Dawood Ibrahim Kaskar",
                entity_type="INDIVIDUAL",
                nationality="IND",
                aliases="Dawood Ebrahim|Haji Dawood|Sheikh Dawood Hassan",
                reason="Global terrorist designation",
                is_active=True
            ),
            WatchlistEntry(
                id=str(uuid.uuid4()),
                watchlist_id=watchlist.id,
                name="Hafiz Muhammad Saeed",
                entity_type="INDIVIDUAL",
                nationality="PAK",
                aliases="Hafiz Saeed|Muhammad Saeed",
                reason="UN 1267 sanctions list",
                is_active=True
            ),
            WatchlistEntry(
                id=str(uuid.uuid4()),
                watchlist_id=watchlist.id,
                name="Al-Furqan Foundation",
                entity_type="ENTITY",
                nationality="SYR",
                aliases="Furqan Media",
                reason="Designated terrorist entity",
                is_active=True
            ),
            WatchlistEntry(
                id=str(uuid.uuid4()),
                watchlist_id=watchlist.id,
                name="Rosoboronexport",
                entity_type="ENTITY",
                nationality="RUS",
                aliases="JSC Rosoboronexport",
                reason="Sectoral sanctions",
                is_active=True
            )
        ]
        session.add_all(watchlist_entries)
        session.flush()

        print("Seeding fraud rules...")
        fraud_rules = [
            FraudRule(
                id=str(uuid.uuid4()),
                name="High Velocity Check",
                description="Triggers review if customer exceeds 5 payments in 10 minutes",
                tags="VELOCITY",
                rule_logic={"and": [{">": [{"var": "customer_recent_tx_count"}, 5]}]},
                score_contribution=45,
                decision=FraudDecision.REVIEW,
                priority=1,
                is_active=True
            ),
            FraudRule(
                id=str(uuid.uuid4()),
                name="Large Transaction Threshold",
                description="Flags single transactions exceeding 500,000 INR (50M paise)",
                tags="AMOUNT_THRESHOLD",
                rule_logic={">": [{"var": "amount_minor"}, 50000000]},
                score_contribution=40,
                decision=FraudDecision.REVIEW,
                priority=2,
                is_active=True
            ),
            FraudRule(
                id=str(uuid.uuid4()),
                name="Structuring / Smurfing Pattern",
                description="Detects multiple transactions just below reporting limit (49,000 - 49,999 INR)",
                tags="STRUCTURING",
                rule_logic={"and": [{">=": [{"var": "amount_minor"}, 4900000]}, {"<": [{"var": "amount_minor"}, 5000000]}]},
                score_contribution=60,
                decision=FraudDecision.BLOCK,
                priority=3,
                is_active=True
            ),
            FraudRule(
                id=str(uuid.uuid4()),
                name="Odd Hours High Value",
                description="Flags high value transactions initiated between 01:00 AM and 04:30 AM",
                tags="ODD_HOURS",
                rule_logic={"and": [{"in_hours": [1, 4]}, {">": [{"var": "amount_minor"}, 10000000]}]},
                score_contribution=30,
                decision=FraudDecision.REVIEW,
                priority=4,
                is_active=True
            )
        ]
        session.add_all(fraud_rules)
        session.flush()

        print("Seeding system settings...")
        settings_data = [
            SystemSetting(id=str(uuid.uuid4()), key="SANCTIONS_BLOCK_THRESHOLD", value="85.0", value_type="float", description="Minimum match score to automatically block payment"),
            SystemSetting(id=str(uuid.uuid4()), key="SANCTIONS_REVIEW_THRESHOLD", value="70.0", value_type="float", description="Minimum match score to route payment to review"),
            SystemSetting(id=str(uuid.uuid4()), key="SANCTIONS_FAIL_CLOSED", value="false", value_type="bool", description="Whether to block transactions if sanctions provider is down"),
            SystemSetting(id=str(uuid.uuid4()), key="KYC_FAIL_CLOSED", value="false", value_type="bool", description="Whether to block if KYC provider is down"),
            SystemSetting(id=str(uuid.uuid4()), key="AUTO_RESOLVE_RECON", value="true", value_type="bool", description="Automatically settle internal payments matched at rail")
        ]
        session.add_all(settings_data)
        session.flush()

        print("Seeding customers and accounts...")
        customer_ids = []
        customer_accounts = {}
        customer_beneficiaries = {}

        for i in range(30):
            c_name = fake.name()
            c_id = str(uuid.uuid4())
            customer = Customer(
                id=c_id,
                external_id=f"CUST-{1000 + i}",
                full_name=c_name,
                email=fake.email(),
                phone=f"+91{random.randint(7000000000, 9999999999)}",
                nationality="IND",
                country_of_residence="IND",
                kyc_status=KycStatus.VERIFIED,
                kyc_level=random.choice([KycLevel.BASIC, KycLevel.STANDARD, KycLevel.ENHANCED]),
                risk_rating="LOW",
                is_active=True
            )
            session.add(customer)
            customer_ids.append(c_id)

            # Account
            raw_acc_num = f"91{random.randint(1000000000, 9999999999)}"
            account_id = str(uuid.uuid4())
            account = Account(
                id=account_id,
                customer_id=c_id,
                account_number_encrypted=encrypt_field(raw_acc_num),
                account_number_masked=f"••••{raw_acc_num[-4:]}",
                account_type="SAVINGS",
                currency="INR",
                ifsc_code=f"HDFC000{random.randint(1000, 9999)}",
                bank_code="HDFC",
                is_active=True
            )
            session.add(account)
            customer_accounts[c_id] = account_id

            # Ledger Account for customer
            cust_ledger = LedgerAccount(
                id=str(uuid.uuid4()),
                account_id=account_id,
                name=f"{c_name} (Savings)",
                account_type="LIABILITY",
                currency="INR",
                is_system=False
            )
            session.add(cust_ledger)

            # Beneficiary
            raw_ben_acc = f"92{random.randint(1000000000, 9999999999)}"
            ben_id = str(uuid.uuid4())
            ben = Beneficiary(
                id=ben_id,
                customer_id=c_id,
                name=fake.name(),
                account_number_encrypted=encrypt_field(raw_ben_acc),
                account_number_masked=f"••••{raw_ben_acc[-4:]}",
                ifsc_code=f"SBIN000{random.randint(1000, 9999)}",
                bank_name="State Bank of India",
                bank_code="SBIN",
                currency="INR",
                country="IND",
                is_active=True,
                is_new=False
            )
            session.add(ben)
            customer_beneficiaries[c_id] = ben_id

        session.flush()

        print("Seeding 12 months historical payments...")
        now = datetime.now(timezone.utc)
        rail_map = {"UPI": upi_rail.id, "NEFT": neft_rail.id, "CARD": card_rail.id}
        states = (
            [PaymentState.SETTLED] * 120 +
            [PaymentState.SUBMITTED] * 10 +
            [PaymentState.AUTHORISED] * 5 +
            [PaymentState.VALIDATED] * 5 +
            [PaymentState.FAILED] * 15 +
            [PaymentState.BLOCKED] * 8 +
            [PaymentState.REVIEW] * 8 +
            [PaymentState.CREATED] * 5
        )

        for m in range(12):
            month_date = now - timedelta(days=m * 30)
            for _ in range(15):
                c_id = random.choice(customer_ids)
                p_state = random.choice(states)
                amt = random.randint(5000, 500000)  # 50.00 to 5,000.00 INR
                p_id = str(uuid.uuid4())
                ref = f"PAY-{month_date.strftime('%Y%m')}-{random.randint(10000, 99999)}"
                rail_code = random.choice(["UPI", "NEFT", "CARD"])

                pmt = Payment(
                    id=p_id,
                    reference=ref,
                    idempotency_key=str(uuid.uuid4()),
                    customer_id=c_id,
                    sender_account_id=customer_accounts[c_id],
                    beneficiary_id=customer_beneficiaries[c_id],
                    rail_id=rail_map[rail_code],
                    amount_minor=amt,
                    currency="INR",
                    fee_minor=0 if rail_code == "UPI" else (250 if rail_code == "NEFT" else 200),
                    amount_settled_minor=amt if p_state == PaymentState.SETTLED else None,
                    state=p_state,
                    version=1,
                    urgency="INSTANT" if rail_code == "UPI" else "NORMAL",
                    description=fake.sentence(nb_words=4),
                    rail_reference=f"TXN-{random.randint(1000000, 9999999)}",
                    screening_status=ScreeningResult.PASS if p_state != PaymentState.BLOCKED else ScreeningResult.BLOCKED,
                    fraud_decision=FraudDecision.ALLOW if p_state not in [PaymentState.BLOCKED, PaymentState.REVIEW] else (FraudDecision.BLOCK if p_state == PaymentState.BLOCKED else FraudDecision.REVIEW),
                    fraud_score=random.randint(5, 25) if p_state not in [PaymentState.BLOCKED, PaymentState.REVIEW] else random.randint(75, 95),
                    settled_at=month_date + timedelta(minutes=5) if p_state == PaymentState.SETTLED else None,
                    submitted_at=month_date,
                    created_at=month_date,
                    updated_at=month_date
                )
                session.add(pmt)

        session.commit()
        print("Database seeded successfully with demo users, rails, watchlists, fraud rules, customers, and 12-month payment history!")

    except Exception as exc:
        print(f"Error seeding database: {exc}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
