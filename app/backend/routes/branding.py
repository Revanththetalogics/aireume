"""White-label branding and custom domain resolution."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user, require_admin, require_feature
from app.backend.models.db_models import Tenant, User

router = APIRouter(prefix="/api/branding", tags=["branding"])


class BrandingUpdateRequest(BaseModel):
    brand_name: Optional[str] = Field(None, max_length=200)
    brand_logo_url: Optional[str] = Field(None, max_length=500)
    brand_primary_color: Optional[str] = Field(None, max_length=20)
    brand_favicon_url: Optional[str] = Field(None, max_length=500)
    custom_domain: Optional[str] = Field(None, max_length=255)


def _branding_dict(tenant: Tenant) -> dict:
    return {
        "brand_name": tenant.brand_name or tenant.name,
        "brand_logo_url": tenant.brand_logo_url,
        "brand_primary_color": tenant.brand_primary_color or "#4F46E5",
        "brand_favicon_url": tenant.brand_favicon_url,
        "custom_domain": tenant.custom_domain,
        "slug": tenant.slug,
    }


@router.get("/resolve")
def resolve_branding(host: str = "", db: Session = Depends(get_db)):
    """Public: resolve branding by Host header or ?host= query."""
    hostname = (host or "").lower().strip()
    if not hostname:
        return {"branding": None}
    tenant = db.query(Tenant).filter(
        Tenant.custom_domain == hostname,
        Tenant.deleted_at.is_(None),
    ).first()
    if not tenant:
        return {"branding": None}
    return {"branding": _branding_dict(tenant), "tenant_id": tenant.id}


@router.get("/me")
def get_my_branding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"branding": _branding_dict(tenant)}


@router.put("/me", dependencies=[Depends(require_feature("white_label"))])
def update_my_branding(
    body: BrandingUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.custom_domain is not None:
        domain = body.custom_domain.strip().lower() or None
        if domain:
            existing = db.query(Tenant).filter(
                Tenant.custom_domain == domain,
                Tenant.id != tenant.id,
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Custom domain already in use")
        tenant.custom_domain = domain

    if body.brand_name is not None:
        tenant.brand_name = body.brand_name.strip() or None
    if body.brand_logo_url is not None:
        tenant.brand_logo_url = body.brand_logo_url.strip() or None
    if body.brand_primary_color is not None:
        tenant.brand_primary_color = body.brand_primary_color.strip() or None
    if body.brand_favicon_url is not None:
        tenant.brand_favicon_url = body.brand_favicon_url.strip() or None

    db.commit()
    db.refresh(tenant)
    return {"branding": _branding_dict(tenant)}
