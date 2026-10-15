"""Admin router: Users & Roles, API Clients, Webhook subscriptions, and System Settings."""
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_roles
from app.core.security import hash_password, generate_api_key
from app.db.database import get_db
from app.models import (
    User, UserRole, ApiClient, WebhookSubscription,
    WebhookDelivery, SystemSetting, Customer, Beneficiary, Account
)
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "OPERATIONS"


class ApiClientCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rate_limit_per_minute: int = 120


class WebhookSubCreate(BaseModel):
    url: str
    events: List[str] = ["payment.settled", "payment.failed", "payment.blocked"]
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None


# ── Users & Roles ─────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """List all registered platform users."""
    stmt = select(User).order_by(User.created_at.desc())
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [{
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role.value if hasattr(u.role, "value") else str(u.role),
        "is_active": u.is_active,
        "created_at": u.created_at
    } for u in users]


@router.post("/users")
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """Admin creates a new user."""
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    u = User(
        id=str(uuid.uuid4()),
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=UserRole(req.role),
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(u)
    await db.commit()

    await record_audit_log(
        db=db,
        entity_type="USER",
        entity_id=u.id,
        action="CREATE_USER",
        actor_id=current_user.id,
        actor_type="USER",
        new_values={"email": u.email, "role": u.role.value}
    )
    return {"message": "User created", "id": u.id, "email": u.email}


# ── API Clients & Keys ────────────────────────────────────────────────────────

@router.get("/api-clients")
async def list_api_clients(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """List all registered API client applications."""
    stmt = select(ApiClient).order_by(ApiClient.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/api-clients")
async def create_api_client(
    req: ApiClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """Issues a new API Client credential with masked key and raw secret."""
    raw_key, key_hash, prefix = generate_api_key()
    client = ApiClient(
        id=str(uuid.uuid4()),
        name=req.name,
        description=req.description,
        key_prefix=prefix,
        key_hash=key_hash,
        rate_limit_per_minute=req.rate_limit_per_minute,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(client)
    await db.commit()

    await record_audit_log(
        db=db,
        entity_type="API_CLIENT",
        entity_id=client.id,
        action="CREATE_KEY",
        actor_id=current_user.id,
        actor_type="USER",
        new_values={"name": client.name, "prefix": prefix}
    )
    return {
        "id": client.id,
        "name": client.name,
        "api_key": raw_key,
        "warning": "Store this API key safely; it will not be displayed again."
    }


# ── Webhook Subscriptions & Deliveries ────────────────────────────────────────

@router.get("/webhooks")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATIONS]))
):
    """List configured webhook endpoints."""
    stmt = select(WebhookSubscription).order_by(WebhookSubscription.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/webhooks")
async def create_webhook(
    req: WebhookSubCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """Registers a webhook endpoint with a generated HMAC secret."""
    secret = f"whsec_{secrets.token_hex(24)}"
    sub = WebhookSubscription(
        id=str(uuid.uuid4()),
        url=req.url,
        secret=secret,
        events=req.events,
        description=req.description,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(sub)
    await db.commit()
    return {"id": sub.id, "url": sub.url, "secret": secret}


@router.get("/webhooks/deliveries")
async def list_webhook_deliveries(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATIONS]))
):
    """List recent webhook delivery attempts."""
    stmt = select(WebhookDelivery).order_by(desc(WebhookDelivery.created_at)).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


# ── System Settings ───────────────────────────────────────────────────────────

@router.get("/settings")
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List runtime-configurable system settings."""
    stmt = select(SystemSetting).order_by(SystemSetting.key)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.put("/settings")
async def update_system_setting(
    setting: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """Update a system setting at runtime."""
    stmt = select(SystemSetting).where(SystemSetting.key == setting.key)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        item = SystemSetting(
            id=str(uuid.uuid4()),
            key=setting.key,
            value=setting.value,
            description=setting.description,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(item)
    else:
        old_val = item.value
        item.value = setting.value
        item.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await record_audit_log(
        db=db,
        entity_type="SYSTEM_SETTING",
        entity_id=setting.key,
        action="UPDATE_SETTING",
        actor_id=current_user.id,
        actor_type="USER",
        new_values={"key": setting.key, "value": setting.value}
    )
    return {"message": "Setting updated", "key": setting.key, "value": setting.value}


# ── Customers & Beneficiaries helper endpoints for UI forms ────────────────────

@router.get("/customers")
async def list_customers(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List customers with accounts for dropdown selection in payments form."""
    stmt = select(Customer).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/beneficiaries")
async def list_beneficiaries(
    customer_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List beneficiaries for dropdown selection."""
    query = select(Beneficiary)
    if customer_id:
        query = query.where(Beneficiary.customer_id == customer_id)
    query = query.limit(limit)
    res = await db.execute(query)
    return res.scalars().all()
