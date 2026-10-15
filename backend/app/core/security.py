"""Security: JWT, password hashing, field encryption, API key generation."""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing with argon2
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# Field encryption
_fernet: Optional[Fernet] = None


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.field_encryption_key.encode()
        _fernet = Fernet(key)
    return _fernet


# ── Passwords ─────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


# ── Field Encryption ──────────────────────────────────────────────────────────

def encrypt_field(value: str) -> str:
    """Encrypt sensitive field value."""
    return get_fernet().encrypt(value.encode()).decode()


def decrypt_field(encrypted_value: str) -> str:
    """Decrypt sensitive field value."""
    return get_fernet().decrypt(encrypted_value.encode()).decode()


def mask_account_number(account_number: str) -> str:
    """Return masked account number showing only last 4 digits."""
    if len(account_number) <= 4:
        return "****"
    return "*" * (len(account_number) - 4) + account_number[-4:]


# ── API Key Generation ────────────────────────────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """Generate API key. Returns (full_key, prefix, hash)."""
    key = f"pnx_{secrets.token_urlsafe(32)}"
    prefix = key[:12]
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, prefix, key_hash


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    return hmac.compare_digest(key_hash, stored_hash)


# ── HMAC Webhook Signatures ───────────────────────────────────────────────────

def sign_webhook_payload(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook delivery."""
    return "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()


# ── Audit Hash Chain ──────────────────────────────────────────────────────────

def compute_audit_hash(prev_hash: Optional[str], row_content: str) -> str:
    """SHA256 of concatenated prev_hash + row_content."""
    data = (prev_hash or "") + row_content
    return hashlib.sha256(data.encode()).hexdigest()


def build_audit_row_content(entry: dict) -> str:
    """Deterministic string for hashing an audit log row."""
    import json
    fields = ["sequence", "entity_type", "entity_id", "action", "actor_id",
              "actor_type", "correlation_id", "created_at"]
    content = {k: str(entry.get(k, "")) for k in fields}
    return json.dumps(content, sort_keys=True)
