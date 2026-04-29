"""
Gap Detector — mechanical date math only.

All intelligence (what gaps mean contextually, narrative interpretation, penalties)
lives in the LLM agents. This module is responsible ONLY for:
  - Date parsing and YYYY-MM normalization
  - Overlap-aware total experience (interval merging, fixes double-count bug)
  - Objective gap severity labels (threshold-based, no penalty values)
  - Structured employment timeline output for the LLM pipeline
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dateutil.relativedelta import relativedelta

try:
    import dateparser as _dateparser
    _HAS_DATEPARSER = True
except ImportError:
    from dateutil import parser as _dateutil_parser  # type: ignore
    _HAS_DATEPARSER = False


# ─── Date utilities ────────────────────────────────────────────────────────────

def _to_ym(date_str: Optional[str]) -> Optional[str]:
    """Normalize any date string to YYYY-MM format."""
    if not date_str:
        return None
    s = str(date_str).strip()
    # Normalize "till date" and other present synonyms
    if re.match(r'^(till\s*date|till\s*now|till\s*present|to\s*date|to\s*present|ongoing|continuing)$', s, re.IGNORECASE):
        return datetime.now().strftime("%Y-%m")
    if s.lower() in ("present", "current", "now"):
        return datetime.now().strftime("%Y-%m")
    # Strip periods from month abbreviations before parsing
    s = re.sub(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)\.', r'\1', s, flags=re.IGNORECASE)
    # Bare 4-digit year
    if re.match(r"^(?:19|20)\d{2}$", s):
        return f"{s}-01"
    # Try dateparser first (better format coverage than dateutil)
    try:
        if _HAS_DATEPARSER:
            dt = _dateparser.parse(s, settings={'PREFER_DAY_OF_MONTH': 'first', 'REQUIRE_PARTS': ['year']})
            if dt:
                return dt.strftime("%Y-%m")
    except Exception:
        pass
    # Fallback to dateutil
    try:
        dt = _dateutil_parser.parse(s, fuzzy=True)
        if dt:
            return dt.strftime("%Y-%m")
    except Exception:
        pass
    # Last resort: bare year extraction
    m = re.search(r"\b((?:19|20)\d{2})\b", s)
    if m:
        return f"{m.group(0)}-01"
    return None


def _ym_to_dt(ym: str) -> datetime:
    """Convert YYYY-MM string to datetime (first of month)."""
    try:
        return datetime.strptime(ym, "%Y-%m")
    except Exception:
        return datetime.now()


def _months_between(start_ym: str, end_ym: str) -> int:
    """Calculate whole months between two YYYY-MM strings. Always >= 0."""
    start = _ym_to_dt(start_ym)
    end   = _ym_to_dt(end_ym)
    rd    = relativedelta(end, start)
    return max(0, rd.years * 12 + rd.months)


def _classify_gap(months: int) -> str:
    """Classify gap severity by objective threshold — no judgment on meaning."""
    if months < 3:
        return "negligible"
    if months < 6:
        return "minor"
    if months < 12:
        return "moderate"
    return "critical"


# ─── Interval merging (fixes double-count in overlapping jobs) ─────────────────

def _merge_intervals(intervals: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Merge overlapping or adjacent YYYY-MM date intervals.
    Prevents double-counting of total experience when jobs overlap.
    """
    if not intervals:
        return []
    sorted_iv = sorted(intervals, key=lambda x: x[0])
    merged = [list(sorted_iv[0])]
    for start, end in sorted_iv[1:]:
        prev = merged[-1]
        if start <= prev[1]:
            prev[1] = max(prev[1], end)
        else:
            merged.append([start, end])
    return [tuple(iv) for iv in merged]


# ─── Main detector ─────────────────────────────────────────────────────────────

