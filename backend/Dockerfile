FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Create models directory
RUN mkdir -p /app/models

# Entry-point scripts
COPY entrypoint-migrate.sh /app/entrypoint-migrate.sh
COPY entrypoint-api.sh /app/entrypoint-api.sh
RUN chmod +x /app/entrypoint-migrate.sh /app/entrypoint-api.sh

# Non-root user
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
