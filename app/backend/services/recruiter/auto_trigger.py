"""Auto-trigger logic for AI Recruiter interviews.

Evaluates whether a candidate status change should automatically initiate an
AI recruiter interview based on per-tenant configuration.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    Candidate,
    RecruiterAutoTriggerConfig,
    ScreeningResult,
)
from app.backend.services.recruiter.orchestrator import RecruiterOrchestrator

logger = logging.getLogger("aria.recruiter")


class RecruiterAutoTrigger:
    """Decides when to automatically start an AI recruiter interview."""

    def __init__(self, db: Session) -> None:
        self.db = db

    async def evaluate_trigger(
        self,
        tenant_id: int,
        candidate_id: int,
        screening_result_id: int,
        new_status: str,
    ) -> bool:
        """
        Evaluate whether an AI recruiter interview should be auto-triggered.

        Returns True if an interview was initiated, False otherwise.
        """
        config = self.db.execute(
            select(RecruiterAutoTriggerConfig).where(
                RecruiterAutoTriggerConfig.tenant_id == tenant_id
            )
        ).scalar_one_or_none()

        if config is None or not config.enabled:
            return False

        if new_status != config.trigger_pipeline_stage:
            return False

        screening = self.db.execute(
            select(ScreeningResult).where(
                ScreeningResult.id == screening_result_id,
                ScreeningResult.tenant_id == tenant_id,
                ScreeningResult.candidate_id == candidate_id,
            )
        ).scalar_one_or_none()

        if screening is None:
            logger.info(
                "Auto-trigger skipped: screening result %s not found",
                screening_result_id,
            )
            return False

        score = screening.deterministic_score
        if score is None:
            score = 0

        min_threshold = config.min_fit_score_threshold
        max_threshold = config.max_fit_score_threshold

        if not (min_threshold <= score <= max_threshold):
            logger.info(
                "Auto-trigger skipped: score %s outside thresholds [%s, %s]",
                score,
                min_threshold,
                max_threshold,
            )
            return False

        candidate = self.db.execute(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if candidate is None:
            logger.info(
                "Auto-trigger skipped: candidate %s not found", candidate_id
            )
            return False

        if not candidate.phone:
            logger.info(
                "Auto-trigger skipped: candidate %s has no phone number",
                candidate_id,
            )
            return False

        jd_id = screening.role_template_id
        if jd_id is None:
            logger.info(
                "Auto-trigger skipped: screening result %s has no JD",
                screening_result_id,
            )
            return False

        orchestrator = RecruiterOrchestrator(self.db)
        try:
            session_id = await orchestrator.initiate_interview(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                jd_id=jd_id,
                screening_result_id=screening_result_id,
                trigger_type="auto_pipeline",
                config={},
            )
        except Exception as exc:
            logger.warning("Auto-trigger failed to initiate interview: %s", exc)
            return False

        logger.info(
            "Auto-triggered recruiter interview %s for candidate %s",
            session_id,
            candidate_id,
        )
        return bool(session_id)

    async def evaluate_trigger_from_screening(
        self,
        tenant_id: int,
        screening_result_id: int,
        new_status: str,
    ) -> bool:
        """Convenience overload that loads the candidate from the screening result."""
        screening = self.db.execute(
            select(ScreeningResult).where(
                ScreeningResult.id == screening_result_id,
                ScreeningResult.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if screening is None or screening.candidate_id is None:
            return False

        return await self.evaluate_trigger(
            tenant_id=tenant_id,
            candidate_id=screening.candidate_id,
            screening_result_id=screening_result_id,
            new_status=new_status,
        )
