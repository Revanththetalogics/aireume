"""
Phase 4: Continuous Learning System

Enterprise-grade continuous learning from hiring outcomes:
1. Outcome tracking & storage
2. Skill weight optimization based on success patterns
3. Predictive analytics for hiring success
4. Model retraining triggers
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os


class OutcomeTracker:
    """
    Track hiring outcomes to continuously improve matching accuracy.
    
    Stores:
    - Interview results (pass/fail at each stage)
    - Hiring decisions (hired/rejected)
    - Performance reviews (30/60/90 day)
    - Retention data
    - Hiring manager satisfaction
    """
    
    def __init__(self, storage_path: str = "data/outcomes"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def record_outcome(self, outcome: Dict) -> str:
        """
        Record a hiring outcome.
        
        Args:
            outcome: {
                "candidate_id": str,
                "jd_id": str,
                "original_score": float,
                "stages": {
                    "screening": {"passed": bool, "score": float},
                    "technical_interview": {"passed": bool, "score": float},
                    "cultural_fit": {"passed": bool, "score": float}
                },
                "decision": "hired" | "rejected",
                "performance_30d": {"rating": float, "feedback": str},
                "performance_90d": {"rating": float, "feedback": str},
                "retention_6m": bool,
                "hiring_manager_satisfaction": float,  # 1-5
                "recorded_at": str  # ISO timestamp
            }
        
        Returns:
            outcome_id: Unique identifier for this outcome
        """
        outcome_id = f"{outcome['candidate_id']}_{outcome['jd_id']}_{datetime.utcnow().strftime('%Y%m%d')}"
        
        # Add metadata
        outcome["outcome_id"] = outcome_id
        outcome["recorded_at"] = outcome.get("recorded_at", datetime.utcnow().isoformat())
        
        # Save to file
        filepath = os.path.join(self.storage_path, f"{outcome_id}.json")
        with open(filepath, 'w') as f:
            json.dump(outcome, f, indent=2)
        
        return outcome_id
    
    def get_outcomes(self, jd_id: Optional[str] = None, 
                    decision: Optional[str] = None,
                    date_from: Optional[datetime] = None) -> List[Dict]:
        """
        Retrieve outcomes with optional filtering.
        
        Args:
            jd_id: Filter by specific job
            decision: Filter by decision (hired/rejected)
            date_from: Filter by date range
        
        Returns:
            List of outcome dictionaries
        """
        outcomes = []
        
        for filename in os.listdir(self.storage_path):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.storage_path, filename)
            with open(filepath, 'r') as f:
                outcome = json.load(f)
            
            # Apply filters
            if jd_id and outcome.get("jd_id") != jd_id:
                continue
            
            if decision and outcome.get("decision") != decision:
                continue
            
            if date_from:
                recorded = datetime.fromisoformat(outcome.get("recorded_at", "2000-01-01"))
                if recorded < date_from:
                    continue
            
            outcomes.append(outcome)
        
        return outcomes
    
    def get_successful_hires(self, jd_id: Optional[str] = None) -> List[Dict]:
        """Get all successful hires (hired + good performance)."""
        all_outcomes = self.get_outcomes(jd_id=jd_id, decision="hired")
        
        successful = []
        for outcome in all_outcomes:
            # Consider successful if performance rating >= 4.0
            # Must have performance data to be considered successful
            perf_90 = outcome.get("performance_90d", {})
            perf_30 = outcome.get("performance_30d", {})
            
            rating_90 = perf_90.get("rating")
            rating_30 = perf_30.get("rating")
            
            # Only count as successful if we have performance data and it's good
            if rating_90 is not None and rating_90 >= 4.0:
                successful.append(outcome)
            elif rating_90 is None and rating_30 is not None and rating_30 >= 4.0:
                # Fall back to 30-day if no 90-day data
                successful.append(outcome)
        
        return successful


class SkillWeightOptimizer:
    """
    Optimize skill weights based on hiring outcomes.
    
    Learns:
    - Which skills actually predict success
    - Which skill gaps are critical vs acceptable
    - How to weight different score components
    """
    
    def __init__(self, outcome_tracker: OutcomeTracker):
        self.outcome_tracker = outcome_tracker
    
    def analyze_success_patterns(self, jd_id: Optional[str] = None) -> Dict:
        """
        Analyze patterns in successful hires.
        
        Returns:
            {
                "skills_correlation": {skill: correlation_with_success},
                "critical_skills": [skills always present in successful hires],
                "acceptable_gaps": [skills often missing in successful hires],
                "optimal_weights": {component: weight},
                "sample_size": int
            }
        """
        successful_hires = self.outcome_tracker.get_successful_hires(jd_id)
        
        if len(successful_hires) < 5:
            return {
                "skills_correlation": {},
                "critical_skills": [],
                "acceptable_gaps": [],
                "optimal_weights": {},
                "sample_size": len(successful_hires),
                "insufficient_data": True
            }
        
        # Analyze skill frequency in successful hires
        skill_frequency = {}
        total_hires = len(successful_hires)
        
        for hire in successful_hires:
            # Extract skills from original score components
            # This would come from the original matching data
            # For now, we'll track score patterns
            score = hire.get("original_score", 0)
            
            # Track performance vs original score correlation
            perf_90 = hire.get("performance_90d", {}).get("rating", 0)
            
            # Store for analysis
            skill_frequency[hire.get("outcome_id")] = {
                "score": score,
                "performance": perf_90
            }
        
        # Calculate correlations (simplified)
        correlations = self._calculate_correlations(skill_frequency)
        
        return {
            "skills_correlation": correlations,
            "critical_skills": [],  # Would require skill-level data
            "acceptable_gaps": [],
            "optimal_weights": self._suggest_weights(successful_hires),
            "sample_size": total_hires,
            "insufficient_data": False
        }
    
    def _calculate_correlations(self, data: Dict) -> Dict:
        """Calculate correlation between scores and performance."""
        if not data:
            return {}
        
        scores = [v["score"] for v in data.values() if v["performance"] > 0]
        performances = [v["performance"] for v in data.values() if v["performance"] > 0]
        
        if len(scores) < 3:
            return {}
        
        # Simple correlation calculation
        mean_scores = sum(scores) / len(scores)
        mean_perf = sum(performances) / len(performances)
        
        numerator = sum((s - mean_scores) * (p - mean_perf) 
                       for s, p in zip(scores, performances))
        denom_scores = sum((s - mean_scores) ** 2 for s in scores) ** 0.5
        denom_perf = sum((p - mean_perf) ** 2 for p in performances) ** 0.5
        
        if denom_scores == 0 or denom_perf == 0:
            return {}
        
        correlation = numerator / (denom_scores * denom_perf)
        
        return {
            "score_performance_correlation": round(correlation, 3)
        }
    
    def _suggest_weights(self, successful_hires: List[Dict]) -> Dict:
        """Suggest optimal weights based on successful hire patterns."""
        # Analyze what score components correlate with success
        # For now, return current defaults with note
        return {
            "skills": 0.40,
            "experience": 0.30,
            "education": 0.20,
            "risk": 0.10,
            "note": "Weights based on current defaults - need more data for optimization"
        }


class PredictiveAnalytics:
    """
    Predict hiring outcomes based on historical data.
    
    Predictions:
    - Probability of interview pass
    - Probability of offer acceptance
    - 90-day performance prediction
    - 1-year retention probability
    """
    
    def __init__(self, outcome_tracker: OutcomeTracker):
        self.outcome_tracker = outcome_tracker
    
    def predict_success(self, candidate_score: float, 
                       job_function: str = "other") -> Dict:
        """
        Predict candidate success probability.
        
        Args:
            candidate_score: Overall fit score from matching
            job_function: Job function for context
        
        Returns:
            {
                "interview_pass_probability": float,
                "predicted_90d_performance": float,
                "predicted_1y_retention": float,
                "confidence": float,
                "factors": List[str]
            }
        """
        # Get historical data for calibration
        historical_outcomes = self.outcome_tracker.get_outcomes()
        
        if len(historical_outcomes) < 10:
            # Not enough data - use heuristic predictions
            return self._heuristic_prediction(candidate_score)
        
        # Use historical data for predictions
        return self._data_driven_prediction(candidate_score, historical_outcomes)
    
    def _heuristic_prediction(self, score: float) -> Dict:
        """Generate predictions using heuristics when data is limited."""
        # Linear mapping from score to probabilities
        interview_prob = max(0.1, min(0.95, score / 100.0))
        performance_pred = max(2.0, min(5.0, (score / 100.0) * 5.0))
        retention_prob = max(0.5, min(0.95, 0.6 + (score / 100.0) * 0.35))
        
        return {
            "interview_pass_probability": round(interview_prob, 2),
            "predicted_90d_performance": round(performance_pred, 1),
            "predicted_1y_retention": round(retention_prob, 2),
            "confidence": 0.50,  # Low confidence due to heuristic
            "factors": [
                "Prediction based on score heuristics (limited historical data)",
                f"Score of {score:.0f} suggests {'strong' if score > 75 else 'moderate' if score > 55 else 'weak'} candidate"
            ]
        }
    
    def _data_driven_prediction(self, score: float, 
                               historical_outcomes: List[Dict]) -> Dict:
        """Generate predictions based on historical data."""
        # Find similar-score candidates in history
        similar_candidates = [
            o for o in historical_outcomes
            if abs(o.get("original_score", 0) - score) < 10
        ]
        
        if len(similar_candidates) < 5:
            return self._heuristic_prediction(score)
        
        # Calculate statistics from similar candidates
        hired_count = sum(1 for o in similar_candidates if o.get("decision") == "hired")
        interview_pass_rate = hired_count / len(similar_candidates)
        
        # Performance prediction
        performances = [
            o.get("performance_90d", {}).get("rating", 0)
            for o in similar_candidates
            if o.get("performance_90d", {}).get("rating", 0) > 0
        ]
        
        avg_performance = sum(performances) / len(performances) if performances else 3.5
        
        # Retention prediction
        retention_data = [
            o.get("retention_6m", False)
            for o in similar_candidates
            if "retention_6m" in o
        ]
        
        retention_rate = sum(retention_data) / len(retention_data) if retention_data else 0.75
        
        return {
            "interview_pass_probability": round(interview_pass_rate, 2),
            "predicted_90d_performance": round(avg_performance, 1),
            "predicted_1y_retention": round(retention_rate, 2),
            "confidence": min(0.85, 0.60 + (len(similar_candidates) * 0.05)),
            "factors": [
                f"Based on {len(similar_candidates)} similar candidates",
                f"Historical interview pass rate: {interview_pass_rate:.0%}",
                f"Average 90-day performance: {avg_performance:.1f}/5.0"
            ]
        }


class ModelRetrainingPipeline:
    """
    Automated model retraining based on new outcome data.
    
    Triggers retraining when:
    - Sufficient new outcomes collected (e.g., 50+)
    - Model performance degrades
    - Scheduled interval (e.g., monthly)
    """
    
    def __init__(self, outcome_tracker: OutcomeTracker, 
                 weight_optimizer: SkillWeightOptimizer):
        self.outcome_tracker = outcome_tracker
        self.weight_optimizer = weight_optimizer
    
    def should_retrain(self, last_retrained: datetime) -> bool:
        """Determine if model should be retrained."""
        # Check time-based trigger (monthly)
        days_since_retrain = (datetime.utcnow() - last_retrained).days
        if days_since_retrain >= 30:
            return True
        
        # Check data-based trigger (50+ new outcomes)
        new_outcomes = self.outcome_tracker.get_outcomes(
            date_from=last_retrained
        )
        
        if len(new_outcomes) >= 50:
            return True
        
        return False
    
    def execute_retraining(self) -> Dict:
        """
        Execute model retraining pipeline.
        
        Returns:
            Retraining results and new weights
        """
        # Analyze success patterns
        patterns = self.weight_optimizer.analyze_success_patterns()
        
        if patterns.get("insufficient_data"):
            return {
                "retrained": False,
                "reason": f"Insufficient data (only {patterns['sample_size']} successful hires)",
                "minimum_required": 5
            }
        
        # Update weights if correlation is strong
        correlation = patterns.get("skills_correlation", {}).get(
            "score_performance_correlation", 0
        )
        
        if abs(correlation) > 0.3:
            # Strong correlation - use suggested weights
            new_weights = patterns["optimal_weights"]
            
            return {
                "retrained": True,
                "correlation": correlation,
                "new_weights": new_weights,
                "sample_size": patterns["sample_size"],
                "confidence": "high" if patterns["sample_size"] > 50 else "medium"
            }
        
        return {
            "retrained": False,
            "reason": "Weak correlation between scores and performance",
            "correlation": correlation
        }
