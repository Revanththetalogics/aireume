"""Anti-template lint for interview kit spoken lines."""

from __future__ import annotations

from typing import Any

FORBIDDEN_STEMS = (
    "this role needs",
    "the role calls for",
    "describe a production scenario",
)
MAX_SPOKEN_LEN = 200
MIN_SPOKEN_WORDS = 8


def get_spoken_line(step: dict[str, Any]) -> str:
    """Return the line to speak or display for a kit step."""
    return (step.get("spoken_text") or step.get("text") or "").strip()


def _iter_steps(kit: dict[str, Any]):
    for thread in kit.get("threads") or []:
        if not isinstance(thread, dict):
            continue
        for step in thread.get("steps") or []:
            if isinstance(step, dict):
                yield step
    for key in (
        "technical_questions",
        "behavioral_questions",
        "experience_deep_dive_questions",
        "culture_fit_questions",
    ):
        for step in kit.get(key) or []:
            if isinstance(step, dict):
                yield step


def lint_interview_kit(kit: dict[str, Any]) -> dict[str, Any]:
    """Return lint result: ok, issues, score (0-100)."""
    issues: list[dict[str, str]] = []
    stems_seen: dict[str, int] = {}

    for step in _iter_steps(kit):
        text = get_spoken_line(step)
        lower = text.lower()
        if not text:
            issues.append({"severity": "error", "message": "Empty question text"})
            continue
        if len(text) > MAX_SPOKEN_LEN:
            issues.append({
                "severity": "error",
                "message": f"Question too long ({len(text)} chars)",
            })
        word_count = len(text.split())
        if word_count < MIN_SPOKEN_WORDS:
            issues.append({"severity": "warn", "message": "Question very short"})
        for stem in FORBIDDEN_STEMS:
            if stem in lower:
                issues.append({"severity": "error", "message": f"Forbidden stem: {stem}"})
        first_three = " ".join(lower.split()[:3])
        stems_seen[first_three] = stems_seen.get(first_three, 0) + 1

    for stem, count in stems_seen.items():
        if count > 1 and stem.startswith("walk me"):
            issues.append({
                "severity": "error",
                "message": f"Repeated stem '{stem}' ({count}x)",
            })

    errors = [i for i in issues if i["severity"] == "error"]
    score = max(0, 100 - len(errors) * 20 - len(issues) * 5)
    return {"ok": len(errors) == 0, "issues": issues, "score": score}
