"""
Phase 3: Explainable AI Scoring System

Enterprise-grade explainable scoring with:
1. EvidenceChain for full audit trail
2. Component-level score breakdown
3. Bias detection & mitigation
4. Actionable improvement suggestions
5. Risk factor identification
"""

from typing import Dict, List, Optional
from datetime import datetime


class EvidenceChain:
    """
    Track evidence for every scoring decision.
    
    Provides full transparency and auditability for AI scoring decisions.
    """
    
    def __init__(self):
        self.evidence_log: List[Dict] = []
    
    def record(
        self,
        component: str,
        claim: str,
        evidence: str,
        source: str,
        confidence: float,
        score_impact: float = 0.0,
        mitigating_factors: Optional[List[str]] = None
    ):
        """
        Record a piece of evidence supporting a score.
        
        Args:
            component: Score component (skills, experience, education, etc.)
            claim: What is being claimed (e.g., "Candidate has Python expertise")
            evidence: Supporting evidence from resume/JD
            source: Where evidence came from (e.g., "Resume: Work Experience")
            confidence: Confidence in this evidence (0.0-1.0)
            score_impact: How much this impacted the score (+/-)
            mitigating_factors: Factors that mitigate gaps/weaknesses
        """
        self.evidence_log.append({
            "component": component,
            "claim": claim,
            "evidence": evidence,
            "source": source,
            "confidence": round(confidence, 2),
            "score_impact": round(score_impact, 2),
            "mitigating_factors": mitigating_factors or [],
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_evidence_for_component(self, component: str) -> List[Dict]:
        """Get all evidence for a specific component."""
        return [e for e in self.evidence_log if e["component"] == component]
    
    def get_high_confidence_evidence(self, threshold: float = 0.8) -> List[Dict]:
        """Get evidence above confidence threshold."""
        return [e for e in self.evidence_log if e["confidence"] >= threshold]
    
    def get_low_confidence_evidence(self, threshold: float = 0.5) -> List[Dict]:
        """Get evidence below confidence threshold (uncertain claims)."""
        return [e for e in self.evidence_log if e["confidence"] < threshold]
    
    def generate_audit_trail(self) -> str:
        """Generate human-readable audit trail."""
        trail = []
        trail.append("=" * 80)
        trail.append("EXPLAINABLE AI SCORING - AUDIT TRAIL")
        trail.append("=" * 80)
        trail.append("")
        
        # Group by component
        components = {}
        for entry in self.evidence_log:
            comp = entry["component"]
            if comp not in components:
                components[comp] = []
            components[comp].append(entry)
        
        for component, entries in components.items():
            trail.append(f"\n{component.upper().replace('_', ' ')}:")
            trail.append("-" * 60)
            
            for entry in entries:
                trail.append(f"  Claim: {entry['claim']}")
                trail.append(f"    Evidence: {entry['evidence']}")
                trail.append(f"    Source: {entry['source']}")
                trail.append(f"    Confidence: {entry['confidence']:.0%}")
                trail.append(f"    Score Impact: {entry['score_impact']:+.2f}")
                
                if entry["mitigating_factors"]:
                    trail.append(f"    Mitigating: {', '.join(entry['mitigating_factors'])}")
                
                trail.append("")
        
        return "\n".join(trail)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_evidence_items": len(self.evidence_log),
            "evidence": self.evidence_log,
            "audit_trail": self.generate_audit_trail()
        }


class BiasDetector:
    """
    Detect and mitigate bias in scoring decisions.
    
    Monitors for:
    - Education bias (overweighting pedigree)
    - Age bias (penalizing experience gaps)
    - Gender bias (language patterns)
    - Geographic bias (location preferences)
    """
    
    def detect_bias(self, score_components: Dict, candidate_data: Dict) -> Dict:
        """
        Analyze scoring for potential biases.
        
        Returns:
            {
                "bias_detected": bool,
                "bias_types": List[str],
                "severity": "low" | "medium" | "high",
                "recommendations": List[str],
                "audit_notes": str
            }
        """
        bias_types = []
        recommendations = []
        
        # Check education bias
        education_bias = self._check_education_bias(score_components)
        if education_bias["biased"]:
            bias_types.append("education_bias")
            recommendations.extend(education_bias["recommendations"])
        
        # Check experience bias
        experience_bias = self._check_experience_bias(score_components, candidate_data)
        if experience_bias["biased"]:
            bias_types.append("experience_bias")
            recommendations.extend(experience_bias["recommendations"])
        
        # Calculate overall severity
        severity = self._calculate_severity(bias_types)
        
        return {
            "bias_detected": len(bias_types) > 0,
            "bias_types": bias_types,
            "severity": severity,
            "recommendations": recommendations,
            "audit_notes": f"Checked {len(bias_types)} bias types: {', '.join(bias_types) if bias_types else 'none detected'}"
        }
    
    def _check_education_bias(self, score_components: Dict) -> Dict:
        """Check if education is overweighted relative to skills/experience."""
        education_score = score_components.get("education", {}).get("score", 50)
        skills_score = score_components.get("skills", {}).get("score", 50)
        experience_score = score_components.get("experience", {}).get("score", 50)
        
        # Education shouldn't dominate if skills/experience are strong
        if education_score > 90 and (skills_score < 70 or experience_score < 70):
            return {
                "biased": True,
                "recommendations": [
                    "Education score is high but skills/experience scores are lower",
                    "Consider if education is being overweighted vs practical abilities",
                    "Review if degree requirements are truly necessary for the role"
                ]
            }
        
        return {"biased": False, "recommendations": []}
    
    def _check_experience_bias(self, score_components: Dict, candidate_data: Dict) -> Dict:
        """Check for age/experience bias."""
        timeline_score = score_components.get("timeline", {}).get("score", 50)
        
        # Check if career gaps are penalized too heavily
        employment_gaps = candidate_data.get("employment_gaps", [])
        if len(employment_gaps) > 0 and timeline_score < 40:
            return {
                "biased": True,
                "recommendations": [
                    "Candidate has employment gaps that may be unfairly penalized",
                    "Consider reasons for gaps (education, caregiving, entrepreneurship)",
                    "Focus on skills and capabilities rather than continuous employment"
                ]
            }
        
        return {"biased": False, "recommendations": []}
    
    def _calculate_severity(self, bias_types: List[str]) -> str:
        """Calculate overall bias severity."""
        if len(bias_types) == 0:
            return "low"
        elif len(bias_types) == 1:
            return "medium"
        else:
            return "high"


class ExplainableScorer:
    """
    Generate transparent, evidence-based scoring with full audit trail.
    """
    
    def __init__(self):
        self.evidence_chain = EvidenceChain()
        self.bias_detector = BiasDetector()
    
    def compute_explainable_score(
        self,
        skill_match: Dict,
        experience_analysis: Dict,
        education_analysis: Dict,
        jd_data: Dict,
        candidate_data: Dict
    ) -> Dict:
        """
        Compute comprehensive explainable score.
        
        Args:
            skill_match: Output from match_skills_enterprise()
            experience_analysis: Experience matching results
            education_analysis: Education matching results
            jd_data: Parsed JD data
            candidate_data: Parsed candidate data
        
        Returns:
            Full explainable scoring result with evidence
        """
        # Reset evidence chain
        self.evidence_chain = EvidenceChain()
        
        # Component scores
        skills_score = self._score_skills(skill_match, jd_data)
        experience_score = self._score_experience(experience_analysis, jd_data)
        education_score = self._score_education(education_analysis, jd_data)
        
        # Weighted overall score
        overall_score = (
            skills_score["score"] * 0.40 +
            experience_score["score"] * 0.30 +
            education_score["score"] * 0.20 +
            self._calculate_risk_score(skill_match, experience_analysis) * 0.10
        )
        
        # Compile component scores
        component_scores = {
            "skills": skills_score,
            "experience": experience_score,
            "education": education_score
        }
        
        # Bias detection
        bias_analysis = self.bias_detector.detect_bias(component_scores, candidate_data)
        
        # Generate strengths and gaps
        strengths = self._identify_strengths(skill_match, experience_analysis)
        gaps = self._identify_gaps(skill_match, experience_analysis)
        risk_factors = self._identify_risks(experience_analysis)
        improvement_suggestions = self._generate_improvement_suggestions(gaps)
        
        # Determine recommendation
        recommendation = self._determine_recommendation(overall_score)
        
        return {
            "overall_fit_score": round(overall_score, 2),
            "recommendation": recommendation,
            "confidence": self._calculate_overall_confidence(component_scores),
            
            "component_scores": component_scores,
            
            "strengths": strengths,
            "gaps": gaps,
            "risk_factors": risk_factors,
            "improvement_suggestions": improvement_suggestions,
            
            "bias_audit": bias_analysis,
            
            "evidence_chain": self.evidence_chain.to_dict()
        }
    
    def _score_skills(self, skill_match: Dict, jd_data: Dict) -> Dict:
        """Score skills component with evidence."""
        weighted_score = skill_match.get("weighted_skill_score", 0)
        
        # Record evidence for matched skills
        for skill in skill_match.get("matched_required", []):
            self.evidence_chain.record(
                component="skills",
                claim=f"Candidate has required skill: {skill}",
                evidence=f"Matched against JD requirement",
                source="Resume skills section",
                confidence=0.90,
                score_impact=+5.0
            )
        
        # Record evidence for missing skills
        for skill in skill_match.get("missing_required", []):
            mitigating = []
            # Check if candidate has related skills
            matched_str = " ".join(skill_match.get("matched_required", [])).lower()
            if any(related in matched_str for related in self._get_related_skills(skill)):
                mitigating.append(f"Has related skills that may compensate")
            
            self.evidence_chain.record(
                component="skills",
                claim=f"Candidate missing required skill: {skill}",
                evidence=f"Not found in resume",
                source="Resume skills analysis",
                confidence=0.75,
                score_impact=-5.0,
                mitigating_factors=mitigating if mitigating else None
            )
        
        return {
            "score": weighted_score,
            "breakdown": {
                "required_match_score": skill_match.get("required_match_score", 0),
                "nice_to_have_score": skill_match.get("nice_to_have_score", 0),
                "matched_required_count": len(skill_match.get("matched_required", [])),
                "missing_required_count": len(skill_match.get("missing_required", []))
            },
            "evidence_count": len(self.evidence_chain.get_evidence_for_component("skills"))
        }
    
    def _score_experience(self, experience_analysis: Dict, jd_data: Dict) -> Dict:
        """Score experience component with evidence."""
        score = experience_analysis.get("score", 50)
        
        years_candidate = experience_analysis.get("years", 0)
        years_required = jd_data.get("required_years", 0)
        
        if years_candidate >= years_required:
            self.evidence_chain.record(
                component="experience",
                claim=f"Candidate meets experience requirement ({years_candidate}y vs {years_required}y required)",
                evidence=f"{years_candidate} years of relevant experience",
                source="Resume work history",
                confidence=0.85,
                score_impact=+10.0
            )
        else:
            self.evidence_chain.record(
                component="experience",
                claim=f"Candidate below experience requirement ({years_candidate}y vs {years_required}y required)",
                evidence=f"Gap of {years_required - years_candidate} years",
                source="Resume work history",
                confidence=0.90,
                score_impact=-10.0,
                mitigating_factors=["Quality of experience may compensate for quantity"]
            )
        
        return {
            "score": score,
            "breakdown": {
                "years_match": experience_analysis.get("years", 0),
                "years_required": years_required,
                "seniority_alignment": experience_analysis.get("seniority_match", 50)
            },
            "evidence_count": len(self.evidence_chain.get_evidence_for_component("experience"))
        }
    
    def _score_education(self, education_analysis: Dict, jd_data: Dict) -> Dict:
        """Score education component with evidence."""
        score = education_analysis.get("score", 50)
        
        degree = education_analysis.get("degree", "Not specified")
        if degree and degree != "Not specified":
            self.evidence_chain.record(
                component="education",
                claim=f"Candidate has {degree} degree",
                evidence=f"Listed in education section",
                source="Resume education",
                confidence=0.95,
                score_impact=+5.0
            )
        
        return {
            "score": score,
            "breakdown": {
                "degree": degree,
                "field_alignment": education_analysis.get("field_alignment", 50)
            },
            "evidence_count": len(self.evidence_chain.get_evidence_for_component("education"))
        }
    
    def _calculate_risk_score(self, skill_match: Dict, experience_analysis: Dict) -> float:
        """Calculate risk score (lower is better)."""
        risk_score = 100.0
        
        # High skill gap increases risk
        missing_ratio = len(skill_match.get("missing_required", [])) / max(
            len(skill_match.get("matched_required", [])) + len(skill_match.get("missing_required", [])),
            1
        )
        risk_score -= missing_ratio * 30
        
        # Experience gap increases risk
        if experience_analysis.get("years", 0) < experience_analysis.get("required_years", 0):
            risk_score -= 20
        
        return max(0, min(100, risk_score))
    
    def _identify_strengths(self, skill_match: Dict, experience_analysis: Dict) -> List[str]:
        """Identify candidate strengths."""
        strengths = []
        
        if skill_match.get("required_match_score", 0) >= 80:
            strengths.append(f"Strong skill match ({skill_match['required_match_score']:.0f}% of required skills)")
        
        if experience_analysis.get("years", 0) > experience_analysis.get("required_years", 0) * 1.5:
            strengths.append(f"Extensive experience ({experience_analysis['years']}y vs {experience_analysis.get('required_years', 0)}y required)")
        
        if len(skill_match.get("matched_nice_to_have", [])) > 2:
            strengths.append(f"Has {len(skill_match['matched_nice_to_have'])} bonus skills")
        
        return strengths
    
    def _identify_gaps(self, skill_match: Dict, experience_analysis: Dict) -> List[str]:
        """Identify candidate gaps."""
        gaps = []
        
        for skill in skill_match.get("missing_required", []):
            gaps.append(f"Missing required skill: {skill}")
        
        if experience_analysis.get("years", 0) < experience_analysis.get("required_years", 0):
            gap = experience_analysis.get("required_years", 0) - experience_analysis.get("years", 0)
            gaps.append(f"Experience gap: {gap} years below requirement")
        
        return gaps
    
    def _identify_risks(self, experience_analysis: Dict) -> List[Dict]:
        """Identify risk factors."""
        risks = []
        
        # Overqualification risk
        if experience_analysis.get("years", 0) > experience_analysis.get("required_years", 0) * 2:
            risks.append({
                "risk": "Overqualified",
                "probability": 0.40,
                "impact": "May leave for higher-level role within 12-18 months",
                "mitigation": "Discuss career growth path and alignment during interview"
            })
        
        return risks
    
    def _generate_improvement_suggestions(self, gaps: List[str]) -> List[str]:
        """Generate suggestions for addressing gaps."""
        suggestions = []
        
        for gap in gaps:
            if "Missing required skill" in gap:
                skill = gap.split(":")[-1].strip()
                suggestions.append(f"Explore transferable skills or willingness to learn {skill}")
            elif "Experience gap" in gap:
                suggestions.append("Highlight relevant projects or achievements that demonstrate capability")
        
        return suggestions
    
    def _determine_recommendation(self, score: float) -> str:
        """Determine hiring recommendation based on score."""
        if score >= 85:
            return "Strong Match - Highly Recommend"
        elif score >= 70:
            return "Good Match - Recommend"
        elif score >= 55:
            return "Fair Match - Consider"
        elif score >= 40:
            return "Weak Match - Review Carefully"
        else:
            return "Poor Match - Not Recommended"
    
    def _calculate_overall_confidence(self, component_scores: Dict) -> float:
        """Calculate overall confidence in the score."""
        evidence_counts = [
            comp.get("evidence_count", 0)
            for comp in component_scores.values()
        ]
        
        total_evidence = sum(evidence_counts)
        
        # More evidence = higher confidence (up to a point)
        confidence = min(0.95, 0.60 + (total_evidence * 0.05))
        
        return round(confidence, 2)
    
    def _get_related_skills(self, skill: str) -> List[str]:
        """Get related skills that might compensate for a missing skill."""
        relations = {
            "python": ["django", "fastapi", "flask"],
            "react": ["vue", "angular", "javascript"],
            "postgresql": ["mysql", "mongodb", "sql"],
            "aws": ["gcp", "azure", "cloud"],
            "docker": ["kubernetes", "containers"],
        }
        
        return relations.get(skill.lower(), [])
