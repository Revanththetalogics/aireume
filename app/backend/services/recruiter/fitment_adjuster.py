"""Fitment adjuster — updates fitment score based on interview evidence."""

import logging
from typing import Any

logger = logging.getLogger("aria.recruiter")


class FitmentAdjuster:
    """Adjusts existing fitment score based on interview evidence."""

    MAX_ADJUSTMENT = 25
    HIGH_CONFIDENCE_THRESHOLD = 80

    async def adjust(
        self,
        original_fitment: dict[str, Any],
        scorecard: dict[str, Any],
        interview_evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compares original fitment assumptions against interview evidence.
        Never adjusts more than ±25 points without high confidence.
        """
        original_score = int(original_fitment.get("score", 50) or 50)

        technical = scorecard.get("technical", {}) or {}
        behavioral = scorecard.get("behavioral", {}) or {}
        communication = scorecard.get("communication", {}) or {}
        cultural = scorecard.get("cultural_fit", {}) or {}

        technical_score = technical.get("score", 50) or 50
        behavioral_score = behavioral.get("score", 50) or 50
        communication_score = communication.get("score", 50) or 50
        cultural_score = cultural.get("score", 50) or 50

        avg_interview = (
            technical_score + behavioral_score + communication_score + cultural_score
        ) / 4

        delta = self._compute_delta(original_score, avg_interview, scorecard)

        # Clamp adjustment
        if abs(delta) > self.MAX_ADJUSTMENT:
            confidence = "low" if abs(delta) > self.MAX_ADJUSTMENT else "medium"
            delta = max(-self.MAX_ADJUSTMENT, min(self.MAX_ADJUSTMENT, delta))
        else:
            confidence = self._derive_confidence(
                technical_score,
                behavioral_score,
                communication_score,
                cultural_score,
            )

        adjusted_score = min(100, max(0, original_score + delta))

        risks_validated, risks_dismissed = self._assess_risks(
            original_fitment.get("risk_signals", []),
            interview_evidence,
        )

        gaps_explained = self._assess_gaps(interview_evidence)

        reasoning = self._build_reasoning(
            original_score,
            adjusted_score,
            avg_interview,
            technical_score,
            behavioral_score,
            communication_score,
            cultural_score,
            risks_validated,
            risks_dismissed,
        )

        logger.info(
            "Fitment adjusted: original=%d adjusted=%d delta=%d confidence=%s",
            original_score,
            adjusted_score,
            delta,
            confidence,
        )

        return {
            "original_score": original_score,
            "adjusted_score": adjusted_score,
            "delta": adjusted_score - original_score,
            "confidence": confidence,
            "reasoning": reasoning,
            "risks_validated": risks_validated,
            "risks_dismissed": risks_dismissed,
            "gaps_explained": gaps_explained,
        }

    def _compute_delta(
        self,
        original_score: int,
        avg_interview: float,
        scorecard: dict[str, Any],
    ) -> int:
        """Compute raw adjustment based on interview vs. original fitment."""
        delta = 0

        # Base adjustment: move halfway toward interview average
        delta += int((avg_interview - original_score) / 2)

        # Boost for strong technical performance
        technical = scorecard.get("technical", {}) or {}
        tech_score = technical.get("score", 50) or 50
        if tech_score >= 80 and original_score < 80:
            delta += 10
        elif tech_score <= 40 and original_score > 50:
            delta -= 10

        # Communication penalty/bonus
        communication = scorecard.get("communication", {}) or {}
        comm_score = communication.get("score", 50) or 50
        if comm_score >= 80:
            delta += 5
        elif comm_score <= 40:
            delta -= 5

        return delta

    def _derive_confidence(
        self,
        technical: int,
        behavioral: int,
        communication: int,
        cultural: int,
    ) -> str:
        scores = [technical, behavioral, communication, cultural]
        if all(s >= self.HIGH_CONFIDENCE_THRESHOLD or s <= 30 for s in scores):
            return "high"
        if any(s is None for s in scores):
            return "low"
        return "medium"

    def _assess_risks(
        self,
        risk_signals: list[Any],
        interview_evidence: list[dict[str, Any]],
    ) -> tuple[list[str], list[str]]:
        validated: list[str] = []
        dismissed: list[str] = []

        evidence_text = " ".join(
            str(e.get("text", e.get("response", ""))).lower()
            for e in interview_evidence
            if isinstance(e, dict)
        )

        for risk in risk_signals:
            if isinstance(risk, dict):
                risk_type = risk.get("type", "unknown")
                description = risk.get("description", risk_type)
            else:
                risk_type = str(risk)
                description = str(risk)

            # Heuristic dismissal signals
            dismissal_phrases = {
                "job_hopping": ["layoff", "restructure", "contract ended", "company shut", "acquired", "better opportunity", "relocated"],
                "overqualification": ["looking for hands-on", "excited by the challenge", "want to stay technical", "enjoy execution"],
                "short_tenures": ["contract", "consulting", "project-based", "freelance"],
            }

            phrases = dismissal_phrases.get(risk_type, [])
            if any(p in evidence_text for p in phrases):
                dismissed.append(description)
            else:
                validated.append(description)

        return validated, dismissed

    def _assess_gaps(self, interview_evidence: list[dict[str, Any]]) -> list[str]:
        explained: list[str] = []
        for e in interview_evidence:
            if not isinstance(e, dict):
                continue
            category = e.get("category", "")
            if category in ("gap_probe", "skill_validation") and e.get("response"):
                explained.append(
                    f"{category}: {e.get('question', '')} -> {e.get('response', '')[:120]}"
                )
        return explained

    def _build_reasoning(
        self,
        original_score: int,
        adjusted_score: int,
        avg_interview: float,
        technical: int,
        behavioral: int,
        communication: int,
        cultural: int,
        risks_validated: list[str],
        risks_dismissed: list[str],
    ) -> str:
        direction = "increased" if adjusted_score > original_score else "decreased" if adjusted_score < original_score else "unchanged"
        parts = [
            f"Fitment score {direction} from {original_score} to {adjusted_score}.",
            f"Interview average was {avg_interview:.1f}.",
            f"Dimension scores: technical={technical}, behavioral={behavioral}, communication={communication}, cultural={cultural}.",
        ]
        if risks_dismissed:
            parts.append(f"Risks dismissed: {', '.join(risks_dismissed)}.")
        if risks_validated:
            parts.append(f"Risks validated: {', '.join(risks_validated)}.")
        return " ".join(parts)
