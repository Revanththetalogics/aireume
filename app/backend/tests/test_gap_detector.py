import pytest
from datetime import datetime
from app.backend.services.gap_detector import GapDetector, analyze_gaps


class TestGapDetector:
    def test_detect_gaps_with_6_month_plus_gap(self):
        detector = GapDetector()
        work_exp = [
            {"company": "Company A", "title": "Dev", "start_date": "2020-01", "end_date": "2021-06"},
            {"company": "Company B", "title": "Dev", "start_date": "2022-02", "end_date": "present"}
        ]

        gaps = detector.detect_gaps(work_exp)

        assert len(gaps) == 1
        assert gaps[0]["duration_months"] >= 6

    def test_detect_gaps_with_no_gap(self):
        detector = GapDetector()
        work_exp = [
            {"company": "Company A", "title": "Dev", "start_date": "2020-01", "end_date": "2021-06"},
            {"company": "Company B", "title": "Dev", "start_date": "2021-07", "end_date": "present"}
        ]

        gaps = detector.detect_gaps(work_exp)

        assert len(gaps) == 0

    def test_detect_overlapping_jobs(self):
        detector = GapDetector()
        work_exp = [
            {"company": "Company A", "title": "Dev", "start_date": "2020-01", "end_date": "2022-01"},
            {"company": "Company B", "title": "Dev", "start_date": "2021-01", "end_date": "2023-01"}
        ]

        overlaps = detector.detect_overlaps(work_exp)

        assert len(overlaps) >= 1

    def test_detect_short_stints(self):
        detector = GapDetector()
        work_exp = [
            {"company": "Company A", "title": "Dev", "start_date": "2020-01", "end_date": "2020-03"},
            {"company": "Company B", "title": "Dev", "start_date": "2020-06", "end_date": "present"}
        ]

        short_stints = detector.detect_short_stints(work_exp)

        assert len(short_stints) >= 1
        assert short_stints[0]["duration_months"] < 6

    def test_calculate_total_experience(self):
        detector = GapDetector()
        work_exp = [
            {"company": "Company A", "title": "Dev", "start_date": "2020-01", "end_date": "2021-01"},
            {"company": "Company B", "title": "Dev", "start_date": "2021-06", "end_date": "present"}
        ]

        total_years = detector._calculate_total_experience(work_exp)

        assert total_years > 0

    def test_analyze_gaps_function(self):
        work_exp = [
            {"company": "Company A", "title": "Dev", "start_date": "2020-01", "end_date": "2021-06"},
            {"company": "Company B", "title": "Dev", "start_date": "2022-02", "end_date": "present"}
        ]

        result = analyze_gaps(work_exp)

        assert "employment_gaps" in result
        assert "overlapping_jobs" in result
        assert "short_stints" in result
        assert "total_years" in result

    def test_empty_work_experience(self):
        detector = GapDetector()
        result = detector.analyze([])

        assert result["employment_gaps"] == []
        assert result["overlapping_jobs"] == []
        assert result["short_stints"] == []
        assert result["total_years"] == 0.0
