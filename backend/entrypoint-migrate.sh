#!/bin/sh
set -e

echo "[migrator] Waiting for Postgres to be ready..."
until python -c "
import psycopg2, os
try:
    url = os.environ['SYNC_DATABASE_URL']
    conn = psycopg2.connect(url)
    conn.close()
    print('ok')
except Exception as e:
    print(f'not ready: {e}')
    exit(1)
"; do
    echo "[migrator] Postgres not ready, retrying in 2s..."
    sleep 2
done

echo "[migrator] Running Alembic migrations..."
cd /app && alembic upgrade head

echo "[migrator] Running seed script..."
python scripts/seed.py

echo "[migrator] Training fraud model..."
python scripts/train_fraud_model.py || echo "[migrator] Fraud model training skipped (will use fallback)"

echo "[migrator] Done."
