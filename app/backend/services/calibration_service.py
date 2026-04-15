"""
Calibration & Drift Detection Service

Ensures consistent scoring over time by running analysis on known-good calibration
examples and detecting when the model's scoring drifts from expected values.

Provides:
- Calibration dataset management
- Automated daily calibration checks
- Drift detection and alerting
- Calibration logs for audit
"""
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


@dataclass
class CalibrationExample:
    """A single calibration example with expected results."""
    id: str
    transcript: str
    jd: str
    expected_fit_score: int
    expected_recommendation: str
    category: str  # strong_technical, moderate_fit, poor_fit, etc.
    description: str


@dataclass
class CalibrationResult:
    """Result of running calibration on one example."""
    calibration_id: str
    category: str
    expected_score: int
    actual_score: int
    score_drift: int
    expected_recommendation: str
    actual_recommendation: str
    recommendation_match: bool
    timestamp: datetime


class CalibrationService:
    """
    Service for model calibration and drift detection.
    
    Runs analysis on known examples and compares results to expected values.
    Alerts when scoring drifts beyond acceptable thresholds.
    """
    
    def __init__(self, drift_threshold: int = 10):
        """
        Initialize calibration service.
        
        Args:
            drift_threshold: Maximum acceptable drift in points (default: 10)
        """
        self.drift_threshold = drift_threshold
        self.calibration_examples = self._load_calibration_examples()
    
    def _load_calibration_examples(self) -> List[CalibrationExample]:
        """
        Load calibration dataset.
        
        These are carefully curated examples with known-good scores.
        """
        return [
            CalibrationExample(
                id="cal_001_strong_python",
                transcript=(
                    "I have six years of professional Python experience. "
                    "I've built REST APIs using FastAPI and Django, implemented "
                    "microservices architecture with Docker and Kubernetes, and "
                    "led a team of 4 developers on a major migration project. "
                    "I'm proficient in async programming, database optimization, "
                    "and have experience with AWS services like Lambda and RDS."
                ),
                jd=(
                    "Looking for a Senior Python Engineer with 5+ years experience. "
                    "Must have: FastAPI, Docker, AWS, microservices architecture. "
                    "Nice to have: Team leadership, database optimization."
                ),
                expected_fit_score=85,
                expected_recommendation="proceed",
                category="strong_technical",
                description="Strong candidate with all required skills and evidence"
            ),
            CalibrationExample(
                id="cal_002_moderate_fit",
                transcript=(
                    "I have three years of Python experience, mostly with Django. "
                    "I've worked on web applications and APIs. I'm familiar with "
                    "Docker basics and have used AWS EC2 for deployments. "
                    "I haven't worked with microservices yet but I'm eager to learn."
                ),
                jd=(
                    "Looking for a Senior Python Engineer with 5+ years experience. "
                    "Must have: FastAPI, Docker, AWS, microservices architecture."
                ),
                expected_fit_score=55,
                expected_recommendation="hold",
                category="moderate_fit",
                description="Moderate candidate with some skills but gaps in experience"
            ),
            CalibrationExample(
                id="cal_003_poor_fit",
                transcript=(
                    "I'm a JavaScript developer with two years of experience. "
                    "I've worked mainly with React and Node.js. I've heard of "
                    "Python but haven't used it professionally. I'm a quick learner "
                    "and interested in backend development."
                ),
                jd=(
                    "Looking for a Senior Python Engineer with 5+ years experience. "
                    "Must have: FastAPI, Docker, AWS, microservices architecture."
                ),
                expected_fit_score=25,
                expected_recommendation="reject",
                category="poor_fit",
                description="Poor fit - lacks required skills and experience"
            ),
            CalibrationExample(
                id="cal_004_strong_communication",
                transcript=(
                    "I have five years of Python experience building scalable APIs. "
                    "Let me walk you through my approach: First, I analyze requirements "
                    "and design the API structure. Then I implement using FastAPI with "
                    "proper error handling and validation. I use Docker for containerization "
                    "and deploy to AWS ECS. I also write comprehensive tests and documentation. "
                    "In my last project, I reduced API latency by 40% through caching and optimization."
                ),
                jd=(
                    "Looking for a Senior Python Engineer with 5+ years experience. "
                    "Must have: FastAPI, Docker, AWS, microservices architecture. "
                    "Strong communication skills required."
                ),
                expected_fit_score=90,
                expected_recommendation="proceed",
                category="strong_technical_and_communication",
                description="Excellent candidate with strong technical skills and communication"
            ),
            CalibrationExample(
                id="cal_005_red_flag",
                transcript=(
                    "I have ten years of Python experience. Well, actually maybe eight years. "
                    "I worked at Google... I mean, a company similar to Google. "
                    "I've built systems handling millions of requests. The exact numbers "
                    "are confidential but it was a lot. I can do anything you need."
                ),
                jd=(
                    "Looking for a Senior Python Engineer with 5+ years experience. "
                    "Must have: FastAPI, Docker, AWS, microservices architecture."
                ),
                expected_fit_score=35,
                expected_recommendation="reject",
                category="red_flags",
                description="Red flags - inconsistent statements, vague claims, no evidence"
            ),
        ]
    
    async def run_calibration_check(
        self,
        analyze_func: Any,  # The analyze_transcript function
    ) -> Dict[str, Any]:
        """
        Run calibration check on all examples.
        
        Args:
            analyze_func: The analyze_transcript function to test
            
        Returns:
            Calibration report with drift metrics and status
        """
        logger.info("Starting calibration check...")
        
        results = []
        
        # Run analysis on each calibration example
        for example in self.calibration_examples:
            try:
                # Run analysis (with PII redaction and evidence validation)
                actual_result = await analyze_func(
                    transcript=example.transcript,
                    jd_text=example.jd,
                    candidate_name="CANDIDATE",
                    enable_pii_redaction=True,
                    enable_evidence_validation=True
                )
                
                # Calculate drift
                actual_score = actual_result.get("fit_score", 50)
                score_drift = abs(actual_score - example.expected_fit_score)
                
                # Check recommendation match
                actual_rec = actual_result.get("recommendation", "hold")
                rec_match = actual_rec == example.expected_recommendation
                
                result = CalibrationResult(
                    calibration_id=example.id,
                    category=example.category,
                    expected_score=example.expected_fit_score,
                    actual_score=actual_score,
                    score_drift=score_drift,
                    expected_recommendation=example.expected_recommendation,
                    actual_recommendation=actual_rec,
                    recommendation_match=rec_match,
                    timestamp=datetime.utcnow()
                )
                
                results.append(result)
                
                logger.info(
                    f"Calibration {example.id}: "
                    f"Expected {example.expected_fit_score}, Got {actual_score}, "
                    f"Drift: {score_drift}, Rec Match: {rec_match}"
                )
                
            except Exception as e:
                logger.error(f"Calibration failed for {example.id}: {e}")
                # Continue with other examples
                continue
        
        if not results:
            return {
                "status": "ERROR",
                "error": "All calibration checks failed",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Calculate aggregate metrics
        avg_drift = statistics.mean([r.score_drift for r in results])
        max_drift = max([r.score_drift for r in results])
        rec_accuracy = sum(r.recommendation_match for r in results) / len(results)
        
        # Determine status
        status = "OK"
        if avg_drift > self.drift_threshold:
            status = "ALERT"
            logger.warning(f"Calibration drift detected: {avg_drift:.1f} points (threshold: {self.drift_threshold})")
        
        report = {
            "status": status,
            "average_drift": avg_drift,
            "max_drift": max_drift,
            "recommendation_accuracy": rec_accuracy,
            "total_examples": len(results),
            "results": [
                {
                    "calibration_id": r.calibration_id,
                    "category": r.category,
                    "expected_score": r.expected_score,
                    "actual_score": r.actual_score,
                    "score_drift": r.score_drift,
                    "expected_recommendation": r.expected_recommendation,
                    "actual_recommendation": r.actual_recommendation,
                    "recommendation_match": r.recommendation_match,
                }
                for r in results
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "drift_threshold": self.drift_threshold,
        }
        
        logger.info(
            f"Calibration complete: Status={status}, "
            f"Avg Drift={avg_drift:.1f}, Rec Accuracy={rec_accuracy:.1%}"
        )
        
        return report
    
    def generate_alert_message(self, report: Dict[str, Any]) -> str:
        """Generate alert message for administrators."""
        if report["status"] != "ALERT":
            return ""
        
        message = f"""⚠️ CALIBRATION DRIFT ALERT

Average scoring drift: {report['average_drift']:.1f} points (threshold: {report['drift_threshold']})
Maximum drift: {report['max_drift']} points
Recommendation accuracy: {report['recommendation_accuracy']:.1%}

Problematic examples:
"""
        
        # Show examples with high drift
        for result in report["results"]:
            if result["score_drift"] > self.drift_threshold:
                message += f"\n- {result['calibration_id']}: Expected {result['expected_score']}, Got {result['actual_score']} (drift: {result['score_drift']})"
        
        message += "\n\nAction required: Review model configuration and consider recalibration."
        
        return message
    
    def generate_summary(self, report: Dict[str, Any]) -> str:
        """Generate human-readable summary of calibration report."""
        status_emoji = "✅" if report["status"] == "OK" else "⚠️"
        
        summary = f"""{status_emoji} Calibration Report
Status: {report['status']}
Timestamp: {report['timestamp']}

Metrics:
- Average Drift: {report['average_drift']:.1f} points
- Max Drift: {report['max_drift']} points
- Recommendation Accuracy: {report['recommendation_accuracy']:.1%}
- Examples Tested: {report['total_examples']}

Results by Category:
"""
        
        # Group by category
        by_category = {}
        for result in report["results"]:
            cat = result["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(result)
        
        for category, results in by_category.items():
            avg_drift = statistics.mean([r["score_drift"] for r in results])
            summary += f"\n{category}: Avg drift {avg_drift:.1f} points"
        
        return summary


# Singleton instance
_calibration_service: Optional[CalibrationService] = None


def get_calibration_service(drift_threshold: int = 10) -> CalibrationService:
    """Get or create singleton calibration service."""
    global _calibration_service
    if _calibration_service is None:
        _calibration_service = CalibrationService(drift_threshold=drift_threshold)
    return _calibration_service
