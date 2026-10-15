"""Prometheus metrics definitions for PayNexus."""
from prometheus_client import Counter, Histogram, Gauge, Summary

# ── Payment metrics ────────────────────────────────────────────────────────────
payments_total = Counter(
    "paynexus_payments_total",
    "Total payments created",
    ["currency", "rail", "state"],
)

payments_by_state = Gauge(
    "paynexus_payments_by_state",
    "Current payment count by state",
    ["state"],
)

payment_amount_total = Counter(
    "paynexus_payment_amount_minor_total",
    "Total payment value in minor units",
    ["currency"],
)

payment_processing_duration = Histogram(
    "paynexus_payment_processing_seconds",
    "Payment processing latency",
    ["stage"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# ── API metrics ────────────────────────────────────────────────────────────────
http_requests_total = Counter(
    "paynexus_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration = Histogram(
    "paynexus_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Compliance metrics ─────────────────────────────────────────────────────────
sanctions_hits_total = Counter(
    "paynexus_sanctions_hits_total",
    "Total sanctions screening hits",
    ["result"],  # PASS, REVIEW, BLOCKED
)

fraud_decisions_total = Counter(
    "paynexus_fraud_decisions_total",
    "Total fraud engine decisions",
    ["decision"],  # ALLOW, REVIEW, BLOCK
)

# ── Rail metrics ───────────────────────────────────────────────────────────────
rail_requests_total = Counter(
    "paynexus_rail_requests_total",
    "Total rail adapter requests",
    ["rail", "result"],  # SUCCESS, FAILURE, TIMEOUT
)

rail_latency = Histogram(
    "paynexus_rail_latency_seconds",
    "Rail adapter latency",
    ["rail"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

circuit_breaker_state = Gauge(
    "paynexus_circuit_breaker_open",
    "Circuit breaker state (1=open, 0=closed)",
    ["rail"],
)

# ── Queue metrics ──────────────────────────────────────────────────────────────
stream_queue_depth = Gauge(
    "paynexus_stream_queue_depth",
    "Redis stream pending message count",
    ["stream"],
)

dlq_size = Gauge(
    "paynexus_dlq_size_total",
    "Dead letter queue size",
)

# ── Reconciliation metrics ─────────────────────────────────────────────────────
recon_match_rate = Gauge(
    "paynexus_recon_match_rate",
    "Reconciliation match rate (0-1)",
    ["rail"],
)

recon_exceptions_total = Counter(
    "paynexus_recon_exceptions_total",
    "Total reconciliation exceptions",
    ["exception_type"],
)

# ── Idempotency metrics ────────────────────────────────────────────────────────
idempotency_replays_total = Counter(
    "paynexus_idempotency_replays_total",
    "Total idempotent request replays",
)

idempotency_conflicts_total = Counter(
    "paynexus_idempotency_conflicts_total",
    "Total idempotency key conflicts",
)
