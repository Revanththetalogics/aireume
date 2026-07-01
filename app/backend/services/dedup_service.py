"""Resume deduplication service.

Computes content hashes from resume text to detect duplicate uploads
and prevent creating separate candidate records for the same person.
"""

import hashlib
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def compute_resume_hash(resume_text: str) -> str:
    """Compute a normalized content hash for a resume.

    Normalizes whitespace, removes common boilerplate, and produces
    a SHA-256 hash of the normalized content. Two resumes with the
    same content but different formatting will produce the same hash.

    Args:
        resume_text: Raw extracted resume text.

    Returns:
        Hex string hash (first 32 chars of SHA-256).
    """
    if not resume_text:
        return ""

    # Normalize: lowercase, collapse whitespace, remove common boilerplate
    text = resume_text.lower().strip()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove page numbers, headers/footers
    text = re.sub(r'\bpage\s+\d+\b', '', text)
    # Remove common resume boilerplate phrases
    boilerplate = [
        r'references available upon request',
        r'curriculum vitae',
        r'resume',
    ]
    for pattern in boilerplate:
        text = re.sub(pattern, '', text)
    # Final whitespace cleanup
    text = re.sub(r'\s+', ' ', text).strip()

    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]


def compute_email_hash(email: str) -> str:
    """Compute a normalized hash for an email address."""
    if not email:
        return ""
    email = email.strip().lower()
    return hashlib.sha256(email.encode('utf-8')).hexdigest()[:16]


def find_duplicate_candidate(
    db,
    tenant_id: int,
    resume_text: str,
    email: Optional[str] = None,
) -> Tuple[bool, Optional[int]]:
    """Check if a candidate with the same resume content already exists.

    Args:
        db: Database session.
        tenant_id: Tenant ID for isolation.
        resume_text: Resume text to check.
        email: Optional email for faster lookup.

    Returns:
        Tuple of (is_duplicate, existing_candidate_id).
    """
    from app.backend.models.db_models import Candidate

    resume_hash = compute_resume_hash(resume_text)
    if not resume_hash:
        return False, None

    # Check by email first (fastest, most reliable)
    if email:
        email_h = compute_email_hash(email)
        existing = db.query(Candidate).filter(
            Candidate.tenant_id == tenant_id,
            Candidate.email == email,
        ).first()
        if existing:
            return True, existing.id

    # Check by resume content hash
    existing = db.query(Candidate).filter(
        Candidate.tenant_id == tenant_id,
        Candidate.resume_file_hash == resume_hash,
    ).first()

    if existing:
        return True, existing.id

    return False, None
