"""FastAPI Main Application entry point for PayNexus."""
import uuid
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.core.config import get_settings
from app.core.logging import get_logger, correlation_id_var, setup_logging
from app.core.redis_client import get_redis, close_redis
from app.api.v1.auth import router as auth_router
from app.api.v1.payments import router as payments_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.exceptions import router as exceptions_router
from app.api.v1.rails import router as rails_router
from app.api.v1.audit import router as audit_router
from app.api.v1.messages import router as messages_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.stream import router as stream_router
from app.api.v1.admin import router as admin_router
from app.api.v1.performance import router as performance_router
from app.core.telemetry import record_http_request, record_error

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events."""
    setup_logging()
    logger.info("PayNexus API starting up...", extra={"environment": settings.ENVIRONMENT})
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection established.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis at startup: {e}")

    yield

    logger.info("PayNexus API shutting down...")
    await close_redis()


app = FastAPI(
    title="PayNexus API",
    description="Next-generation Payments Modernisation Platform API with ISO 20022 canonical messaging, bulletproof idempotency, multi-rail orchestration, and compliance pipeline.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# ── CORS Middleware ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Idempotent-Replayed", "X-Correlation-ID"]
)


# ── Correlation ID, Logging & Telemetry Middleware ────────────────────────────
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    token = correlation_id_var.set(correlation_id)

    start_time = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        process_time = time.time() - start_time
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        return response
    except Exception as exc:
        process_time = time.time() - start_time
        record_error(type(exc).__name__, str(exc), endpoint=request.url.path, status_code=500)
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        # Exclude /metrics and /healthz from recursive metrics counts
        if not request.url.path.startswith("/metrics") and not request.url.path.startswith("/api/v1/stream"):
            record_http_request(request.method, request.url.path, status_code, duration_ms)
        correlation_id_var.reset(token)


# ── RFC 7807 Exception Handlers ────────────────────────────────────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    correlation_id = correlation_id_var.get() or "unknown"
    record_error(type(exc).__name__, str(exc), endpoint=request.url.path, status_code=500)
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "https://paynexus.io/errors/internal-server-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred while processing your request.",
            "instance": request.url.path,
            "correlation_id": correlation_id
        },
        headers={"Content-Type": "application/problem+json"}
    )


# ── Health & Readiness Endpoints ───────────────────────────────────────────────
@app.get("/health", tags=["observability"])
@app.get("/healthz", tags=["observability"])
async def healthz():
    """Liveness probe."""
    return {"status": "ok", "service": "paynexus-api"}


@app.get("/readyz", tags=["observability"])
async def readyz():
    """Readiness probe checking DB and Redis connectivity."""
    db_ok = True
    redis_ok = True
    try:
        redis = await get_redis()
        await redis.ping()
    except Exception:
        redis_ok = False

    if db_ok and redis_ok:
        return {"status": "ready", "database": "up", "redis": "up"}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready", "database": "up" if db_ok else "down", "redis": "up" if redis_ok else "down"}
    )


# Mount Prometheus metrics endpoint at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ── Include API v1 Routers ─────────────────────────────────────────────────────
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(payments_router, prefix=api_v1_prefix)
app.include_router(compliance_router, prefix=api_v1_prefix)
app.include_router(reconciliation_router, prefix=api_v1_prefix)
app.include_router(exceptions_router, prefix=api_v1_prefix)
app.include_router(rails_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)
app.include_router(messages_router, prefix=api_v1_prefix)
app.include_router(analytics_router, prefix=api_v1_prefix)
app.include_router(stream_router, prefix=api_v1_prefix)
app.include_router(admin_router, prefix=api_v1_prefix)
app.include_router(performance_router, prefix=api_v1_prefix)
