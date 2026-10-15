#!/bin/sh
set -e

echo "[api] Starting PayNexus API server..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop uvloop \
    --log-config /app/app/core/log_config.json \
    --access-log
