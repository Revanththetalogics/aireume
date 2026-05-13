"""
Phase 4 Tests: Continuous Learning System

Tests for:
1. Outcome tracking & storage
2. Skill weight optimization
3. Predictive analytics
4. Model retraining pipeline
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from services.continuous_learning import (
    OutcomeTracker,
    SkillWeightOptimizer,
    PredictiveAnalytics,
    ModelRetrainingPipeline
)


class TestOutcomeTracker:
    """Test outcome tracking."""

    def test_record_outcome(self):
        """Test recording a hiring outcome."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            
            outcome = {
                "candidate_id": "cand_001",
                "jd_id": "jd_001",
                "original_score": 85.0,
                "stages": {
                    "screening": {"passed": True, "score": 90},
                    "technical_interview": {"passed": True, "score": 85}
                },
                "decision": "hired",
                "performance_30d": {"rating": 4.5, "feedback": "Excellent"},
                "performance_90d": {"rating": 4.7, "feedback": "Outstanding"}
            }
            
            outcome_id = tracker.record_outcome(outcome)
            
            assert "cand_001_jd_001" in outcome_id
            
            # Verify file was created
            filepath = os.path.join(tmpdir, f"{outcome_id}.json")
            assert os.path.exists(filepath)
            
            # Verify content
            with open(filepath, 'r') as f:
                saved = json.load(f)
            
            assert saved["decision"] == "hired"
            assert saved["performance_90d"]["rating"] == 4.7

    def test_get_outcomes(self):
        """Test retrieving outcomes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            
            # Record multiple outcomes
            for i in range(3):
                tracker.record_outcome({
                    "candidate_id": f"cand_{i:03d}",
                    "jd_id": "jd_001",
                    "original_score": 80.0 + i * 5,
                    "decision": "hired" if i < 2 else "rejected"
                })
            
            outcomes = tracker.get_outcomes()
            assert len(outcomes) == 3
            
            # Filter by decision
            hired = tracker.get_outcomes(decision="hired")
            assert len(hired) == 2

    def test_get_successful_hires(self):
        """Test filtering successful hires."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            
            # Record successful hire
            tracker.record_outcome({
                "candidate_id": "cand_good",
                "jd_id": "jd_001",
                "original_score": 85.0,
                "decision": "hired",
                "performance_90d": {"rating": 4.5}
            })
            
            # Record unsuccessful hire
            tracker.record_outcome({
                "candidate_id": "cand_bad",
                "jd_id": "jd_001",
                "original_score": 75.0,
                "decision": "hired",
                "performance_90d": {"rating": 2.5}
            })
            
            successful = tracker.get_successful_hires()
            assert len(successful) == 1
            assert successful[0]["candidate_id"] == "cand_good"


