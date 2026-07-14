"""Saved analytics views — pin filters and default landing preferences."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import SavedAnalyticsView

VALID_VIEW_TYPES = frozenset({"explore", "overview"})


def _serialize(view: SavedAnalyticsView) -> dict[str, Any]:
    return {
        "id": view.id,
        "name": view.name,
        "view_type": view.view_type,
        "slice": view.slice,
        "filters": view.filters or {},
        "is_default": view.is_default,
        "created_at": view.created_at.isoformat() if view.created_at else None,
        "updated_at": view.updated_at.isoformat() if view.updated_at else None,
    }


def list_views(db: Session, tenant_id: int, user_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(SavedAnalyticsView)
        .filter(
            SavedAnalyticsView.tenant_id == tenant_id,
            SavedAnalyticsView.user_id == user_id,
        )
        .order_by(SavedAnalyticsView.is_default.desc(), SavedAnalyticsView.updated_at.desc())
        .all()
    )
    return [_serialize(v) for v in rows]


def get_default_view(db: Session, tenant_id: int, user_id: int) -> Optional[dict[str, Any]]:
    row = (
        db.query(SavedAnalyticsView)
        .filter(
            SavedAnalyticsView.tenant_id == tenant_id,
            SavedAnalyticsView.user_id == user_id,
            SavedAnalyticsView.is_default.is_(True),
        )
        .first()
    )
    return _serialize(row) if row else None


def create_view(
    db: Session,
    tenant_id: int,
    user_id: int,
    *,
    name: str,
    view_type: str = "explore",
    slice: Optional[str] = None,
    filters: Optional[dict] = None,
    is_default: bool = False,
) -> dict[str, Any]:
    if view_type not in VALID_VIEW_TYPES:
        raise ValueError(f"view_type must be one of {sorted(VALID_VIEW_TYPES)}")

    if is_default:
        db.query(SavedAnalyticsView).filter(
            SavedAnalyticsView.tenant_id == tenant_id,
            SavedAnalyticsView.user_id == user_id,
            SavedAnalyticsView.is_default.is_(True),
        ).update({"is_default": False})

    row = SavedAnalyticsView(
        tenant_id=tenant_id,
        user_id=user_id,
        name=name.strip(),
        view_type=view_type,
        slice=slice,
        filters=filters or {},
        is_default=is_default,
    )
    db.add(row)
    db.flush()
    return _serialize(row)


def update_view(
    db: Session,
    tenant_id: int,
    user_id: int,
    view_id: int,
    *,
    name: Optional[str] = None,
    slice: Optional[str] = None,
    filters: Optional[dict] = None,
    is_default: Optional[bool] = None,
) -> dict[str, Any]:
    row = (
        db.query(SavedAnalyticsView)
        .filter(
            SavedAnalyticsView.id == view_id,
            SavedAnalyticsView.tenant_id == tenant_id,
            SavedAnalyticsView.user_id == user_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Saved view not found")

    if name is not None:
        row.name = name.strip()
    if slice is not None:
        row.slice = slice
    if filters is not None:
        row.filters = filters
    if is_default is True:
        db.query(SavedAnalyticsView).filter(
            SavedAnalyticsView.tenant_id == tenant_id,
            SavedAnalyticsView.user_id == user_id,
            SavedAnalyticsView.is_default.is_(True),
        ).update({"is_default": False})
        row.is_default = True
    elif is_default is False:
        row.is_default = False

    db.flush()
    return _serialize(row)


def delete_view(db: Session, tenant_id: int, user_id: int, view_id: int) -> None:
    row = (
        db.query(SavedAnalyticsView)
        .filter(
            SavedAnalyticsView.id == view_id,
            SavedAnalyticsView.tenant_id == tenant_id,
            SavedAnalyticsView.user_id == user_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Saved view not found")
    db.delete(row)
