.PHONY: up down seed test load-test demo reset logs shell-backend shell-db

# ── Main targets ────────────────────────────────────────────────────────────
up:
	docker compose up --build -d
	@echo "Services starting... UI will be at http://localhost:3000"
	@echo "API docs at http://localhost:8000/docs"
	@echo "Grafana at http://localhost:3001"

down:
	docker compose down

reset:
	docker compose down -v --remove-orphans
	docker compose up --build -d

# ── Seed data ────────────────────────────────────────────────────────────────
seed:
	docker compose exec backend python scripts/seed.py

# ── Testing ──────────────────────────────────────────────────────────────────
test:
	docker compose exec backend pytest tests/ -v --tb=short 2>&1 | tee test_results.txt

test-unit:
	docker compose exec backend pytest tests/unit/ -v --tb=short

test-integration:
	docker compose exec backend pytest tests/integration/ -v --tb=short

test-e2e:
	cd frontend && npx playwright test

lint:
	docker compose exec backend ruff check app/ tests/ && mypy app/ --ignore-missing-imports
	cd frontend && npm run lint && npx tsc --noEmit

# ── Load testing ────────────────────────────────────────────────────────────
load-test:
	docker compose exec backend python scripts/load_test.py

# ── Demo scenarios ──────────────────────────────────────────────────────────
demo:
	docker compose exec backend python scripts/demo_scenarios.py

# ── Logs ────────────────────────────────────────────────────────────────────
logs:
	docker compose logs -f --tail=100

logs-backend:
	docker compose logs -f backend orchestrator outbox-publisher

logs-workers:
	docker compose logs -f orchestrator reconciliation-worker outbox-publisher

# ── Shell access ─────────────────────────────────────────────────────────────
shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U paynexus -d paynexus

# ── Fraud model training ─────────────────────────────────────────────────────
train-fraud-model:
	docker compose exec backend python scripts/train_fraud_model.py

# ── Health check ─────────────────────────────────────────────────────────────
health:
	@curl -s http://localhost:8000/healthz | python -m json.tool
	@curl -s http://localhost:8000/readyz | python -m json.tool
