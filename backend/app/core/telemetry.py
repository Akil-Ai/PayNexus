"""In-memory telemetry and metrics collector for PayNexus system performance.
Provides bounded circular buffers for API request metrics, latency distributions,
database query execution times, error records (with sensitive data redaction),
and system resource tracking.
"""
import ctypes
import os
import platform
import re
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

START_TIME = time.time()
START_DATETIME = datetime.now(timezone.utc)

# Lock for thread-safe in-memory metrics mutations
_metrics_lock = threading.Lock()

# Bounded capacity
MAX_REQUEST_LOGS = 2000
MAX_ERROR_LOGS = 100
MAX_LATENCY_HISTORY = 300

# Circular buffers for live metric calculation
_request_records: deque = deque(maxlen=MAX_REQUEST_LOGS)
_error_records: deque = deque(maxlen=MAX_ERROR_LOGS)
_db_latency_records: deque = deque(maxlen=1000)

# Counters
_counters: Dict[str, int] = {
    "total_requests": 0,
    "status_2xx": 0,
    "status_3xx": 0,
    "status_4xx": 0,
    "status_5xx": 0,
    "db_queries_total": 0,
    "db_slow_queries_total": 0,
    "db_errors_total": 0,
    "idempotency_conflicts_total": 0,
    "idempotency_replays_total": 0,
}

# Per-endpoint stats: { endpoint: { "count": int, "total_ms": float, "errors": int, "min_ms": float, "max_ms": float, "samples": deque } }
_endpoint_stats: Dict[str, Dict[str, Any]] = {}

