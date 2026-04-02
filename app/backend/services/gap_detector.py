from datetime import datetime
from typing import List, Dict, Any
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
import re


class GapDetector:
    def __init__(self):
        self.GAP_THRESHOLD_MONTHS = 6
        self.SHORT_STINT_THRESHOLD_MONTHS = 6

    def detect_gaps(self, work_experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not work_experience:
            return []

        gaps = []
        sorted_jobs = self._sort_jobs_by_date(work_experience)

        for i in range(len(sorted_jobs) - 1):
            current_job = sorted_jobs[i]
            next_job = sorted_jobs[i + 1]

            current_end = self._parse_date(current_job.get('end_date', 'present'))
            next_start = self._parse_date(next_job.get('start_date'))

            if current_end and next_start:
                gap_months = self._calculate_months_between(current_end, next_start)

                if gap_months > self.GAP_THRESHOLD_MONTHS:
                    gaps.append({
                        "start_date": current_job.get('end_date', ''),
                        "end_date": next_job.get('start_date', ''),
                        "duration_months": gap_months,
                        "type": "employment_gap"
                    })

        return gaps

    def detect_overlaps(self, work_experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        overlaps = []
        sorted_jobs = self._sort_jobs_by_date(work_experience)

        for i in range(len(sorted_jobs)):
            for j in range(i + 1, len(sorted_jobs)):
                job1 = sorted_jobs[i]
                job2 = sorted_jobs[j]

                start1 = self._parse_date(job1.get('start_date'))
                end1 = self._parse_date(job1.get('end_date', 'present'))
                start2 = self._parse_date(job2.get('start_date'))
                end2 = self._parse_date(job2.get('end_date', 'present'))

                if start1 and end1 and start2 and end2:
                    if start1 <= end2 and start2 <= end1:
                        overlaps.append({
                            "job1": f"{job1.get('title', '')} at {job1.get('company', '')}",
                            "job2": f"{job2.get('title', '')} at {job2.get('company', '')}",
                            "type": "overlapping_job"
                        })

        return overlaps

    def detect_short_stints(self, work_experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        short_stints = []

        for job in work_experience:
            start = self._parse_date(job.get('start_date'))
            end = self._parse_date(job.get('end_date', 'present'))

            if start and end:
                duration_months = self._calculate_months_between(start, end)

                if duration_months < self.SHORT_STINT_THRESHOLD_MONTHS:
                    short_stints.append({
                        "company": job.get('company', ''),
                        "title": job.get('title', ''),
                        "duration_months": duration_months,
                        "type": "short_stint"
                    })

        return short_stints

    def analyze(self, work_experience: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "employment_gaps": self.detect_gaps(work_experience),
            "overlapping_jobs": self.detect_overlaps(work_experience),
            "short_stints": self.detect_short_stints(work_experience),
            "total_years": self._calculate_total_experience(work_experience)
        }

    def _sort_jobs_by_date(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def get_start_date(job):
            date = self._parse_date(job.get('start_date'))
            return date if date else datetime.min

        return sorted(jobs, key=get_start_date, reverse=False)

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str or date_str.lower() in ['present', 'current', 'now']:
            return datetime.now()

        try:
            return date_parser.parse(date_str, fuzzy=True)
        except:
            year_match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
            if year_match:
                return datetime(int(year_match.group(0)), 1, 1)
            return None

    def _calculate_months_between(self, start: datetime, end: datetime) -> int:
        rd = relativedelta(end, start)
        return rd.years * 12 + rd.months

    def _calculate_total_experience(self, work_experience: List[Dict[str, Any]]) -> float:
        if not work_experience:
            return 0.0

        total_months = 0
        for job in work_experience:
            start = self._parse_date(job.get('start_date'))
            end = self._parse_date(job.get('end_date', 'present'))

            if start and end:
                total_months += self._calculate_months_between(start, end)

        return round(total_months / 12, 1)


def analyze_gaps(work_experience: List[Dict[str, Any]]) -> Dict[str, Any]:
    detector = GapDetector()
    return detector.analyze(work_experience)
