# PayNexus Operations Runbook

## 1. Quick Start Commands

```bash
# Start all containers with healthy DB, Redis, and mock services
docker compose up --build -d

# Check health of all services
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz

# Inspect background orchestrator logs
docker compose logs -f orchestrator

# Reset database and re-seed
make reset
```

---

## 2. Chaos Recovery & Incident Playbooks

### Incident A: Payment Rail Outage (e.g. UPI Circuit Breaker OPEN)
1. **Symptom**: UPI payments fail fast with `Circuit breaker OPEN`.
2. **Mitigation**:
   - Router automatically diverts traffic to alternate rail (NEFT/Card) if rule permits.
   - Investigate rail simulator or provider status.
   - Once rail recovery is confirmed, reset circuit breaker via UI (`/rails`) or API:
     `POST /api/v1/rails/UPI/circuit-breaker/reset`.

### Incident B: Replaying Dead-Letter Queue (DLQ) Items
1. Open `/exceptions` in UI and select the Dead-Letter Queue tab.
2. Select failed items.
3. Click "Replay Selected to Main Stream".
4. The worker automatically picks up items, reconciles state, and attempts processing without double charging.

### Incident C: Audit Tamper Alert
1. **Symptom**: `POST /api/v1/audit/verify` returns `is_valid: false` with `corrupted_sequence`.
2. **Investigation**:
   - Query row at corrupted sequence.
   - Correlate PostgreSQL WAL logs with actor IP.
   - Notify Chief Information Security Officer (CISO).
