"""Recruiter orchestrator — main service for AI Recruiter interviews."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    Candidate,
    RecruiterInterviewQuestion,
    RecruiterInterviewSession,
    RecruiterScorecard,
    ScreeningResult,
    VoiceScreeningSession,
    VoiceTranscriptEntry,
)
from app.backend.services.recruiter.context_engine import InterviewContextEngine
from app.backend.services.recruiter.strategy_agent import InterviewStrategyAgent
from app.backend.services.recruiter.evaluation_agents import (
    TechnicalEvaluator,
    BehavioralEvaluator,
    CommunicationEvaluator,
    CulturalFitEvaluator,
)
from app.backend.services.recruiter.fitment_adjuster import FitmentAdjuster
from app.backend.services.recruiter.recommendation_agent import RecommendationAgent
from app.backend.services.recruiter.copilot_agent import CopilotAgent

logger = logging.getLogger("aria.recruiter")


class RecruiterOrchestrator:
    """Main orchestration service for AI Recruiter interviews."""

    def __init__(self, db: Session):
        self.db = db
        self.context_engine = InterviewContextEngine()
        self.strategy_agent = InterviewStrategyAgent()

    async def initiate_interview(
        self,
        tenant_id: int,
        candidate_id: int,
        jd_id: int,
        screening_result_id: int | None,
        trigger_type: str,
        config: dict[str, Any] | None = None,
        created_by: int | None = None,
    ) -> str:
        """
        Creates a new recruiter interview session, generates a strategy,
        and schedules the voice call via existing voice infrastructure.
        """
        logger.info(
            "Initiating AI recruiter interview: tenant=%s candidate=%s jd=%s",
            tenant_id,
            candidate_id,
            jd_id,
        )

        if config is None:
            config = {}

        # Multi-tenancy: ensure candidate and JD belong to the tenant
        candidate = self.db.execute(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found for tenant {tenant_id}")

        if not candidate.phone:
            raise ValueError(f"Candidate {candidate_id} has no phone number")

        # Build context and generate strategy
        context = self.context_engine.build_context(
            self.db,
            candidate_id=candidate_id,
            screening_result_id=screening_result_id,
            jd_id=jd_id,
        )

        strategy_config = {
            "duration_minutes": config.get("duration_minutes", 20),
            "question_count": config.get("question_count", 12),
        }
        strategy = await self.strategy_agent.generate_strategy(context, strategy_config)

        # Normalize scheduled_at to datetime if provided as ISO string
        scheduled_at = self._parse_scheduled_at(config.get("scheduled_at"))

        # Create the voice screening session using existing infrastructure
        voice_session = VoiceScreeningSession(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            jd_id=jd_id,
            phone_number=candidate.phone,
            direction="outbound",
            status="scheduled",
            scheduled_at=scheduled_at,
        )
        self.db.add(voice_session)
        self.db.commit()
        self.db.refresh(voice_session)

        # Schedule the call
        from app.backend.services.voice_call_scheduler import schedule_voice_call

        schedule_voice_call(voice_session.id, scheduled_at)

        # Create the recruiter interview session
        interview_session = RecruiterInterviewSession(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            jd_id=jd_id,
            screening_result_id=screening_result_id,
            voice_session_id=voice_session.id,
            trigger_type=trigger_type,
            status="pending_strategy",
            interview_strategy_json=json.dumps(strategy, default=str),
            interview_config_json=json.dumps(config, default=str),
            created_by=created_by,
        )
        self.db.add(interview_session)

        # Persist generated questions
        for q in strategy.get("questions", []):
            self.db.add(
                RecruiterInterviewQuestion(
                    id=str(uuid.uuid4()),
                    session_id=interview_session.id,
                    sequence_number=q.get("sequence_number", 0),
                    category=q.get("category", "technical"),
                    question_text=q.get("question_text", ""),
                    question_context=q.get("question_context", ""),
                    is_follow_up=False,
                )
            )

        interview_session.status = "scheduled"
        self.db.commit()
        self.db.refresh(interview_session)

        logger.info(
            "Recruiter interview session created: %s (voice_session=%s)",
            interview_session.id,
            voice_session.id,
        )
        return interview_session.id

    async def on_interview_completed(self, session_id: str) -> None:
        """
        Post-interview processing pipeline:
        transcript -> evaluation agents -> fitment adjustment -> recommendation -> scorecard.
        """
        logger.info("Processing completed recruiter interview: %s", session_id)

        interview_session = self._get_session(session_id)
        if interview_session is None:
            logger.error("Recruiter interview session %s not found", session_id)
            return

        # Ensure tenant-scoped access
        tenant_id = interview_session.tenant_id

        # Load transcript from voice session
        transcript: list[dict[str, Any]] = []
        voice_session = interview_session.voice_session
        if voice_session:
            entries = self.db.execute(
                select(VoiceTranscriptEntry)
                .where(VoiceTranscriptEntry.session_id == voice_session.id)
                .order_by(VoiceTranscriptEntry.timestamp.asc())
            ).scalars().all()
            transcript = [
                {"speaker": e.speaker, "text": e.text, "timestamp": e.timestamp.isoformat() if e.timestamp else None}
                for e in entries
            ]

        # ── Build question-response pairs ─────────────────────────────────────
        # Prefer responses stored by the internal callback endpoint (which
        # captures actual candidate answers). Fall back to deriving from
        # strategy + transcript when the callback hasn't stored responses.
        stored_questions = self.db.execute(
            select(RecruiterInterviewQuestion)
            .where(RecruiterInterviewQuestion.session_id == session_id)
            .order_by(RecruiterInterviewQuestion.sequence_number.asc())
        ).scalars().all()

        if any(q.candidate_response for q in stored_questions):
            # Use stored responses from the callback
            questions_responses = [
                {
                    "sequence_number": q.sequence_number,
                    "category": q.category,
                    "question": q.question_text,
                    "question_context": q.question_context or "",
                    "response": q.candidate_response or "",
                    "response_duration": q.response_duration_seconds,
                    "is_follow_up": q.is_follow_up,
                }
                for q in stored_questions
            ]
        else:
            # Fall back to deriving from strategy + transcript
            strategy = self._load_json(interview_session.interview_strategy_json, {})
            questions_responses = self._pair_questions_responses(
                strategy.get("questions", []), transcript
            )

        # Rebuild context
        context = self.context_engine.build_context(
            self.db,
            candidate_id=interview_session.candidate_id,
            screening_result_id=interview_session.screening_result_id,
            jd_id=interview_session.jd_id,
        )

        # Run evaluators
        technical_eval = TechnicalEvaluator()
        behavioral_eval = BehavioralEvaluator()
        communication_eval = CommunicationEvaluator()
        cultural_eval = CulturalFitEvaluator()

        jd_context = {
            "required_skills": context.get("role", {}).get("required_skills", []),
            "title": context.get("role", {}).get("title", ""),
        }
        company_context = {
            "title": context.get("role", {}).get("title", ""),
            "jd_text": context.get("role", {}).get("jd_text", ""),
        }

        technical = await technical_eval.evaluate(questions_responses, jd_context)
        behavioral = await behavioral_eval.evaluate(questions_responses, company_context)
        communication = await communication_eval.evaluate(transcript, {})
        cultural = await cultural_eval.evaluate(questions_responses, company_context)

        # Extract motivation and integrity scores from per-answer data
        motivation_score = self._extract_dimension_score(questions_responses, "motivation", cultural.get("score", 50))
        integrity_score = self._extract_dimension_score(questions_responses, "integrity", behavioral.get("score", 50))

        # Confidence score from communication metrics (if available from orchestrator)
        confidence_score = communication.get("score", 50)
        if any(qr.get("confidence_score") for qr in questions_responses):
            scores = [qr["confidence_score"] for qr in questions_responses if qr.get("confidence_score")]
            confidence_score = sum(scores) // len(scores) if scores else 50

        scorecard = {
            "technical": technical,
            "behavioral": behavioral,
            "communication": communication,
            "cultural_fit": cultural,
            "motivation": {"score": motivation_score, "evidence": ["Derived from motivation stage answers."]},
            "integrity": {"score": integrity_score, "evidence": ["Derived from resume verification and behavioral answers."]},
            "confidence": {"score": confidence_score, "evidence": ["Derived from communication metrics."]},
        }

        # Run Copilot agent for per-answer observations
        copilot = CopilotAgent()
        for qr in questions_responses:
            if qr.get("answer") and qr.get("score") is not None:
                try:
                    observation = await copilot.generate_observation(
                        question=qr.get("question", ""),
                        answer=qr.get("answer", ""),
                        stage=qr.get("stage", qr.get("category", "technical")),
                        answer_score=qr.get("score", 50),
                        context=context,
                    )
                    qr["copilot_observation"] = observation
                except Exception as e:
                    logger.warning("Copilot observation failed for Q: %s", e)

        # Fitment adjustment
        screening = context.get("screening_result", {}) or {}
        original_fitment = {
            "score": screening.get("fit_score", 50),
            "risk_signals": screening.get("risk_signals", []),
        }
        fitment_adjuster = FitmentAdjuster()
        adjusted_fitment = await fitment_adjuster.adjust(
            original_fitment, scorecard, questions_responses
        )

        # Final recommendation
        recommender = RecommendationAgent()
        recommendation = await recommender.recommend(scorecard, adjusted_fitment, context)

        # Persist scorecard
        scorecard_record = RecruiterScorecard(
            id=str(uuid.uuid4()),
            session_id=interview_session.id,
            tenant_id=tenant_id,
            candidate_id=interview_session.candidate_id,
            technical_score=technical.get("score"),
            technical_evidence=json.dumps(technical, default=str),
            behavioral_score=behavioral.get("score"),
            behavioral_evidence=json.dumps(behavioral, default=str),
            communication_score=communication.get("score"),
            communication_evidence=json.dumps(communication, default=str),
            cultural_fit_score=cultural.get("score"),
            cultural_fit_evidence=json.dumps(cultural, default=str),
            risk_signals_validated=json.dumps(adjusted_fitment.get("risks_validated", []), default=str),
            gaps_explained=json.dumps(adjusted_fitment.get("gaps_explained", []), default=str),
            original_fit_score=original_fitment.get("score"),
            adjusted_fit_score=adjusted_fitment.get("adjusted_score"),
            adjustment_reasoning=adjusted_fitment.get("reasoning"),
            overall_score=recommendation.get("overall_score"),
            confidence_level=recommendation.get("confidence_level"),
            recommendation=recommendation.get("recommendation"),
            recommendation_reasoning=recommendation.get("recommendation_reasoning"),
            executive_summary=recommendation.get("executive_summary"),
        )
        self.db.add(scorecard_record)

        # Update stored questions with copilot observations and scores
        for qr in questions_responses:
            if qr.get("copilot_observation") or qr.get("score") is not None:
                matching_db_q = next(
                    (q for q in stored_questions if q.question_text == qr.get("question", "")),
                    None,
                )
                if matching_db_q:
                    if qr.get("score") is not None:
                        matching_db_q.answer_score = qr["score"]
                    if qr.get("copilot_observation"):
                        matching_db_q.copilot_observation = json.dumps(qr["copilot_observation"], default=str)

        interview_session.status = "completed"
        interview_session.ended_at = datetime.now(timezone.utc)
        if transcript and voice_session and voice_session.started_at:
            try:
                interview_session.duration_seconds = int(
                    (datetime.now(timezone.utc) - voice_session.started_at).total_seconds()
                )
            except Exception:
                pass

        self.db.commit()

        logger.info(
            "Recruiter interview completed: %s recommendation=%s score=%s",
            session_id,
            recommendation.get("recommendation"),
            recommendation.get("overall_score"),
        )

    def get_session_status(self, session_id: str) -> dict[str, Any]:
        """Returns current session status with progress info."""
        session = self._get_session(session_id)
        if session is None:
            return {"error": "Session not found", "session_id": session_id}

        scorecard = session.scorecard
        return {
            "session_id": session.id,
            "status": session.status,
            "tenant_id": session.tenant_id,
            "candidate_id": session.candidate_id,
            "jd_id": session.jd_id,
            "voice_session_id": session.voice_session_id,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_seconds": session.duration_seconds,
            "scorecard": {
                "overall_score": scorecard.overall_score,
                "recommendation": scorecard.recommendation,
                "confidence_level": scorecard.confidence_level,
            } if scorecard else None,
        }

    async def cancel_interview(self, session_id: str) -> None:
        """Cancels a scheduled or in-progress interview."""
        session = self._get_session(session_id)
        if session is None:
            logger.error("Cannot cancel — session %s not found", session_id)
            return

        if session.status in ("completed", "cancelled"):
            logger.info("Session %s already %s", session_id, session.status)
            return

        session.status = "cancelled"
        session.ended_at = datetime.now(timezone.utc)

        # Cancel associated voice session and scheduler jobs
        if session.voice_session_id:
            from app.backend.services.voice_call_scheduler import cancel_pending_retries

            cancel_pending_retries(session.voice_session_id)
            voice_session = self.db.execute(
                select(VoiceScreeningSession).where(
                    VoiceScreeningSession.id == session.voice_session_id,
                    VoiceScreeningSession.tenant_id == session.tenant_id,
                )
            ).scalar_one_or_none()
            if voice_session and voice_session.status not in ("completed", "failed"):
                voice_session.status = "cancelled"
                voice_session.ended_at = datetime.now(timezone.utc)

        self.db.commit()
        logger.info("Recruiter interview cancelled: %s", session_id)

    async def retry_interview(self, session_id: str) -> str:
        """Retries a failed interview by creating a new session."""
        session = self._get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        logger.info("Retrying recruiter interview: %s", session_id)

        config = self._load_json(session.interview_config_json, {})
        config["retried_from_session_id"] = session_id
        config["scheduled_at"] = config.get("scheduled_at") or datetime.now(timezone.utc).isoformat()

        new_session_id = await self.initiate_interview(
            tenant_id=session.tenant_id,
            candidate_id=session.candidate_id,
            jd_id=session.jd_id,
            screening_result_id=session.screening_result_id,
            trigger_type=f"retry:{session.trigger_type}",
            config=config,
            created_by=session.created_by,
        )

        logger.info("Retry session created: %s -> %s", session_id, new_session_id)
        return new_session_id

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _get_session(self, session_id: str) -> RecruiterInterviewSession | None:
        return self.db.execute(
            select(RecruiterInterviewSession).where(
                RecruiterInterviewSession.id == session_id
            )
        ).scalar_one_or_none()

    def _parse_scheduled_at(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None

    def _load_json(self, raw: str | None, default: Any) -> Any:
        if not raw:
            return default
        try:
            parsed = json.loads(raw)
            return parsed if parsed is not None else default
        except (json.JSONDecodeError, TypeError):
            return default

    def _pair_questions_responses(
        self,
        questions: list[dict[str, Any]],
        transcript: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Best-effort pairing of strategy questions with candidate transcript turns.
        Since the voice agent does not currently tag answers by question, we
        assign successive candidate turns to successive questions.
        """
        candidate_turns = [
            t.get("text", "")
            for t in transcript
            if isinstance(t, dict) and t.get("speaker") != "bot"
        ]

        paired: list[dict[str, Any]] = []
        turn_idx = 0
        for q in questions:
            if not isinstance(q, dict):
                continue
            response = candidate_turns[turn_idx] if turn_idx < len(candidate_turns) else ""
            paired.append({
                "sequence_number": q.get("sequence_number"),
                "category": q.get("category", "technical"),
                "question": q.get("question_text", ""),
                "response": response,
                "question_context": q.get("question_context", ""),
            })
            if response:
                turn_idx += 1
        return paired

    def _extract_dimension_score(
        self,
        questions_responses: list[dict[str, Any]],
        dimension: str,
        fallback: int = 50,
    ) -> int:
        """Extract a dimension score from per-answer data (from the voice agent orchestrator)."""
        matching = [
            qr for qr in questions_responses
            if isinstance(qr, dict) and qr.get("stage") == dimension and qr.get("score") is not None
        ]
        if matching:
            scores = [qr["score"] for qr in matching]
            return sum(scores) // len(scores)
        # Also check category field for backward compat
        matching_cat = [
            qr for qr in questions_responses
            if isinstance(qr, dict) and qr.get("category") == dimension and qr.get("score") is not None
        ]
        if matching_cat:
            scores = [qr["score"] for qr in matching_cat]
            return sum(scores) // len(scores)
        return fallback
