"""Recommendation agent — synthesizes evaluations into hiring recommendation."""

import logging
from typing import Any

logger = logging.getLogger("aria.recruiter")


class RecommendationAgent:
    """Synthesizes all evaluations into final hiring recommendation."""

    async def recommend(
        self,
        scorecard: dict[str, Any],
        adjusted_fitment: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Produces final recommendation with overall score, confidence, summary,
        strengths, concerns, and items needing human validation.
        """
        technical = scorecard.get("technical", {}) or {}
        behavioral = scorecard.get("behavioral", {}) or {}
        communication = scorecard.get("communication", {}) or {}
        cultural = scorecard.get("cultural_fit", {}) or {}
        motivation = scorecard.get("motivation", {}) or {}
        integrity = scorecard.get("integrity", {}) or {}
        confidence = scorecard.get("confidence", {}) or {}

        tech_score = technical.get("score", 50) or 50
        beh_score = behavioral.get("score", 50) or 50
        comm_score = communication.get("score", 50) or 50
        cult_score = cultural.get("score", 50) or 50
        mot_score = motivation.get("score", 50) or 50
        int_score = integrity.get("score", 50) or 50
        conf_score = confidence.get("score", 50) or 50

        # Weighted blend of 7 dimensions
        overall_score = int(
            (tech_score * 0.25)
            + (beh_score * 0.15)
            + (comm_score * 0.15)
            + (cult_score * 0.10)
            + (mot_score * 0.15)
            + (int_score * 0.10)
            + (conf_score * 0.10)
        )

        adjusted = adjusted_fitment.get("adjusted_score", overall_score) or overall_score
        # Blend adjusted fitment with interview performance
        final_score = int((overall_score + adjusted) / 2)

        recommendation = self._bucket_recommendation(final_score)
        confidence = self._derive_confidence(
            tech_score, beh_score, comm_score, cult_score, adjusted_fitment
        )

        key_strengths = self._collect_strengths(scorecard)
        key_concerns = self._collect_concerns(scorecard, adjusted_fitment)
        human_validation_needed = self._human_validation_items(scorecard, adjusted_fitment)

        candidate_name = context.get("candidate", {}).get("name", "The candidate")
        role_title = context.get("role", {}).get("title", "the role")

        executive_summary = (
            f"{candidate_name} interviewed for {role_title} with an overall score of "
            f"{final_score}/100 ({recommendation.replace('_', ' ')}). "
            f"Technical: {tech_score}, Behavioral: {beh_score}, Communication: {comm_score}, "
            f"Cultural fit: {cult_score}, Motivation: {mot_score}, Integrity: {int_score}, "
            f"Confidence: {conf_score}."
        )

        recommendation_reasoning = self._build_reasoning(
            final_score,
            tech_score,
            beh_score,
            comm_score,
            cult_score,
            adjusted_fitment,
            key_concerns,
        )

        logger.info(
            "Recommendation produced: %s score=%d confidence=%s",
            recommendation,
            final_score,
            confidence,
        )

        return {
            "recommendation": recommendation,
            "overall_score": final_score,
            "confidence_level": confidence,
            "executive_summary": executive_summary,
            "recommendation_reasoning": recommendation_reasoning,
            "key_strengths": key_strengths,
            "key_concerns": key_concerns,
            "human_validation_needed": human_validation_needed,
        }

    def _bucket_recommendation(self, score: int) -> str:
        if score >= 85:
            return "strong_hire"
        if score >= 70:
            return "hire"
        if score >= 50:
            return "maybe"
        if score >= 35:
            return "no_hire"
        return "strong_no_hire"

    def _derive_confidence(
        self,
        technical: int,
        behavioral: int,
        communication: int,
        cultural: int,
        adjusted_fitment: dict[str, Any],
    ) -> str:
        scores = [technical, behavioral, communication, cultural]
        spread = max(scores) - min(scores)

        fit_confidence = adjusted_fitment.get("confidence", "medium")
        if spread > 30:
            return "low"
        if fit_confidence == "high" and all(s >= 60 for s in scores):
            return "high"
        if fit_confidence == "low":
            return "low"
        return "medium"

    def _collect_strengths(self, scorecard: dict[str, Any]) -> list[str]:
        strengths: list[str] = []
        for dim in ("technical", "behavioral", "communication", "cultural_fit"):
            data = scorecard.get(dim, {}) or {}
            dim_strengths = data.get("strengths", []) if isinstance(data.get("strengths"), list) else []
            for s in dim_strengths[:2]:
                strengths.append(f"{dim}: {s}")
        return strengths[:5]

    def _collect_concerns(
        self,
        scorecard: dict[str, Any],
        adjusted_fitment: dict[str, Any],
    ) -> list[str]:
        concerns: list[str] = []
        for dim in ("technical", "behavioral", "communication", "cultural_fit"):
            data = scorecard.get(dim, {}) or {}
            gaps = data.get("gaps", []) if isinstance(data.get("gaps"), list) else []
            for g in gaps[:2]:
                concerns.append(f"{dim}: {g}")

        validated = adjusted_fitment.get("risks_validated", []) or []
        for risk in validated[:3]:
            concerns.append(f"Validated risk: {risk}")

        return concerns[:5]

    def _human_validation_items(
        self,
        scorecard: dict[str, Any],
        adjusted_fitment: dict[str, Any],
    ) -> list[str]:
        items: list[str] = []

        technical = scorecard.get("technical", {}) or {}
        if (technical.get("score", 50) or 50) < 50:
            items.append("Technical depth — verify hands-on skill with a live exercise.")

        communication = scorecard.get("communication", {}) or {}
        if (communication.get("score", 50) or 50) < 50:
            items.append("Communication clarity — assess in a follow-up conversation.")

        cultural = scorecard.get("cultural_fit", {}) or {}
        if (cultural.get("score", 50) or 50) < 50:
            items.append("Cultural fit — involve hiring manager for team-alignment check.")

        if adjusted_fitment.get("confidence") == "low":
            items.append("Low confidence adjustment — human reviewer should confirm fitment change.")

        return items

    def _build_reasoning(
        self,
        final_score: int,
        technical: int,
        behavioral: int,
        communication: int,
        cultural: int,
        adjusted_fitment: dict[str, Any],
        key_concerns: list[str],
    ) -> str:
        recommendation = self._bucket_recommendation(final_score)
        reason = (
            f"Overall score of {final_score} maps to '{recommendation.replace('_', ' ')}'. "
            f"Technical ({technical}), behavioral ({behavioral}), communication ({communication}), "
            f"and cultural fit ({cultural}) contributed to the score. "
            f"Adjusted fitment: {adjusted_fitment.get('original_score')} -> "
            f"{adjusted_fitment.get('adjusted_score')} "
            f"({adjusted_fitment.get('confidence')} confidence)."
        )
        if key_concerns:
            reason += f" Key concerns: {'; '.join(key_concerns)}."
        return reason
