"""User profile preferences (notifications, first-visit modals)."""
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.services.user_preferences_service import load_preferences, merge_preferences, mark_modal_seen

router = APIRouter(prefix="/api/users", tags=["users"])


class NotificationPreferences(BaseModel):
    emailOnComplete: bool | None = None
    emailOnBatchComplete: bool | None = None
    marketing: bool | None = None


class PreferencesPatch(BaseModel):
    notifications: NotificationPreferences | None = None
    invited_welcome_dismissed: bool | None = None


class MarkModalSeenRequest(BaseModel):
    modal_id: str = Field(..., min_length=1, max_length=80)


@router.get("/me/preferences")
def get_my_preferences(current_user=Depends(get_current_user)):
    return {"preferences": load_preferences(current_user)}


@router.patch("/me/preferences")
def patch_my_preferences(
    body: PreferencesPatch,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patch = {}
    if body.notifications is not None:
        patch["notifications"] = body.notifications.model_dump(exclude_none=True)
    if body.invited_welcome_dismissed is not None:
        patch["invited_welcome_dismissed"] = body.invited_welcome_dismissed
    prefs = merge_preferences(current_user, patch, db)
    return {"preferences": prefs}


@router.post("/me/preferences/seen-modal")
def post_seen_modal(
    body: MarkModalSeenRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = mark_modal_seen(current_user, body.modal_id, db)
    return {"preferences": prefs}
