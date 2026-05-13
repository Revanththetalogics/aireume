"""
Phase 3 Tests: Explainable AI Scoring System

Tests for:
1. EvidenceChain audit trail
2. Explainable scorer with component breakdown
3. Bias detection & mitigation
4. Recommendation generation
"""

import pytest
from services.explainable_scorer import EvidenceChain, BiasDetector, ExplainableScorer


class TestEvidenceChain:
    """Test evidence chain tracking."""

    def test_record_evidence(self):
        """Test recording evidence."""
        chain = EvidenceChain()
        chain.record(
            component="skills",
            claim="Candidate has Python expertise",
            evidence="7 years Python experience",
            source="Resume: Work Experience",
            confidence=0.95,
            score_impact=+5.0
        )
        
        assert len(chain.evidence_log) == 1
        assert chain.evidence_log[0]["component"] == "skills"
        assert chain.evidence_log[0]["confidence"] == 0.95

    def test_get_evidence_by_component(self):
        """Test filtering evidence by component."""
        chain = EvidenceChain()
        chain.record(component="skills", claim="Skill 1", evidence="Ev1", source="Src", confidence=0.9)
        chain.record(component="experience", claim="Exp 1", evidence="Ev2", source="Src", confidence=0.8)
        chain.record(component="skills", claim="Skill 2", evidence="Ev3", source="Src", confidence=0.85)
        
        skills_evidence = chain.get_evidence_for_component("skills")
        assert len(skills_evidence) == 2

    def test_confidence_filtering(self):
        """Test filtering by confidence threshold."""
        chain = EvidenceChain()
        chain.record(component="skills", claim="High conf", evidence="Ev1", source="Src", confidence=0.95)
        chain.record(component="skills", claim="Med conf", evidence="Ev2", source="Src", confidence=0.70)
        chain.record(component="skills", claim="Low conf", evidence="Ev3", source="Src", confidence=0.40)
        
        high_conf = chain.get_high_confidence_evidence(0.8)
        assert len(high_conf) == 1
        
        low_conf = chain.get_low_confidence_evidence(0.5)
        assert len(low_conf) == 1

    def test_audit_trail_generation(self):
        """Test audit trail is human-readable."""
        chain = EvidenceChain()
        chain.record(component="skills", claim="Test", evidence="Ev", source="Src", confidence=0.9)
        
        trail = chain.generate_audit_trail()
        
        assert "SKILLS" in trail
        assert "Test" in trail
        assert "0.90" in trail or "90%" in trail

    def test_to_dict(self):
        """Test dictionary serialization."""
        chain = EvidenceChain()
        chain.record(component="skills", claim="Test", evidence="Ev", source="Src", confidence=0.9)
        
        result = chain.to_dict()
        
        assert "total_evidence_items" in result
        assert "evidence" in result
        assert "audit_trail" in result
        assert result["total_evidence_items"] == 1


class TestBiasDetector:
    """Test bias detection."""

    def test_no_bias_detected(self):
        """Test when no bias is present."""
        detector = BiasDetector()
        
        score_components = {
            "skills": {"score": 80},
            "experience": {"score": 75},
            "education": {"score": 70}
        }
        candidate_data = {}
        
        result = detector.detect_bias(score_components, candidate_data)
        
        assert result["bias_detected"] is False
        assert result["severity"] == "low"

    def test_education_bias(self):
        """Test detection of education bias."""
        detector = BiasDetector()
        
        # Education very high, but skills/experience low
        score_components = {
            "skills": {"score": 60},
            "experience": {"score": 65},
            "education": {"score": 95}
        }
        candidate_data = {}
        
        result = detector.detect_bias(score_components, candidate_data)
        
        assert "education_bias" in result["bias_types"]
        assert len(result["recommendations"]) > 0

    def test_experience_bias_with_gaps(self):
        """Test detection of experience bias with employment gaps."""
        detector = BiasDetector()
        
        score_components = {
            "timeline": {"score": 35}
        }
        candidate_data = {
            "employment_gaps": [{"start": "2020", "end": "2021", "reason": "caregiving"}]
        }
        
        result = detector.detect_bias(score_components, candidate_data)
        
        assert "experience_bias" in result["bias_types"]

    def test_multiple_biases_severity(self):
        """Test that multiple biases increase severity."""
        detector = BiasDetector()
        
        score_components = {
            "skills": {"score": 60},
            "experience": {"score": 65},
            "education": {"score": 95},
            "timeline": {"score": 35}
        }
        candidate_data = {
            "employment_gaps": [{"start": "2020", "end": "2021"}]
        }
        
        result = detector.detect_bias(score_components, candidate_data)
        
        assert result["severity"] in ["medium", "high"]