# Patterns for sensitive data redaction
_SENSITIVE_PATTERNS = [
    (re.compile(r"Bearer\s+[\w\.\-_]+", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"password['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE), "password: [REDACTED]"),
    (re.compile(r"token['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE), "token: [REDACTED]"),
    (re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "[REDACTED_PAN]"),  # Card number
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
]


def redact_sensitive_info(text: str) -> str:
    """Redacts tokens, passwords, card numbers, and secret values."""
    if not text:
        return ""
    clean = str(text)
    for pattern, repl in _SENSITIVE_PATTERNS:
        clean = pattern.sub(repl, clean)
    return clean


def normalize_path(path: str) -> str:
    """Normalizes URL paths to prevent high-cardinality metrics (replaces UUIDs, numeric IDs)."""
    # Replace UUIDs
    p = re.sub(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        ":id",
        path,
    )
    # Replace numeric segments
    p = re.sub(r"/\d+(?=/|$)", "/:id", p)
    # Replace query string if present
    if "?" in p:
        p = p.split("?")[0]
    return p or "/"


def record_http_request(method: str, path: str, status_code: int, duration_ms: float, client_ip: str = "internal"):
    """Records an incoming HTTP request in telemetry buffers."""
    norm_path = normalize_path(path)
    now_ts = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()

    with _metrics_lock:
        _counters["total_requests"] += 1
        if 200 <= status_code < 300:
            _counters["status_2xx"] += 1
        elif 300 <= status_code < 400:
            _counters["status_3xx"] += 1
        elif 400 <= status_code < 500:
            _counters["status_4xx"] += 1
        elif status_code >= 500:
            _counters["status_5xx"] += 1

        record = {
            "timestamp": now_ts,
            "datetime": now_iso,
            "method": method.upper(),
            "endpoint": norm_path,
            "status_code": status_code,
            "duration_ms": duration_ms,
        }
        _request_records.append(record)

        # Per-endpoint breakdown
        ep_key = f"{method.upper()} {norm_path}"
        if ep_key not in _endpoint_stats:
            _endpoint_stats[ep_key] = {
                "method": method.upper(),
                "endpoint": norm_path,
                "count": 0,
                "total_ms": 0.0,
                "errors": 0,
                "min_ms": duration_ms,
                "max_ms": duration_ms,
                "durations": deque(maxlen=200),
            }
        stat = _endpoint_stats[ep_key]
        stat["count"] += 1
        stat["total_ms"] += duration_ms
        stat["min_ms"] = min(stat["min_ms"], duration_ms)
        stat["max_ms"] = max(stat["max_ms"], duration_ms)
        stat["durations"].append(duration_ms)
        if status_code >= 400:
            stat["errors"] += 1


def record_error(error_type: str, message: str, endpoint: Optional[str] = None, status_code: int = 500):
    """Records an application error with sensitive data redacted."""
    safe_msg = redact_sensitive_info(message)
    with _metrics_lock:
        _error_records.append({
            "timestamp": time.time(),
            "datetime": datetime.now(timezone.utc).isoformat(),
            "type": error_type,
            "message": safe_msg,
            "endpoint": normalize_path(endpoint) if endpoint else None,
            "status_code": status_code,
        })


def record_db_query(duration_ms: float, is_slow: bool = False, failed: bool = False):
    """Records a database query latency metric."""
    with _metrics_lock:
        _counters["db_queries_total"] += 1
        if is_slow:
            _counters["db_slow_queries_total"] += 1
        if failed:
            _counters["db_errors_total"] += 1
        _db_latency_records.append(duration_ms)


def record_idempotency_event(event_type: str):
    """Tracks idempotency conflict or replay."""
    with _metrics_lock:
        if event_type == "conflict":
            _counters["idempotency_conflicts_total"] += 1
        elif event_type == "replay":
            _counters["idempotency_replays_total"] += 1


def _calculate_percentile(sorted_values: List[float], p: float) -> float:
    """Calculates percentile p (0.0 to 1.0) using linear interpolation."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return round(sorted_values[0], 2)
    k = (len(sorted_values) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    d = k - f
    val = sorted_values[f] + d * (sorted_values[c] - sorted_values[f])
    return round(val, 2)


def get_system_resources() -> Dict[str, Any]:
    """Inspects backend process and system memory/CPU safely without requiring psutil."""
    now_iso = datetime.now(timezone.utc).isoformat()
    system_info = {
        "timestamp": now_iso,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count() or 1,
        "process_id": os.getpid(),
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "started_at": START_DATETIME.isoformat(),
        "memory_percent": None,
        "memory_total_mb": None,
        "memory_avail_mb": None,
        "process_memory_mb": None,
        "process_cpu_time_s": None,
        "environment": "development/demo",
    }

    # Attempt Windows API retrieval via ctypes
    if sys.platform == "win32":
        try:
            from ctypes import wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                system_info["memory_percent"] = stat.dwMemoryLoad
                system_info["memory_total_mb"] = stat.ullTotalPhys // (1024 * 1024)
                system_info["memory_avail_mb"] = stat.ullAvailPhys // (1024 * 1024)

            # Process times
            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

            creation = FILETIME()
            exit_t = FILETIME()
            kernel = FILETIME()
            user = FILETIME()
            h_proc = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.kernel32.GetProcessTimes(h_proc, ctypes.byref(creation), ctypes.byref(exit_t), ctypes.byref(kernel), ctypes.byref(user)):
                k_time = (kernel.dwHighDateTime << 32) + kernel.dwLowDateTime
                u_time = (user.dwHighDateTime << 32) + user.dwLowDateTime
                system_info["process_cpu_time_s"] = round((k_time + u_time) / 10000000.0, 3)

        except Exception:
            pass

    return system_info


def get_api_performance(window_seconds: Optional[int] = None) -> Dict[str, Any]:
    """Aggregates latency percentiles, error rates, and endpoint breakdowns for the selected window."""
    now_ts = time.time()
    with _metrics_lock:
        if window_seconds:
            min_ts = now_ts - window_seconds
            samples = [r for r in _request_records if r["timestamp"] >= min_ts]
        else:
            samples = list(_request_records)

        err_samples = list(_error_records)

    total_reqs = len(samples)
    if total_reqs == 0:
        return {
            "window_seconds": window_seconds,
            "total_requests": 0,
            "success_requests": 0,
            "failed_requests": 0,
            "success_rate_pct": 100.0,
            "failed_rate_pct": 0.0,
            "status_2xx": 0,
            "status_3xx": 0,
            "status_4xx": 0,
            "status_5xx": 0,
            "avg_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "min_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "slowest_endpoints": [],
            "recent_latency_series": [],
            "recent_errors": err_samples[-10:] if err_samples else [],
        }

    durations = sorted([r["duration_ms"] for r in samples])
    status_2xx = sum(1 for r in samples if 200 <= r["status_code"] < 300)
    status_3xx = sum(1 for r in samples if 300 <= r["status_code"] < 400)
    status_4xx = sum(1 for r in samples if 400 <= r["status_code"] < 500)
    status_5xx = sum(1 for r in samples if r["status_code"] >= 500)
    failed = status_4xx + status_5xx
    success = status_2xx + status_3xx

    avg_ms = round(sum(durations) / total_reqs, 2)
    p50_ms = _calculate_percentile(durations, 0.50)
    p95_ms = _calculate_percentile(durations, 0.95)
    p99_ms = _calculate_percentile(durations, 0.99)

    # Slowest endpoints ranking
    slowest_list = []
    with _metrics_lock:
        for ep_key, stat in _endpoint_stats.items():
            if stat["count"] > 0:
                ep_avg = round(stat["total_ms"] / stat["count"], 2)
                sorted_durs = sorted(list(stat["durations"]))
                ep_p95 = _calculate_percentile(sorted_durs, 0.95)
                slowest_list.append({
                    "endpoint_key": ep_key,
                    "method": stat["method"],
                    "endpoint": stat["endpoint"],
                    "total_calls": stat["count"],
                    "errors": stat["errors"],
                    "avg_duration_ms": ep_avg,
                    "p95_duration_ms": ep_p95,
                    "max_duration_ms": round(stat["max_ms"], 2),
                })
    slowest_list.sort(key=lambda x: x["p95_duration_ms"], reverse=True)

    # Bucket recent requests into time-series buckets (last 20 intervals)
    series = []
    if samples:
        first_ts = samples[0]["timestamp"]
        span = max(1.0, now_ts - first_ts)
        bucket_count = min(20, total_reqs)
        bucket_size = span / bucket_count if bucket_count > 0 else 1.0

        for b in range(bucket_count):
            b_start = first_ts + b * bucket_size
            b_end = b_start + bucket_size
            b_items = [r for r in samples if b_start <= r["timestamp"] < b_end]
            if b_items:
                b_durs = sorted([r["duration_ms"] for r in b_items])
                series.append({
                    "time": datetime.fromtimestamp(b_start, timezone.utc).strftime("%H:%M:%S"),
                    "avg_ms": round(sum(b_durs) / len(b_durs), 2),
                    "p95_ms": _calculate_percentile(b_durs, 0.95),
                    "requests": len(b_items),
                    "errors": sum(1 for r in b_items if r["status_code"] >= 400),
                })

    return {
        "window_seconds": window_seconds,
        "total_requests": total_reqs,
        "success_requests": success,
        "failed_requests": failed,
        "success_rate_pct": round((success / total_reqs) * 100, 2),
        "failed_rate_pct": round((failed / total_reqs) * 100, 2),
        "status_2xx": status_2xx,
        "status_3xx": status_3xx,
        "status_4xx": status_4xx,
        "status_5xx": status_5xx,
        "avg_latency_ms": avg_ms,
        "p50_latency_ms": p50_ms,
        "p95_latency_ms": p95_ms,
        "p99_latency_ms": p99_ms,
        "min_latency_ms": round(durations[0], 2),
        "max_latency_ms": round(durations[-1], 2),
        "slowest_endpoints": slowest_list[:10],
        "recent_latency_series": series,
        "recent_errors": [
            {
                "time": e["datetime"],
                "type": e["type"],
                "message": e["message"],
                "endpoint": e["endpoint"],
                "status_code": e["status_code"],
            }
            for e in reversed(err_samples[-15:])
        ],
    }


def get_db_metrics() -> Dict[str, Any]:
    """Calculates database query latencies and health indicators."""
    with _metrics_lock:
        durations = sorted(list(_db_latency_records))
        total_queries = _counters["db_queries_total"]
        slow_queries = _counters["db_slow_queries_total"]
        error_queries = _counters["db_errors_total"]

    if not durations:
        return {
            "total_queries": total_queries,
            "slow_queries": slow_queries,
            "failed_queries": error_queries,
            "avg_query_ms": 0.0,
            "p50_query_ms": 0.0,
            "p95_query_ms": 0.0,
            "p99_query_ms": 0.0,
            "status": "connected",
        }

    return {
        "total_queries": total_queries,
        "slow_queries": slow_queries,
        "failed_queries": error_queries,
        "avg_query_ms": round(sum(durations) / len(durations), 2),
        "p50_query_ms": _calculate_percentile(durations, 0.50),
        "p95_query_ms": _calculate_percentile(durations, 0.95),
        "p99_query_ms": _calculate_percentile(durations, 0.99),
        "status": "connected",
    }