class TestSkillWeightOptimizer:
    """Test skill weight optimization."""

    def test_analyze_success_patterns_insufficient_data(self):
        """Test analysis with insufficient data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            optimizer = SkillWeightOptimizer(tracker)
            
            # No data
            patterns = optimizer.analyze_success_patterns()
            
            assert patterns["insufficient_data"] is True
            assert patterns["sample_size"] == 0

    def test_analyze_success_patterns_with_data(self):
        """Test analysis with sufficient data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            
            # Record 10 successful hires
            for i in range(10):
                tracker.record_outcome({
                    "candidate_id": f"cand_{i:03d}",
                    "jd_id": "jd_001",
                    "original_score": 80.0 + i * 2,
                    "decision": "hired",
                    "performance_90d": {"rating": 4.0 + (i % 10) / 10}
                })
            
            optimizer = SkillWeightOptimizer(tracker)
            patterns = optimizer.analyze_success_patterns()
            
            assert patterns["insufficient_data"] is False
            assert patterns["sample_size"] == 10
            assert "optimal_weights" in patterns

    def test_suggest_weights(self):
        """Test weight suggestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            optimizer = SkillWeightOptimizer(tracker)
            
            # Mock successful hires
            successful_hires = [
                {"original_score": 85, "performance_90d": {"rating": 4.5}},
                {"original_score": 90, "performance_90d": {"rating": 4.8}}
            ]
            
            weights = optimizer._suggest_weights(successful_hires)
            
            assert "skills" in weights
            assert "experience" in weights
            assert sum(weights.get(k, 0) for k in ["skills", "experience", "education", "risk"]) > 0


class TestPredictiveAnalytics:
    """Test predictive analytics."""

    def test_heuristic_prediction_high_score(self):
        """Test prediction for high-scoring candidate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            analytics = PredictiveAnalytics(tracker)
            
            result = analytics.predict_success(90)
            
            assert result["interview_pass_probability"] > 0.80
            assert result["predicted_90d_performance"] >= 4.0
            assert result["confidence"] == 0.50  # Heuristic confidence

    def test_heuristic_prediction_low_score(self):
        """Test prediction for low-scoring candidate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            analytics = PredictiveAnalytics(tracker)
            
            result = analytics.predict_success(35)
            
            assert result["interview_pass_probability"] < 0.50
            assert result["predicted_90d_performance"] < 3.0

    def test_data_driven_prediction(self):
        """Test prediction with historical data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            
            # Record historical outcomes
            for i in range(15):
                tracker.record_outcome({
                    "candidate_id": f"hist_{i:03d}",
                    "jd_id": "jd_001",
                    "original_score": 80.0 + (i % 10),
                    "decision": "hired" if i < 12 else "rejected",
                    "performance_90d": {"rating": 4.0 + (i % 10) / 10},
                    "retention_6m": i < 10
                })
            
            analytics = PredictiveAnalytics(tracker)
            result = analytics.predict_success(85)
            
            # Should use data-driven prediction
            assert "Based on" in result["factors"][0]
            assert result["confidence"] > 0.50

    def test_prediction_with_factors(self):
        """Test that predictions include explanatory factors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            analytics = PredictiveAnalytics(tracker)
            
            result = analytics.predict_success(75)
            
            assert len(result["factors"]) > 0
            assert all(isinstance(f, str) for f in result["factors"])


class TestModelRetrainingPipeline:
    """Test model retraining pipeline."""

    def test_should_retrain_time_based(self):
        """Test time-based retraining trigger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            optimizer = SkillWeightOptimizer(tracker)
            pipeline = ModelRetrainingPipeline(tracker, optimizer)
            
            # Last retrained 31 days ago
            last_retrained = datetime.utcnow() - timedelta(days=31)
            
            assert pipeline.should_retrain(last_retrained) is True

    def test_should_retrain_data_based(self):
        """Test data-based retraining trigger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            
            # Record 55 new outcomes
            for i in range(55):
                tracker.record_outcome({
                    "candidate_id": f"cand_{i:03d}",
                    "jd_id": "jd_001",
                    "original_score": 80.0,
                    "decision": "hired"
                })
            
            optimizer = SkillWeightOptimizer(tracker)
            pipeline = ModelRetrainingPipeline(tracker, optimizer)
            
            # Last retrained yesterday
            last_retrained = datetime.utcnow() - timedelta(days=1)
            
            assert pipeline.should_retrain(last_retrained) is True

    def test_should_not_retrain(self):
        """Test when retraining is not needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            
            # Record only 10 outcomes
            for i in range(10):
                tracker.record_outcome({
                    "candidate_id": f"cand_{i:03d}",
                    "jd_id": "jd_001",
                    "original_score": 80.0,
                    "decision": "hired"
                })
            
            optimizer = SkillWeightOptimizer(tracker)
            pipeline = ModelRetrainingPipeline(tracker, optimizer)
            
            # Last retrained 15 days ago
            last_retrained = datetime.utcnow() - timedelta(days=15)
            
            assert pipeline.should_retrain(last_retrained) is False

    def test_execute_retraining_insufficient_data(self):
        """Test retraining with insufficient data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            optimizer = SkillWeightOptimizer(tracker)
            pipeline = ModelRetrainingPipeline(tracker, optimizer)
            
            result = pipeline.execute_retraining()
            
            assert result["retrained"] is False
            assert "Insufficient data" in result["reason"]

    def test_execute_retraining_with_data(self):
        """Test retraining with sufficient data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OutcomeTracker(storage_path=tmpdir)
            
            # Record 20 successful hires with varying scores
            for i in range(20):
                tracker.record_outcome({
                    "candidate_id": f"cand_{i:03d}",
                    "jd_id": "jd_001",
                    "original_score": 70.0 + i * 2,
                    "decision": "hired",
                    "performance_90d": {"rating": 3.5 + (i % 15) / 10}
                })
            
            optimizer = SkillWeightOptimizer(tracker)
            pipeline = ModelRetrainingPipeline(tracker, optimizer)
            
            result = pipeline.execute_retraining()
            
            # May or may not retrain depending on correlation
            assert "retrained" in result
            assert "correlation" in result or "reason" in result


class TestIntegration:
    """Test integration between components."""

    def test_full_learning_loop(self):
        """Test complete learning loop from outcome to prediction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            tracker = OutcomeTracker(storage_path=tmpdir)
            optimizer = SkillWeightOptimizer(tracker)
            analytics = PredictiveAnalytics(tracker)
            pipeline = ModelRetrainingPipeline(tracker, optimizer)
            
            # Record outcomes
            for i in range(15):
                tracker.record_outcome({
                    "candidate_id": f"cand_{i:03d}",
                    "jd_id": "jd_001",
                    "original_score": 75.0 + i * 2,
                    "decision": "hired" if i < 12 else "rejected",
                    "performance_90d": {"rating": 4.0 + (i % 10) / 10}
                })
            
            # Analyze patterns
            patterns = optimizer.analyze_success_patterns()
            assert patterns["sample_size"] > 0
            
            # Make prediction
            prediction = analytics.predict_success(85)
            assert prediction["interview_pass_probability"] > 0
            
            # Check retraining
            last_retrained = datetime.utcnow() - timedelta(days=45)
            assert pipeline.should_retrain(last_retrained) is True
