"""Automated tests for telemetry and performance measurement endpoints.
Verifies API timing, percentile calculations, redaction of sensitive data,
health status probes, and targets evaluation.
"""
import pytest
from app.core.telemetry import (
    record_http_request,
    record_error,
    record_db_query,
    get_api_performance,
    get_db_metrics,
    get_system_resources,
    _calculate_percentile,
    redact_sensitive_info,
    normalize_path,
)


def test_percentile_calculations():
    # Odd sample count
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert _calculate_percentile(values, 0.50) == 30.0
    assert _calculate_percentile(values, 0.0) == 10.0
    assert _calculate_percentile(values, 1.0) == 50.0

    # 100 sample items
    hundred = [float(i) for i in range(1, 101)]
    p50 = _calculate_percentile(hundred, 0.50)
    p95 = _calculate_percentile(hundred, 0.95)
    p99 = _calculate_percentile(hundred, 0.99)
    assert 50.0 <= p50 <= 51.0
    assert 95.0 <= p95 <= 96.0
    assert 99.0 <= p99 <= 100.0


def test_sensitive_info_redaction():
    # Tokens
    raw_auth = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    clean_auth = redact_sensitive_info(raw_auth)
    assert "eyJhbGci" not in clean_auth
    assert "REDACTED" in clean_auth

    # Passwords
    raw_pass = "Failed login with password: 'SuperSecretPassword123!'"
    clean_pass = redact_sensitive_info(raw_pass)
    assert "SuperSecretPassword123!" not in clean_pass

    # Card PAN numbers
    raw_pan = "Processing credit card 4111 2222 3333 4444 on gateway"
    clean_pan = redact_sensitive_info(raw_pan)
    assert "4111 2222 3333 4444" not in clean_pan
    assert "[REDACTED_PAN]" in clean_pan


def test_path_normalization():
    # UUID path normalization
    path1 = "/api/v1/payments/7c17103f-1504-4d44-80f9-7240b5568c1a"
    assert normalize_path(path1) == "/api/v1/payments/:id"

    # Numeric path normalization
    path2 = "/api/v1/customers/12345/accounts/6789"
    assert normalize_path(path2) == "/api/v1/customers/:id/accounts/:id"

    # Query string stripping
    path3 = "/api/v1/audit/?limit=50&offset=0"
    assert normalize_path(path3) == "/api/v1/audit/"


def test_telemetry_recording_and_aggregation():
    # Record mock requests
    record_http_request("GET", "/api/v1/payments/test-1", 200, 45.2)
    record_http_request("POST", "/api/v1/payments", 201, 120.5)
    record_http_request("GET", "/api/v1/analytics/dashboard", 200, 15.0)
    record_http_request("POST", "/api/v1/auth/login", 401, 30.0)

    perf = get_api_performance(window_seconds=3600)
    assert perf["total_requests"] >= 4
    assert perf["status_2xx"] >= 3
    assert perf["status_4xx"] >= 1
    assert perf["avg_latency_ms"] > 0
    assert perf["p95_latency_ms"] > 0
    assert perf["success_rate_pct"] <= 100.0


def test_db_metrics_recording():
    record_db_query(12.5, is_slow=False)
    record_db_query(250.0, is_slow=True)
    db_stats = get_db_metrics()
    assert db_stats["total_queries"] >= 2
    assert db_stats["slow_queries"] >= 1
    assert db_stats["avg_query_ms"] > 0


def test_system_resource_inspection():
    resources = get_system_resources()
    assert resources["uptime_seconds"] >= 0
    assert resources["cpu_count"] >= 1
    assert "process_id" in resources
    assert "platform" in resources
