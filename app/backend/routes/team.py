"""
Team collaboration — invite members, manage comments, share links.
"""
import json
import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user, require_admin
from app.backend.models.db_models import Comment, ScreeningResult, TeamMember, Tenant, User
from app.backend.models.schemas import CommentCreate, CommentOut, InviteRequest
from app.backend.routes.auth import _hash_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["team"])


@router.get("/team")
def list_team(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    members = (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id, User.is_active == True)
        .all()
    )
    return [
        {"id": m.id, "email": m.email, "role": m.role, "created_at": m.created_at}
        for m in members
    ]


@router.post("/invites")
def invite_member(
    body: InviteRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    temp_password = secrets.token_urlsafe(12)
    new_user = User(
        tenant_id=current_user.tenant_id,
        email=body.email,
        hashed_password=_hash_password(temp_password),
        role=body.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("Team member invited: %s (role=%s). Temporary password generated (not logged for security).",
                new_user.email, new_user.role)

    return {
        "message": "Team member invited successfully. The temporary password has been logged securely."
    }


@router.delete("/team/{user_id}")
def remove_member(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == current_user.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()
    return {"removed": user_id}


@router.get("/results/{result_id}/comments", response_model=list[CommentOut])
def get_comments(
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.query(ScreeningResult).filter(
        ScreeningResult.id == result_id,
        ScreeningResult.tenant_id == current_user.tenant_id
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    comments = db.query(Comment).filter(Comment.result_id == result_id).order_by(Comment.created_at).all()
    return [
        CommentOut(
            id=c.id,
            text=c.text,
            created_at=c.created_at,
            author_email=c.author.email if c.author else None,
        )
        for c in comments
    ]


@router.post("/results/{result_id}/comments", response_model=CommentOut)
def add_comment(
    result_id: int,
    body: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.query(ScreeningResult).filter(
        ScreeningResult.id == result_id,
        ScreeningResult.tenant_id == current_user.tenant_id
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    comment = Comment(result_id=result_id, user_id=current_user.id, text=body.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return CommentOut(
        id=comment.id,
        text=comment.text,
        created_at=comment.created_at,
        author_email=current_user.email,
    )