class TestExplainableScorer:
    """Test explainable scoring system."""

    def test_basic_scoring(self):
        """Test basic scoring functionality."""
        scorer = ExplainableScorer()
        
        skill_match = {
            "weighted_skill_score": 85.0,
            "required_match_score": 90.0,
            "nice_to_have_score": 75.0,
            "matched_required": ["python", "fastapi"],
            "missing_required": [],
            "matched_nice_to_have": ["docker"]
        }
        
        experience_analysis = {
            "score": 80,
            "years": 5,
            "required_years": 3,
            "seniority_match": 85
        }
        
        education_analysis = {
            "score": 75,
            "degree": "Bachelor",
            "field_alignment": 70
        }
        
        jd_data = {"required_years": 3}
        candidate_data = {}
        
        result = scorer.compute_explainable_score(
            skill_match, experience_analysis, education_analysis,
            jd_data, candidate_data
        )
        
        assert "overall_fit_score" in result
        assert "recommendation" in result
        assert "component_scores" in result
        assert "evidence_chain" in result
        assert result["overall_fit_score"] > 0

    def test_recommendation_strong_match(self):
        """Test strong match recommendation."""
        scorer = ExplainableScorer()
        
        result = scorer._determine_recommendation(90)
        assert "Strong Match" in result

    def test_recommendation_good_match(self):
        """Test good match recommendation."""
        scorer = ExplainableScorer()
        
        result = scorer._determine_recommendation(75)
        assert "Good Match" in result

    def test_recommendation_fair_match(self):
        """Test fair match recommendation."""
        scorer = ExplainableScorer()
        
        result = scorer._determine_recommendation(60)
        assert "Fair Match" in result

    def test_recommendation_poor_match(self):
        """Test poor match recommendation."""
        scorer = ExplainableScorer()
        
        result = scorer._determine_recommendation(35)
        assert "Poor Match" in result

    def test_strengths_identification(self):
        """Test strength identification."""
        scorer = ExplainableScorer()
        
        skill_match = {
            "required_match_score": 90,
            "matched_nice_to_have": ["docker", "kubernetes", "aws"]
        }
        experience_analysis = {"years": 10, "required_years": 3}
        
        strengths = scorer._identify_strengths(skill_match, experience_analysis)
        
        assert len(strengths) >= 2

    def test_gaps_identification(self):
        """Test gap identification."""
        scorer = ExplainableScorer()
        
        skill_match = {
            "missing_required": ["postgresql", "redis"]
        }
        experience_analysis = {"years": 2, "required_years": 5}
        
        gaps = scorer._identify_gaps(skill_match, experience_analysis)
        
        assert len(gaps) >= 2
        assert any("postgresql" in gap for gap in gaps)
        assert any("Experience gap" in gap for gap in gaps)

    def test_improvement_suggestions(self):
        """Test improvement suggestion generation."""
        scorer = ExplainableScorer()
        
        gaps = [
            "Missing required skill: postgresql",
            "Experience gap: 3 years below requirement"
        ]
        
        suggestions = scorer._generate_improvement_suggestions(gaps)
        
        assert len(suggestions) >= 2
        assert any("postgresql" in s for s in suggestions)

    def test_risk_factors_overqualification(self):
        """Test overqualification risk detection."""
        scorer = ExplainableScorer()
        
        experience_analysis = {"years": 15, "required_years": 3}
        
        risks = scorer._identify_risks(experience_analysis)
        
        assert len(risks) >= 1
        assert any(r["risk"] == "Overqualified" for r in risks)

    def test_evidence_chain_populated(self):
        """Test that evidence chain is populated during scoring."""
        scorer = ExplainableScorer()
        
        skill_match = {
            "weighted_skill_score": 80.0,
            "required_match_score": 85.0,
            "nice_to_have_score": 70.0,
            "matched_required": ["python"],
            "missing_required": ["fastapi"],
            "matched_nice_to_have": []
        }
        
        experience_analysis = {"score": 75, "years": 4, "required_years": 3}
        education_analysis = {"score": 70, "degree": "Bachelor"}
        jd_data = {"required_years": 3}
        candidate_data = {}
        
        result = scorer.compute_explainable_score(
            skill_match, experience_analysis, education_analysis,
            jd_data, candidate_data
        )
        
        # Evidence chain should have items
        evidence = result["evidence_chain"]
        assert evidence["total_evidence_items"] > 0

    def test_bias_audit_included(self):
        """Test that bias audit is included in results."""
        scorer = ExplainableScorer()
        
        skill_match = {"weighted_skill_score": 80, "matched_required": [], "missing_required": []}
        experience_analysis = {"score": 75, "years": 5, "required_years": 3}
        education_analysis = {"score": 70, "degree": "Bachelor"}
        jd_data = {"required_years": 3}
        candidate_data = {}
        
        result = scorer.compute_explainable_score(
            skill_match, experience_analysis, education_analysis,
            jd_data, candidate_data
        )
        
        assert "bias_audit" in result
        assert "bias_detected" in result["bias_audit"]
        assert "bias_types" in result["bias_audit"]

    def test_confidence_calculation(self):
        """Test confidence calculation based on evidence."""
        scorer = ExplainableScorer()
        
        # More components = more evidence = higher confidence
        component_scores = {
            "skills": {"evidence_count": 5},
            "experience": {"evidence_count": 3},
            "education": {"evidence_count": 2}
        }
        
        confidence = scorer._calculate_overall_confidence(component_scores)
        
        assert 0.60 <= confidence <= 0.95

    def test_related_skills(self):
        """Test related skills lookup."""
        scorer = ExplainableScorer()
        
        related = scorer._get_related_skills("python")
        assert len(related) > 0
        assert "django" in related or "fastapi" in related

    def test_full_scoring_with_gaps(self):
        """Test full scoring scenario with gaps and mitigating factors."""
        scorer = ExplainableScorer()
        
        skill_match = {
            "weighted_skill_score": 65.0,
            "required_match_score": 60.0,
            "nice_to_have_score": 70.0,
            "matched_required": ["python"],
            "missing_required": ["fastapi", "postgresql"],
            "matched_nice_to_have": ["docker"]
        }
        
        experience_analysis = {
            "score": 70,
            "years": 4,
            "required_years": 5,
            "seniority_match": 75
        }
        
        education_analysis = {
            "score": 80,
            "degree": "Master",
            "field_alignment": 85
        }
        
        jd_data = {"required_years": 5}
        candidate_data = {}
        
        result = scorer.compute_explainable_score(
            skill_match, experience_analysis, education_analysis,
            jd_data, candidate_data
        )
        
        # Should have moderate score
        assert 50 <= result["overall_fit_score"] <= 80
        
        # Should identify gaps
        assert len(result["gaps"]) > 0
        
        # Should provide suggestions
        assert len(result["improvement_suggestions"]) > 0
        
        # Should have evidence
        assert result["evidence_chain"]["total_evidence_items"] > 0
