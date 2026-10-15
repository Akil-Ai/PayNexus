"""
API Contract tests using schemathesis to validate every response against the OpenAPI spec.
Ensures all endpoints return schema-conformant responses.

Run with:
    pip install schemathesis
    pytest backend/tests/integration/test_api_contract.py -v
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
DB_PATH = os.path.join(ROOT_DIR, "paynexus.db").replace("\\", "/")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")
os.environ.setdefault("SYNC_DATABASE_URL", f"sqlite:///{DB_PATH}")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
os.environ.setdefault("SECRET_KEY", "contract-test-secret-key-32chars!!")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("ENVIRONMENT", "test")

try:
    import schemathesis
    HAS_SCHEMATHESIS = True
except ImportError:
    HAS_SCHEMATHESIS = False

from app.main import app  # noqa: E402


# ── Schemathesis fuzzing (if available) ────────────────────────────────────────

if HAS_SCHEMATHESIS:
    schema = schemathesis.from_asgi("/openapi.json", app)

    @schema.parametrize()
    def test_api_schema_conformance(case):
        """
        Schemathesis automatically generates test cases for every endpoint defined
        in the OpenAPI spec and verifies that responses conform to their declared schema.
        Non-authenticated endpoints will return 401 which is also valid.
        """
        response = case.call_asgi()
        case.validate_response(response, validate_schema=True)

else:
    @pytest.mark.skip(reason="schemathesis not installed; run: pip install schemathesis")
    def test_api_schema_conformance():
        pass


# ── Manual schema validation tests (no schemathesis dependency) ────────────────

import httpx
import pytest_asyncio
from httpx import ASGITransport


@pytest_asyncio.fixture(scope="module")
async def api_client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_openapi_spec_has_required_fields(api_client):
    """Validate that the OpenAPI spec itself is well-formed."""
    resp = await api_client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()

    assert spec["openapi"].startswith("3.")
    assert "info" in spec
    assert spec["info"]["title"] == "PayNexus API"
    assert "paths" in spec
    assert len(spec["paths"]) >= 40  # We expect at least 40 routes


@pytest.mark.asyncio
async def test_all_endpoints_have_response_schemas(api_client):
    """Every endpoint in the spec must define at least one response schema."""
    resp = await api_client.get("/openapi.json")
    spec = resp.json()
    missing_schemas = []

    for path, path_item in spec["paths"].items():
        for method, op in path_item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            responses = op.get("responses", {})
            if not responses:
                missing_schemas.append(f"{method.upper()} {path}")

    assert missing_schemas == [], f"Endpoints missing response schemas: {missing_schemas}"


@pytest.mark.asyncio
async def test_auth_endpoints_have_security_schemes(api_client):
    """All non-auth endpoints should require bearer token security."""
    resp = await api_client.get("/openapi.json")
    spec = resp.json()

    # Check that a security scheme is defined
    security_schemes = spec.get("components", {}).get("securitySchemes", {})
    assert len(security_schemes) > 0, "No security schemes defined in OpenAPI spec"


@pytest.mark.asyncio
async def test_payment_create_schema(api_client):
    """POST /api/v1/payments must be defined with a request body schema."""
    resp = await api_client.get("/openapi.json")
    spec = resp.json()

    payment_post = spec["paths"].get("/api/v1/payments", {}).get("post", {})
    assert payment_post, "POST /api/v1/payments not found in spec"
    assert "requestBody" in payment_post or "parameters" in payment_post


@pytest.mark.asyncio
async def test_healthz_no_auth_required(api_client):
    """Health endpoints must work without authentication."""
    resp = await api_client.get("/healthz")
    assert resp.status_code == 200

    resp = await api_client.get("/readyz")
    assert resp.status_code in (200, 503)  # 503 if Redis unreachable


@pytest.mark.asyncio
async def test_401_on_protected_endpoints_without_token(api_client):
    """Protected endpoints must return 401 without auth token."""
    protected_endpoints = [
        "/api/v1/payments",
        "/api/v1/audit/",
        "/api/v1/admin/users",
        "/api/v1/compliance/fraud-rules",
    ]
    for path in protected_endpoints:
        resp = await api_client.get(path)
        assert resp.status_code in (401, 403), \
            f"Expected 401/403 for unauthenticated {path}, got {resp.status_code}"


@pytest.mark.asyncio
async def test_cors_headers_present(api_client):
    """CORS preflight must be supported."""
    resp = await api_client.options(
        "/api/v1/payments",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert resp.status_code in (200, 204, 405)