class GapDetector:
    def analyze(self, work_experience: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not work_experience:
            return {
                "employment_timeline": [],
                "employment_gaps":     [],
                "overlapping_jobs":    [],
                "short_stints":        [],
                "total_years":         0.0,
            }

        now_ym = datetime.now().strftime("%Y-%m")

        # Normalize all jobs to YYYY-MM dates
        jobs: List[Dict[str, Any]] = []
        for job in work_experience:
            start_ym = _to_ym(job.get("start_date"))
            end_ym   = _to_ym(job.get("end_date", "present")) or now_ym
            if not start_ym:
                continue
            jobs.append({
                "role":             job.get("title", ""),
                "company":          job.get("company", ""),
                "start_ym":         start_ym,
                "end_ym":           end_ym,
                "duration_months":  _months_between(start_ym, end_ym),
            })

        # Roles listed but start_date never parsed — avoid 0y timeline & 0% experience.
        if not jobs:
            estimated = round(min(15.0, max(0.0, len(work_experience) * 1.5)), 1)
            return {
                "employment_timeline": [],
                "employment_gaps":     [],
                "overlapping_jobs":    [],
                "short_stints":        [],
                "total_years":         estimated,
            }

        jobs.sort(key=lambda j: j["start_ym"])

        # Build structured employment timeline with gap metadata
        timeline: List[Dict[str, Any]] = []
        for i, job in enumerate(jobs):
            entry: Dict[str, Any] = {
                "role":              job["role"],
                "company":           job["company"],
                "from":              job["start_ym"],
                "to":                job["end_ym"],
                "duration_months":   job["duration_months"],
                "gap_after_months":  0,
                "gap_severity":      None,
            }
            if i < len(jobs) - 1:
                next_job  = jobs[i + 1]
                gap_months = _months_between(job["end_ym"], next_job["start_ym"])
                if gap_months > 0:
                    entry["gap_after_months"] = gap_months
                    entry["gap_severity"]     = _classify_gap(gap_months)
            timeline.append(entry)

        # employment_gaps list — only gaps >= 3 months (negligible ones excluded)
        employment_gaps: List[Dict[str, Any]] = []
        for i, entry in enumerate(timeline):
            if entry["gap_after_months"] >= 3:
                next_start = jobs[i + 1]["start_ym"] if i + 1 < len(jobs) else ""
                employment_gaps.append({
                    "start_date":      entry["to"],
                    "end_date":        next_start,
                    "duration_months": entry["gap_after_months"],
                    "severity":        entry["gap_severity"],
                })

        # overlapping_jobs — any pair with meaningful overlap (>1 month)
        overlapping_jobs: List[Dict[str, Any]] = []
        for i in range(len(jobs)):
            for j in range(i + 1, len(jobs)):
                a, b = jobs[i], jobs[j]
                if a["start_ym"] <= b["end_ym"] and b["start_ym"] <= a["end_ym"]:
                    overlap = _months_between(b["start_ym"], min(a["end_ym"], b["end_ym"]))
                    if overlap > 1:
                        overlapping_jobs.append({
                            "job1": f"{a['role']} at {a['company']}",
                            "job2": f"{b['role']} at {b['company']}",
                            "type": "overlapping_job",
                        })

        # short_stints — roles lasting < 6 months
        short_stints: List[Dict[str, Any]] = [
            {
                "company":          job["company"],
                "title":            job["role"],
                "duration_months":  job["duration_months"],
                "type":             "short_stint",
            }
            for job in jobs
            if 0 < job["duration_months"] < 6
        ]

        # Overlap-aware total experience — merge overlapping intervals, then sum
        intervals = [(job["start_ym"], job["end_ym"]) for job in jobs]
        merged    = _merge_intervals(intervals)
        total_months = sum(_months_between(s, e) for s, e in merged)
        total_years  = round(total_months / 12, 1)

        return {
            "employment_timeline": timeline,
            "employment_gaps":     employment_gaps,
            "overlapping_jobs":    overlapping_jobs,
            "short_stints":        short_stints,
            "total_years":         total_years,
        }


def analyze_gaps(work_experience: List[Dict[str, Any]]) -> Dict[str, Any]:
    return GapDetector().analyze(work_experience)
