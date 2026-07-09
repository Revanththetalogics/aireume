"""Interview strategy agent — LLM-powered interview plan generation."""

import logging
from typing import Any

from app.backend.services.recruiter.llm_client import generate_recruiter_json, parse_json_safely

logger = logging.getLogger("aria.recruiter")


class InterviewStrategyAgent:
    """LLM-powered interview strategy generation."""

    async def generate_strategy(
        self,
        context: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Calls LLM to generate an interview plan.
        Falls back to a deterministic strategy if LLM is unavailable.
        """
        prompt = self._build_strategy_prompt(context, config)

        try:
            parsed = await generate_recruiter_json(
                prompt,
                max_output_tokens=2048,
                temperature=0.4,
                timeout=180.0,
            )
            if parsed:
                strategy = self._normalize_strategy(parsed, context, config)
                logger.info("Interview strategy generated via LLM")
                return strategy

        except Exception as e:
            logger.warning("LLM strategy generation failed: %s", e)

        logger.info("Using deterministic fallback strategy")
        return self._build_fallback_strategy(context, config)

    def _build_strategy_prompt(
        self,
        context: dict[str, Any],
        config: dict[str, Any],
    ) -> str:
        """Builds the LLM prompt for strategy generation."""
        candidate = context.get("candidate", {})
        role = context.get("role", {})
        screening = context.get("screening_result", {}) or {}
        probes = context.get("probe_areas", [])

        duration_target = config.get("duration_minutes", 20)
        question_count = config.get("question_count", 12)

        probe_text = "\n".join(
            f"- [{p.get('priority', 'low').upper()}] {p.get('category', '')}: {p.get('reasoning', '')}"
            for p in probes[:10]
        )

        return f"""You are a senior technical interviewer designing a structured interview.

ROLE: {role.get('title', 'the position')}

CANDIDATE PROFILE:
- Name: {candidate.get('name', 'Candidate')}
- Current role: {candidate.get('current_role', 'N/A')}
- Current company: {candidate.get('current_company', 'N/A')}
- Total experience: {candidate.get('total_years_exp', 'N/A')} years
- Skills: {', '.join(str(s) for s in candidate.get('parsed_skills', [])[:15])}

SCREENING CONTEXT:
- Fit score: {screening.get('fit_score', 'N/A')}
- Core skill score: {screening.get('core_skill_score', 'N/A')}
- Eligibility: {screening.get('eligibility', 'N/A')}

PROBE AREAS:
{probe_text}

DESIGN REQUIREMENTS:
- Total interview duration target: {duration_target} minutes
- Generate {question_count} questions
- Sequence questions logically (rapport → technical depth → behavioral → motivation)
- Allocate time per dimension
- Include branching rules for follow-ups
- Calibrate difficulty to candidate seniority

Return ONLY a JSON object with this structure:
{{
  "duration_minutes": {duration_target},
  "questions": [
    {{
      "sequence_number": 1,
      "category": "technical|behavioral|communication|cultural_fit|risk_validation|gap_probe|motivation",
      "question_text": "...",
      "question_context": "why this question matters",
      "estimated_minutes": 2,
      "target_skills": ["skill1"],
      "branching_rules": ["if candidate says X, ask Y"]
    }}
  ],
  "time_plan": {{
    "opening_rapport": 2,
    "technical": 8,
    "behavioral": 5,
    "motivation_culture": 3,
    "closing": 2
  }},
  "branching_rules": [
    "If a candidate's answer is vague, ask for a specific example.",
    "If a candidate claims expertise in a required skill, drill down with a scenario."
  ]
}}

JSON:"""

    def _build_fallback_strategy(
        self,
        context: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Deterministic strategy when LLM is unavailable."""
        candidate = context.get("candidate", {})
        role = context.get("role", {})
        probes = context.get("probe_areas", [])

        duration = config.get("duration_minutes", 20)
        base_questions = config.get("question_count", 12)

        required_skills = role.get("required_skills", [])[:5]
        gaps = [p for p in probes if p.get("category") == "skill_validation"]
        risks = [p for p in probes if p.get("category") == "risk_validation"]
        emp_gaps = [p for p in probes if p.get("category") == "employment_gap"]

        questions: list[dict[str, Any]] = []
        seq = 1

        # Opening rapport
        questions.append({
            "sequence_number": seq,
            "category": "communication",
            "question_text": f"Hi {candidate.get('name', 'there')}, thanks for taking the time. Could you briefly walk me through your background and what interests you about this role?",
            "question_context": "Establish rapport and assess communication clarity.",
            "estimated_minutes": 2,
            "target_skills": [],
            "branching_rules": ["If response is very brief, prompt for one career highlight."],
        })
        seq += 1

        # Technical depth
        for skill in required_skills[:4]:
            questions.append({
                "sequence_number": seq,
                "category": "technical",
                "question_text": f"Can you describe a recent project where you used {skill}? What was your specific contribution and the outcome?",
                "question_context": f"Validate depth of experience in {skill}.",
                "estimated_minutes": max(2, duration // base_questions),
                "target_skills": [skill],
                "branching_rules": [
                    "If the candidate gives a high-level answer, ask for architecture or tooling details.",
                    "If the candidate has not used it recently, ask about last hands-on exposure.",
                ],
            })
            seq += 1

        # Gap probes
        for gap in emp_gaps[:2]:
            questions.append({
                "sequence_number": seq,
                "category": "gap_probe",
                "question_text": "I noticed a gap in your employment history. Could you share what you were working on during that time?",
                "question_context": gap.get("reasoning", "Validate employment gap."),
                "estimated_minutes": 2,
                "target_skills": [],
                "branching_rules": ["If the candidate seems defensive, reassure them this is a standard question."],
            })
            seq += 1

        # Behavioral
        questions.append({
            "sequence_number": seq,
            "category": "behavioral",
            "question_text": "Tell me about a time you faced a significant challenge on a project. What was the situation, what did you do, and what was the result?",
            "question_context": "Assess problem-solving and resilience via STAR format.",
            "estimated_minutes": 3,
            "target_skills": ["problem_solving"],
            "branching_rules": ["If STAR is incomplete, prompt for the result or lessons learned."],
        })
        seq += 1

        questions.append({
            "sequence_number": seq,
            "category": "behavioral",
            "question_text": "Describe a situation where you had a disagreement with a teammate. How did you handle it?",
            "question_context": "Assess collaboration and conflict resolution.",
            "estimated_minutes": 3,
            "target_skills": ["teamwork", "communication"],
            "branching_rules": ["If the candidate blames others, probe accountability."],
        })
        seq += 1

        # Risk validation
        for risk in risks[:2]:
            questions.append({
                "sequence_number": seq,
                "category": "risk_validation",
                "question_text": "Your resume shows several short tenures. Can you help me understand the reasons behind those transitions?",
                "question_context": risk.get("reasoning", "Validate risk signal."),
                "estimated_minutes": 2,
                "target_skills": [],
                "branching_rules": ["If reasons seem unclear, ask what the candidate seeks in a long-term role."],
            })
            seq += 1

        # Motivation / culture fit
        questions.append({
            "sequence_number": seq,
            "category": "motivation",
            "question_text": f"What are you looking for in your next role, and why does {role.get('title', 'this position')} appeal to you?",
            "question_context": "Assess motivation and role alignment.",
            "estimated_minutes": 2,
            "target_skills": [],
            "branching_rules": ["If the answer is generic, ask what specific work they want to do."],
        })
        seq += 1

        questions.append({
            "sequence_number": seq,
            "category": "cultural_fit",
            "question_text": "What type of work environment brings out your best performance?",
            "question_context": "Assess cultural fit and preferences.",
            "estimated_minutes": 2,
            "target_skills": [],
            "branching_rules": ["If the answer conflicts with known team norms, flag for human review."],
        })
        seq += 1

        # Closing
        questions.append({
            "sequence_number": seq,
            "category": "communication",
            "question_text": "Do you have any questions for me about the role or team?",
            "question_context": "Assess engagement and preparation.",
            "estimated_minutes": 2,
            "target_skills": [],
            "branching_rules": ["If no questions, note lack of preparation or strong confidence."],
        })

        return {
            "duration_minutes": duration,
            "questions": questions,
            "time_plan": {
                "opening_rapport": 2,
                "technical": 8,
                "behavioral": 6,
                "risk_validation": 3,
                "motivation_culture": 4,
                "closing": 2,
            },
            "branching_rules": [
                "If a candidate's answer is vague, ask for a specific example.",
                "If a candidate claims expertise in a required skill, drill down with a scenario.",
                "If a candidate seems uncertain, rephrase once before moving on.",
            ],
        }

    def _parse_json_response(self, response: str) -> dict[str, Any] | None:
        return parse_json_safely(response)

    def _normalize_strategy(
        self,
        parsed: dict[str, Any],
        context: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and normalize an LLM-generated strategy."""
        questions = parsed.get("questions", [])
        normalized_questions: list[dict[str, Any]] = []

        valid_categories = {
            "technical", "behavioral", "communication", "cultural_fit",
            "risk_validation", "gap_probe", "motivation",
        }

        for idx, q in enumerate(questions, start=1):
            if not isinstance(q, dict):
                continue
            category = q.get("category", "technical")
            if category not in valid_categories:
                category = "technical"
            normalized_questions.append({
                "sequence_number": q.get("sequence_number", idx),
                "category": category,
                "question_text": q.get("question_text", "").strip(),
                "question_context": q.get("question_context", "").strip(),
                "estimated_minutes": max(1, min(15, int(q.get("estimated_minutes", 2)))),
                "target_skills": q.get("target_skills", []) if isinstance(q.get("target_skills"), list) else [],
                "branching_rules": q.get("branching_rules", []) if isinstance(q.get("branching_rules"), list) else [],
            })

        if not normalized_questions:
            return self._build_fallback_strategy(context, config)

        return {
            "duration_minutes": parsed.get("duration_minutes", config.get("duration_minutes", 20)),
            "questions": normalized_questions,
            "time_plan": parsed.get("time_plan", {}),
            "branching_rules": parsed.get("branching_rules", []),
        }
