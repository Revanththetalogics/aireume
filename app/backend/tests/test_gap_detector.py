"""
Tests for app/backend/services/gap_detector.py

Covers:
  - Date string normalization (_to_ym)
  - Month arithmetic (_months_between)
  - Gap severity classification (_classify_gap)
  - Interval merging (_merge_intervals) — key fix for total_years double-count
  - GapDetector.analyze() — all scenarios
  - analyze_gaps() top-level helper
"""
import pytest
from datetime import datetime

from app.backend.services.gap_detector import (
    GapDetector,
    analyze_gaps,
    _to_ym,
    _months_between,
    _classify_gap,
    _merge_intervals,
)


# ─── _to_ym ───────────────────────────────────────────────────────────────────

class TestToYm:
    def test_iso_date(self):
        assert _to_ym("2020-01-15") == "2020-01"

    def test_month_year(self):
        assert _to_ym("January 2020") == "2020-01"

    def test_year_only(self):
        assert _to_ym("2018") == "2018-01"

    def test_present_keyword(self):
        result = _to_ym("present")
        # Should return current YYYY-MM
        expected = datetime.now().strftime("%Y-%m")
        assert result == expected

    def test_current_keyword(self):
        result = _to_ym("current")
        assert result == datetime.now().strftime("%Y-%m")

    def test_now_keyword(self):
        result = _to_ym("now")
        assert result == datetime.now().strftime("%Y-%m")

    def test_none_returns_none(self):
        assert _to_ym(None) is None

    def test_empty_string_returns_none(self):
        assert _to_ym("") is None

    def test_unparseable_returns_none(self):
        assert _to_ym("not a date at all xyz") is None

    def test_slash_separated(self):
        assert _to_ym("03/2021") == "2021-03"


# ─── _months_between ──────────────────────────────────────────────────────────

class TestMonthsBetween:
    def test_same_month_is_zero(self):
        assert _months_between("2020-01", "2020-01") == 0

    def test_one_month_apart(self):
        assert _months_between("2020-01", "2020-02") == 1

    def test_twelve_months_is_one_year(self):
        assert _months_between("2020-01", "2021-01") == 12

    def test_end_before_start_returns_zero(self):
        assert _months_between("2021-06", "2020-01") == 0

    def test_twenty_seven_months(self):
        assert _months_between("2019-03", "2021-06") == 27


# ─── _classify_gap ────────────────────────────────────────────────────────────

class TestClassifyGap:
    def test_zero_months_is_negligible(self):
        assert _classify_gap(0) == "negligible"

    def test_two_months_is_negligible(self):
        assert _classify_gap(2) == "negligible"

    def test_three_months_is_minor(self):
        assert _classify_gap(3) == "minor"

    def test_five_months_is_minor(self):
        assert _classify_gap(5) == "minor"

    def test_six_months_is_moderate(self):
        assert _classify_gap(6) == "moderate"

    def test_eleven_months_is_moderate(self):
        assert _classify_gap(11) == "moderate"

    def test_twelve_months_is_critical(self):
        assert _classify_gap(12) == "critical"

    def test_eighteen_months_is_critical(self):
        assert _classify_gap(18) == "critical"


# ─── _merge_intervals ─────────────────────────────────────────────────────────

class TestMergeIntervals:
    def test_empty_list(self):
        assert _merge_intervals([]) == []

    def test_single_interval(self):
        assert _merge_intervals([("2020-01", "2021-01")]) == [("2020-01", "2021-01")]

    def test_non_overlapping_preserved(self):
        intervals = [("2018-01", "2019-01"), ("2020-01", "2021-01")]
        merged = _merge_intervals(intervals)
        assert len(merged) == 2

    def test_overlapping_merged_into_one(self):
        intervals = [("2019-01", "2021-01"), ("2020-06", "2022-01")]
        merged = _merge_intervals(intervals)
        assert len(merged) == 1
        assert merged[0] == ("2019-01", "2022-01")

    def test_adjacent_intervals_merged(self):
        intervals = [("2019-01", "2020-01"), ("2020-01", "2021-01")]
        merged = _merge_intervals(intervals)
        assert len(merged) == 1

    def test_three_overlapping_all_merge(self):
        intervals = [("2018-01", "2020-06"), ("2019-06", "2021-06"), ("2020-01", "2022-01")]
        merged = _merge_intervals(intervals)
        assert len(merged) == 1
        assert merged[0][0] == "2018-01"
        assert merged[0][1] == "2022-01"


