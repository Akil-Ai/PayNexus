"""Auth router: login, refresh, logout, register (admin only)."""
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_password, hash_password, create_access_token,
    create_refresh_token, decode_token,
)
from app.db.database import get_db
from app.models import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: extract and validate JWT, return current user."""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Try cookie
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


def require_roles(*roles: Any):
    """Dependency factory for RBAC. Supports both varargs require_roles(A, B) and list require_roles([A, B])."""
    flattened_roles: list[Any] = []
    for r in roles:
        if isinstance(r, (list, tuple, set)):
            flattened_roles.extend(r)
        else:
            flattened_roles.append(r)

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in flattened_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role {current_user.role.value} not authorized for this action. "
                       f"Required: {[r.value if hasattr(r, 'value') else str(r) for r in flattened_roles]}",
            )
        return current_user
    return _check


async def _authenticate_user(db: AsyncSession, username_or_email: str, password: str) -> LoginResponse:
    result = await db.execute(
        select(User).where(User.email == username_or_email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Update last login
    await db.execute(
        update(User).where(User.id == user.id).values(last_login_at=datetime.now(timezone.utc))
    )
    await db.commit()

    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    return LoginResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user_id=user.id,
        email=user.email,
        role=user.role.value,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Universal login endpoint supporting JSON and form data."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        username = body.get("email") or body.get("username", "")
        password = body.get("password", "")
    else:
        form = await request.form()
        username = form.get("username") or form.get("email", "")
        password = form.get("password", "")

    return await _authenticate_user(db, str(username), str(password))


@router.post("/token", response_model=LoginResponse)
async def token_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """OAuth2 /token alias."""
    return await login(request, db)



@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    return LoginResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user_id=user.id,
        email=user.email,
        role=user.role.value,
    )


@router.post("/register", status_code=201)
async def register_user(
    body: RegisterRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Admin only: create a new user."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    import uuid
    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    return {"id": user.id, "email": user.email, "role": user.role.value}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "last_login_at": current_user.last_login_at,
    }
