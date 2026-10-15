# PayNexus: Platform Architecture & System Design

## 1. Executive Summary
PayNexus is a high-throughput, multi-rail payments modernisation and orchestration engine designed to resolve the fundamental issues of legacy banking systems: incompatible message formats (SWIFT MT103 vs ISO 20022), double-charge duplicate vulnerabilities, siloed compliance screening, non-deterministic state management, and slow reconciliation breaks.

---

## 2. System Architecture & Topology

```mermaid
graph TD
  UI[Frontend React 18 + Vite :3000] -->|Reverse Proxy /api| NGINX[Nginx Ingress / Frontend Container]
  NGINX --> API[FastAPI Core Gateway :8000]
  
  API --> PG[(PostgreSQL 16 System of Record)]
  API --> REDIS[(Redis 7 Cluster: Streams + Locks)]
  
  ORCH[Payment Orchestrator Worker] -->|Consumer Group| REDIS
  OUTBOX[Transactional Outbox Publisher] -->|Polls outbox_events| PG
  OUTBOX -->|xadd payment_events| REDIS
  
  ORCH -->|Screening Request| SANCTIONS[sanctions-provider-sim :8201]
  ORCH -->|KYC Verification| KYC[kyc-provider-sim :8202]
  
  ORCH --> UPI[rail-upi-sim :8101]
  ORCH --> NEFT[rail-neft-sim :8102]
  ORCH --> SWIFT[rail-swift-sim :8103]
  ORCH --> CARD[rail-card-sim :8104]
  
  RECON[Reconciliation Worker] -->|Ingests Statements| UPI
  RECON -->|Ingests Statements| NEFT
  RECON -->|Updates Matched & Exceptions| PG
  
  PROM[Prometheus :9090] -->|Scrapes /metrics| API
  GRAFANA[Grafana :3001] -->|Visualizes| PROM
```

---

## 3. Core Architectural Patterns

### 3.1 Hexagonal Architecture (Ports and Adapters)
Every payment rail (UPI, NEFT, SWIFT, Card) is an isolated plug-in adapter implementing a unified Python `PaymentRailAdapter` interface. Switching rails or adding FedNow / SEPA requires implementing only one adapter without touching orchestrator core logic.

### 3.2 Transactional Outbox Pattern
State transitions and outbox events are committed inside the exact same atomic PostgreSQL database transaction:
1. `payment.state` updated to `VALIDATED`
2. `outbox_events` row inserted with payload
3. Commit transaction
4. Dedicated outbox publisher polls pending records and pushes them into Redis Stream `payment_events`.
Zero message loss even if the worker or container restarts unexpectedly.

### 3.3 Bulletproof Dual-Layer Idempotency
- **Layer 1 (Fast-Path Lock)**: Redis `SETNX idempotency:{key}` with 30-second TTL to serialize concurrent parallel requests.
- **Layer 2 (Final Arbiter)**: PostgreSQL table `idempotency_keys` with `UNIQUE CONSTRAINT(key)`.
- Concurrent duplicates wait on lock and return HTTP 200 with the original response body and header `Idempotent-Replayed: true`. Mismatched payload hashes raise HTTP 422 Conflict.

### 3.4 Cryptographic Append-Only Audit Trail
Every system action writes to `audit_log`:
- Immuntability is enforced at the database layer via PostgreSQL triggers that reject `UPDATE` and `DELETE`.
- Each row contains `prev_hash` and `row_hash = SHA256(prev_hash + sequence + entity + actor + created_at)`.
- An audit verification API recomputes the entire chain from genesis and pinpoints the exact sequence of any tampered row.

---

## 4. Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    CUSTOMERS ||--o{ ACCOUNTS : owns
    CUSTOMERS ||--o{ BENEFICIARIES : manages
    CUSTOMERS ||--o{ PAYMENTS : initiates
    PAYMENTS ||--o{ PAYMENT_STATE_HISTORY : tracks
    PAYMENTS ||--o{ LEDGER_ENTRIES : posts
    PAYMENTS ||--o{ HOLDS : reserves
    PAYMENTS ||--o{ SCREENING_RESULTS : evaluates
    PAYMENTS ||--o{ FRAUD_DECISIONS : scores
    RECON_RUNS ||--o{ RECON_FILES : ingests
    RECON_RUNS ||--o{ EXCEPTION_CASES : classifies
    USERS ||--o{ AUDIT_LOG : audits
```
