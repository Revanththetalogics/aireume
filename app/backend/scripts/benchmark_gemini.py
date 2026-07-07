"""Benchmark Gemini API latency for resume analysis LLM steps."""
from __future__ import annotations

import asyncio
import os
import sys
import time

# Allow running from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.backend.services.llm_service import gemini_generate_content, get_gemini_model


NARRATIVE_SYSTEM = (
    "You are an expert technical recruiter. Return valid JSON only, no markdown."
)

NARRATIVE_USER = """Analyze this screening match and return JSON with keys:
summary, strengths, gaps, recommendation_rationale, red_flags (array).

Role: Senior Python Backend Engineer
Candidate: Jane Doe, 8 years, current role Staff Engineer at Acme
Scores: overall=78, skills=82, experience=75, education=70
Must-have skills matched: Python, FastAPI, PostgreSQL, Docker
Missing: Kubernetes production experience
"""

STRUCTURED_USER = """Extract from this resume snippet as JSON with keys skills, certifications:
Jane Doe — Staff Engineer. Python, FastAPI, AWS, PostgreSQL, Redis, CI/CD.
Certifications: AWS Solutions Architect.
"""

INTERVIEW_KIT_USER = """Return JSON with interview_questions object containing:
technical_questions, behavioral_questions (each array of {text, what_to_listen_for, follow_ups}).
Role: Senior Python Backend Engineer. Candidate scored 78/100, gap on Kubernetes.
"""


async def timed(label: str, coro):
    start = time.perf_counter()
    try:
        text = await coro
        elapsed = time.perf_counter() - start
        return label, elapsed, len(text), text[:120].replace("\n", " ")
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return label, elapsed, 0, f"ERROR: {exc}"


async def main() -> None:
    if not os.getenv("GEMINI_API_KEY", "").strip():
        print("Set GEMINI_API_KEY before running.")
        sys.exit(1)

    model = get_gemini_model()
    print(f"Model: {model}")
    print("-" * 60)

    tasks = [
        timed(
            "1. Structured extraction (~1.5k out)",
            gemini_generate_content(
                STRUCTURED_USER,
                system="Return JSON only.",
                max_output_tokens=1500,
                temperature=0.1,
            ),
        ),
        timed(
            "2. Narrative JSON (~2k out)",
            gemini_generate_content(
                NARRATIVE_USER,
                system=NARRATIVE_SYSTEM,
                max_output_tokens=2000,
                temperature=0.1,
            ),
        ),
        timed(
            "3. Interview kit JSON (~2.5k out)",
            gemini_generate_content(
                INTERVIEW_KIT_USER,
                system="Return JSON only.",
                max_output_tokens=2500,
                temperature=0.1,
            ),
        ),
    ]

    results = await asyncio.gather(*tasks)
    total = 0.0
    for label, elapsed, chars, preview in results:
        total += elapsed
        print(f"{label}")
        print(f"   {elapsed:.2f}s | {chars} chars | {preview}...")
        print()

    print("-" * 60)
    print(f"Sequential total (3 steps): {total:.2f}s")
    print("Note: narrative is on critical path; kit + voice strategy run in background.")


if __name__ == "__main__":
    asyncio.run(main())
