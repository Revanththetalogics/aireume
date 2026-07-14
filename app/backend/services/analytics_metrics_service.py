"""Metric glossary and documentation for analytics transparency."""

from __future__ import annotations

from typing import Any

METRIC_GLOSSARY: list[dict[str, Any]] = [
    {
        "key": "total_analyzed",
        "label": "Total analyzed",
        "definition": "Count of resume screening analyses completed in the selected period.",
        "formula": "COUNT(screening_results) WHERE timestamp in range",
        "caveats": "Excludes analyses still in queue.",
    },
    {
        "key": "avg_fit_score",
        "label": "Average fit score",
        "definition": "Mean deterministic resume fit score (0–100) across analyses in period.",
        "formula": "AVG(deterministic_score)",
        "caveats": "Null scores excluded.",
    },
    {
        "key": "recommendation_shortlist_rate",
        "label": "AI shortlist rate",
        "definition": "Share of analyses where consolidated AI recommendation is Shortlist.",
        "formula": "shortlist_count / total_analyzed × 100",
        "caveats": "Based on recommendation text, not pipeline status.",
    },
    {
        "key": "pipeline_shortlist_rate",
        "label": "Pipeline shortlist rate",
        "definition": "Share of screening results with pipeline status shortlisted.",
        "formula": "pipeline_shortlisted / total_analyzed × 100",
        "caveats": "Distinct from AI recommendation shortlist rate.",
    },
    {
        "key": "pending_hm_review",
        "label": "Pending HM review",
        "definition": "Submissions sent to hiring managers awaiting an outcome.",
        "formula": "COUNT(requisition_candidates) WHERE submission_status=submitted AND hm_outcome IS NULL",
        "caveats": "Scoped to tenant requisitions.",
    },
    {
        "key": "stale_candidates",
        "label": "Stale pipeline candidates",
        "definition": "Candidates stuck in a pipeline stage beyond the stale threshold.",
        "formula": "Candidates with updated_at older than threshold",
        "caveats": "Threshold configured in funnel slice.",
    },
    {
        "key": "zero_pipeline_requisitions",
        "label": "Empty pipeline requisitions",
        "definition": "Open requisitions with no candidates in the pipeline.",
        "formula": "Open reqs with candidate_count = 0",
        "caveats": "Leadership risk flag.",
    },
    {
        "key": "interview_completion_rate",
        "label": "Interview completion rate",
        "definition": "Share of AI interview sessions that reached a completed state.",
        "formula": "completed_sessions / scheduled_sessions × 100",
        "caveats": "Voice screening sessions only.",
    },
    {
        "key": "ats_failure_count",
        "label": "ATS sync failures",
        "definition": "Failed ATS sync operations in the selected period.",
        "formula": "COUNT(ats_sync_logs) WHERE success = false",
        "caveats": "Per connection; see ATS slice for details.",
    },
    {
        "key": "hm_advance_rate",
        "label": "HM advance rate",
        "definition": "Share of HM decisions that advanced the candidate.",
        "formula": "advance_count / (advance + reject) × 100",
        "caveats": "Hold outcomes excluded from denominator.",
    },
]


def get_metric_glossary() -> dict[str, Any]:
    return {
        "metrics": METRIC_GLOSSARY,
        "version": "1.0",
        "updated_at": "2026-07-14",
    }
