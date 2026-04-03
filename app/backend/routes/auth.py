"""
Authentication routes: register, login, refresh, me.
"""
import os
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user, SECRET_KEY, ALGORITHM
from app.backend.models.db_models import Tenant, User
from app.backend.models.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE_MINUTES  = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES",  "60"))
REFRESH_TOKEN_EXPIRE_DAYS    = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS",    "30"))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(data: dict, expires_delta: timedelta) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + expires_delta}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _make_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _tenant_dict(tenant: Tenant) -> dict:
    return {"id": tenant.id, "name": tenant.name, "slug": tenant.slug}


def _user_dict(user: User) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role, "tenant_id": user.tenant_id}


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Create tenant
    base_slug = _make_slug(body.company_name)
    slug      = base_slug
    counter   = 1
    while db.query(Tenant).filter(Tenant.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    tenant = Tenant(name=body.company_name, slug=slug)
    db.add(tenant)
    db.flush()  # get tenant.id

    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=_hash_password(body.password),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token  = _create_token({"sub": str(user.id)}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = _create_token({"sub": str(user.id), "type": "refresh"}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_dict(user),
        tenant=_tenant_dict(tenant),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email, User.is_active == True).first()
    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()

    access_token  = _create_token({"sub": str(user.id)}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = _create_token({"sub": str(user.id), "type": "refresh"}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_dict(user),
        tenant=_tenant_dict(tenant),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    from jose import JWTError
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user   = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user else None
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token  = _create_token({"sub": str(user.id)}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    new_refresh   = _create_token({"sub": str(user.id), "type": "refresh"}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=_user_dict(user),
        tenant=_tenant_dict(tenant),
    )


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    return {
        "user": _user_dict(current_user),
        "tenant": _tenant_dict(tenant) if tenant else None,
    }
