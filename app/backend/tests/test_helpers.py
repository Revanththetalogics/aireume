"""
Shared test utilities that can be safely imported by test modules
without triggering conftest.py re-initialization.
"""
from app.backend.db import database


def _verify_user_via_api(email: str):
    """Mark a user's email as verified via the DB session.

    Uses ``database.SessionLocal`` which is set to ``TestingSessionLocal``
    by conftest.py at startup, so it always targets the in-memory test DB
    regardless of which module scope the caller lives in.
    """
    from app.backend.models.db_models import User
    db = database.SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.email_verified = True
            db.commit()
    finally:
        db.close()
