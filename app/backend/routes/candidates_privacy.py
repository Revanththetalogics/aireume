"""GDPR candidate routes — extracted from candidates.py."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import require_admin
from app.backend.models.db_models import User


def register_privacy_routes(router: APIRouter) -> None:
    @router.delete("/{candidate_id}/gdpr-delete")
    def gdpr_hard_delete_candidate(
        candidate_id: int,
        reason: str = "gdpr_request",
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin),
    ):
        from app.backend.services.gdpr_service import hard_delete_candidate
        result = hard_delete_candidate(db, candidate_id, current_user.tenant_id, reason=reason)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @router.get("/{candidate_id}/gdpr-export")
    def gdpr_export_candidate_data(
        candidate_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin),
    ):
        from app.backend.services.gdpr_service import export_candidate_data
        data = export_candidate_data(db, candidate_id, current_user.tenant_id)
        if "error" in data:
            raise HTTPException(status_code=404, detail=data["error"])
        return data

    @router.post("/{candidate_id}/gdpr-anonymize")
    def gdpr_anonymize_candidate(
        candidate_id: int,
        reason: str = "retention_expiry",
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin),
    ):
        from app.backend.services.gdpr_service import anonymize_candidate
        result = anonymize_candidate(db, candidate_id, current_user.tenant_id, reason=reason)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