# ─── GapDetector.analyze() ────────────────────────────────────────────────────

class TestGapDetector:
    def test_empty_work_experience(self):
        result = GapDetector().analyze([])
        assert result["employment_timeline"] == []
        assert result["employment_gaps"] == []
        assert result["overlapping_jobs"] == []
        assert result["short_stints"] == []
        assert result["total_years"] == 0.0

    def test_result_keys_present(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2020-01", "end_date": "2022-01"}
        ]
        result = GapDetector().analyze(work_exp)
        for key in ("employment_timeline", "employment_gaps", "overlapping_jobs",
                    "short_stints", "total_years"):
            assert key in result

    # ── Employment gaps ──

    def test_detects_moderate_gap_between_jobs(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2020-01", "end_date": "2021-06"},
            {"company": "B", "title": "Dev", "start_date": "2022-02", "end_date": "present"},
        ]
        result = GapDetector().analyze(work_exp)
        assert len(result["employment_gaps"]) == 1
        gap = result["employment_gaps"][0]
        assert gap["duration_months"] >= 6
        assert gap["severity"] in ("minor", "moderate", "critical")

    def test_no_gap_when_jobs_are_consecutive(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2020-01", "end_date": "2021-06"},
            {"company": "B", "title": "Dev", "start_date": "2021-07", "end_date": "present"},
        ]
        result = GapDetector().analyze(work_exp)
        # 1-month gap → negligible → excluded from employment_gaps (< 3 months threshold)
        assert len(result["employment_gaps"]) == 0

    def test_negligible_gap_excluded_from_employment_gaps(self):
        """Gaps < 3 months are classified as negligible and excluded from the gaps list."""
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2020-01", "end_date": "2021-01"},
            {"company": "B", "title": "Dev", "start_date": "2021-02", "end_date": "present"},
        ]
        result = GapDetector().analyze(work_exp)
        assert len(result["employment_gaps"]) == 0

    def test_gap_severity_labels_on_timeline(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2018-01", "end_date": "2019-01"},
            {"company": "B", "title": "Dev", "start_date": "2020-06", "end_date": "present"},
        ]
        result = GapDetector().analyze(work_exp)
        # 17-month gap → critical
        timeline_entry = result["employment_timeline"][0]
        assert timeline_entry["gap_severity"] == "critical"
        assert timeline_entry["gap_after_months"] >= 12

    # ── Short stints ──

    def test_detects_short_stint(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2020-01", "end_date": "2020-03"},
            {"company": "B", "title": "Dev", "start_date": "2020-06", "end_date": "present"},
        ]
        result = GapDetector().analyze(work_exp)
        assert len(result["short_stints"]) >= 1
        assert result["short_stints"][0]["duration_months"] < 6

    def test_normal_tenure_not_short_stint(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2020-01", "end_date": "2022-01"},
        ]
        result = GapDetector().analyze(work_exp)
        assert len(result["short_stints"]) == 0

    # ── Overlapping jobs ──

    def test_detects_overlapping_jobs(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2020-01", "end_date": "2022-01"},
            {"company": "B", "title": "Dev", "start_date": "2021-01", "end_date": "2023-01"},
        ]
        result = GapDetector().analyze(work_exp)
        assert len(result["overlapping_jobs"]) >= 1

    def test_non_overlapping_jobs_not_flagged(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2018-01", "end_date": "2019-12"},
            {"company": "B", "title": "Dev", "start_date": "2020-03", "end_date": "present"},
        ]
        result = GapDetector().analyze(work_exp)
        assert len(result["overlapping_jobs"]) == 0

    # ── Overlap-aware total_years (key fix) ──

    def test_total_years_does_not_double_count_overlapping_periods(self):
        """
        REGRESSION TEST — The old code summed raw durations causing double-counting.
        Two overlapping 2-year jobs should count as ~2 years, not ~4.
        """
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2018-01", "end_date": "2020-01"},
            {"company": "B", "title": "Dev", "start_date": "2018-06", "end_date": "2020-06"},
        ]
        result = GapDetector().analyze(work_exp)
        # Merged interval: 2018-01 → 2020-06 = 29 months ≈ 2.4 years, not 4 years
        assert result["total_years"] < 3.0
        assert result["total_years"] > 1.5

    def test_total_years_correct_for_sequential_jobs(self):
        """Sequential jobs with a gap: total_years should equal combined tenures."""
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2018-01", "end_date": "2020-01"},  # 24 months
            {"company": "B", "title": "Dev", "start_date": "2021-01", "end_date": "2023-01"},  # 24 months
        ]
        result = GapDetector().analyze(work_exp)
        # 48 months = 4.0 years (gap excluded from total)
        assert result["total_years"] == pytest.approx(4.0, abs=0.2)

    def test_total_years_positive(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2019-01", "end_date": "present"},
        ]
        result = GapDetector().analyze(work_exp)
        assert result["total_years"] > 0

    # ── Timeline structure ──

    def test_timeline_entry_structure(self):
        work_exp = [
            {"company": "A", "title": "Engineer", "start_date": "2020-01", "end_date": "2021-06"},
        ]
        result = GapDetector().analyze(work_exp)
        entry = result["employment_timeline"][0]
        assert entry["role"] == "Engineer"
        assert entry["company"] == "A"
        assert entry["from"] == "2020-01"
        assert entry["to"] == "2021-06"
        assert "duration_months" in entry
        assert "gap_after_months" in entry

    def test_timeline_sorted_chronologically(self):
        work_exp = [
            {"company": "B", "title": "Dev", "start_date": "2020-01", "end_date": "2021-06"},
            {"company": "A", "title": "Junior", "start_date": "2015-06", "end_date": "2019-12"},
        ]
        result = GapDetector().analyze(work_exp)
        timeline = result["employment_timeline"]
        assert timeline[0]["company"] == "A"
        assert timeline[1]["company"] == "B"

    def test_skips_jobs_with_no_start_date(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": None, "end_date": "2021-06"},
            {"company": "B", "title": "Dev", "start_date": "2022-01", "end_date": "present"},
        ]
        result = GapDetector().analyze(work_exp)
        # Job A has no start date — should be ignored
        assert len(result["employment_timeline"]) == 1
        assert result["employment_timeline"][0]["company"] == "B"


# ─── analyze_gaps() top-level function ────────────────────────────────────────

class TestAnalyzeGapsFunction:
    def test_returns_required_keys(self):
        work_exp = [
            {"company": "A", "title": "Dev", "start_date": "2020-01", "end_date": "2022-01"},
        ]
        result = analyze_gaps(work_exp)
        for key in ("employment_timeline", "employment_gaps", "overlapping_jobs",
                    "short_stints", "total_years"):
            assert key in result

    def test_empty_input(self):
        result = analyze_gaps([])
        assert result["total_years"] == 0.0
        assert result["employment_gaps"] == []

    def test_single_current_job(self):
        work_exp = [
            {"company": "FAANG", "title": "Staff Engineer",
             "start_date": "2019-06", "end_date": "present"},
        ]
        result = analyze_gaps(work_exp)
        assert result["total_years"] > 0
        assert len(result["employment_gaps"]) == 0
