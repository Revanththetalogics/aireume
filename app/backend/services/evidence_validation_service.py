"""
Evidence Validation Service for Transcript Analysis

Validates that all claims made by the LLM are supported by actual evidence
from the transcript. Prevents hallucinations and ensures source-of-truth analysis.
"""
import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class EvidenceValidation:
    """Result of evidence validation."""
    is_valid: bool
    confidence: float  # 0-1
    match_type: str  # exact, fuzzy, paraphrase, missing
    matched_segment: Optional[str] = None


@dataclass
class ValidationReport:
    """Comprehensive validation report for analysis result."""
    total_claims: int
    verified_claims: int
    hallucinated_claims: int
    fuzzy_matches: int
    unsupported_claims: List[Dict[str, Any]]
    evidence_quality_score: float
    validation_details: List[Dict[str, Any]]


class EvidenceValidationService:
    """
    Validates that LLM claims are supported by transcript evidence.
    
    Uses multiple matching strategies:
    1. Exact substring match
    2. Fuzzy matching for paraphrases
    3. Semantic similarity (if available)
    """
    
    def __init__(self, fuzzy_threshold: float = 0.75):
        """
        Initialize evidence validator.
        
        Args:
            fuzzy_threshold: Minimum similarity score for fuzzy matches (0-1)
        """
        self.fuzzy_threshold = fuzzy_threshold
    
    def validate_analysis_result(
        self,
        analysis_result: Dict[str, Any],
        transcript: str
    ) -> ValidationReport:
        """
        Validate all evidence claims in analysis result.
        
        Args:
            analysis_result: LLM analysis output
            transcript: Original transcript text
            
        Returns:
            ValidationReport with detailed validation metrics
        """
        validation_details = []
        total_claims = 0
        verified_claims = 0
        hallucinated_claims = 0
        fuzzy_matches = 0
        unsupported_claims = []
        
        # Normalize transcript for matching
        transcript_normalized = self._normalize_text(transcript)
        
        # Validate JD alignment evidence
        for item in analysis_result.get("jd_alignment", []):
            if item.get("demonstrated") and item.get("evidence"):
                total_claims += 1
                validation = self._validate_evidence(
                    evidence=item["evidence"],
                    transcript=transcript_normalized,
                    claim_type="jd_alignment",
                    claim_context=item.get("requirement", "")
                )
                
                validation_details.append({
                    "claim_type": "jd_alignment",
                    "requirement": item.get("requirement"),
                    "evidence": item["evidence"],
                    "validation": validation
                })
                
                if validation.is_valid:
                    verified_claims += 1
                    if validation.match_type == "fuzzy":
                        fuzzy_matches += 1
                else:
                    hallucinated_claims += 1
                    unsupported_claims.append({
                        "type": "jd_alignment",
                        "claim": item.get("requirement"),
                        "evidence": item["evidence"],
                        "reason": f"No {validation.match_type} match found"
                    })
        
        # Validate strengths evidence
        for strength in analysis_result.get("strengths", []):
            if isinstance(strength, dict) and strength.get("evidence"):
                total_claims += 1
                validation = self._validate_evidence(
                    evidence=strength["evidence"],
                    transcript=transcript_normalized,
                    claim_type="strength",
                    claim_context=strength.get("strength", "")
                )
                
                validation_details.append({
                    "claim_type": "strength",
                    "strength": strength.get("strength"),
                    "evidence": strength["evidence"],
                    "validation": validation
                })
                
                if validation.is_valid:
                    verified_claims += 1
                    if validation.match_type == "fuzzy":
                        fuzzy_matches += 1
                else:
                    hallucinated_claims += 1
                    unsupported_claims.append({
                        "type": "strength",
                        "claim": strength.get("strength"),
                        "evidence": strength["evidence"],
                        "reason": f"No {validation.match_type} match found"
                    })
            elif isinstance(strength, str):
                # Old format - no evidence provided
                total_claims += 1
                unsupported_claims.append({
                    "type": "strength",
                    "claim": strength,
                    "evidence": None,
                    "reason": "No evidence provided"
                })
        
        # Validate red flags evidence
        for flag in analysis_result.get("red_flags", []):
            if flag.get("evidence"):
                total_claims += 1
                validation = self._validate_evidence(
                    evidence=flag["evidence"],
                    transcript=transcript_normalized,
                    claim_type="red_flag",
                    claim_context=flag.get("flag", "")
                )
                
                validation_details.append({
                    "claim_type": "red_flag",
                    "flag": flag.get("flag"),
                    "evidence": flag["evidence"],
                    "validation": validation
                })
                
                if validation.is_valid:
                    verified_claims += 1
                    if validation.match_type == "fuzzy":
                        fuzzy_matches += 1
                else:
                    hallucinated_claims += 1
                    unsupported_claims.append({
                        "type": "red_flag",
                        "claim": flag.get("flag"),
                        "evidence": flag["evidence"],
                        "reason": f"No {validation.match_type} match found"
                    })
        
        # Validate areas for improvement evidence
        for area in analysis_result.get("areas_for_improvement", []):
            if isinstance(area, dict) and area.get("evidence"):
                total_claims += 1
                validation = self._validate_evidence(
                    evidence=area["evidence"],
                    transcript=transcript_normalized,
                    claim_type="improvement_area",
                    claim_context=area.get("area", "")
                )
                
                validation_details.append({
                    "claim_type": "improvement_area",
                    "area": area.get("area"),
                    "evidence": area["evidence"],
                    "validation": validation
                })
                
                if validation.is_valid:
                    verified_claims += 1
                    if validation.match_type == "fuzzy":
                        fuzzy_matches += 1
                else:
                    hallucinated_claims += 1
        
        # Calculate evidence quality score
        evidence_quality_score = (
            (verified_claims / total_claims * 100) if total_claims > 0 else 100
        )
        
        return ValidationReport(
            total_claims=total_claims,
            verified_claims=verified_claims,
            hallucinated_claims=hallucinated_claims,
            fuzzy_matches=fuzzy_matches,
            unsupported_claims=unsupported_claims,
            evidence_quality_score=evidence_quality_score,
            validation_details=validation_details
        )
    
    def _validate_evidence(
        self,
        evidence: str,
        transcript: str,
        claim_type: str,
        claim_context: str
    ) -> EvidenceValidation:
        """
        Validate a single evidence claim against transcript.
        
        Uses multiple matching strategies in order of strictness.
        """
        if not evidence or evidence == "null" or len(evidence.strip()) < 5:
            return EvidenceValidation(
                is_valid=False,
                confidence=0.0,
                match_type="missing",
                matched_segment=None
            )
        
        evidence_normalized = self._normalize_text(evidence)
        
        # Strategy 1: Exact substring match
        if evidence_normalized in transcript:
            return EvidenceValidation(
                is_valid=True,
                confidence=1.0,
                match_type="exact",
                matched_segment=evidence
            )
        
        # Strategy 2: Fuzzy matching for paraphrases
        fuzzy_result = self._fuzzy_match(evidence_normalized, transcript)
        if fuzzy_result["similarity"] >= self.fuzzy_threshold:
            return EvidenceValidation(
                is_valid=True,
                confidence=fuzzy_result["similarity"],
                match_type="fuzzy",
                matched_segment=fuzzy_result["matched_segment"]
            )
        
        # Strategy 3: Keyword overlap (for very short evidence)
        if len(evidence.split()) <= 5:
            keyword_match = self._keyword_match(evidence_normalized, transcript)
            if keyword_match["overlap_ratio"] >= 0.8:
                return EvidenceValidation(
                    is_valid=True,
                    confidence=keyword_match["overlap_ratio"],
                    match_type="keyword",
                    matched_segment=keyword_match["matched_segment"]
                )
        
        # No match found
        return EvidenceValidation(
            is_valid=False,
            confidence=fuzzy_result["similarity"],
            match_type="no_match",
            matched_segment=None
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase
        text = text.lower()
        # Remove extra whitespace
        text = " ".join(text.split())
        # Remove common punctuation that doesn't affect meaning
        text = re.sub(r'[,;:!?.]', '', text)
        return text
    
    def _fuzzy_match(self, evidence: str, transcript: str) -> Dict[str, Any]:
        """
        Find best fuzzy match for evidence in transcript.
        
        Uses sliding window approach with SequenceMatcher.
        """
        evidence_words = evidence.split()
        window_size = len(evidence_words)
        transcript_words = transcript.split()
        
        best_similarity = 0.0
        best_segment = ""
        
        # Slide window across transcript
        for i in range(len(transcript_words) - window_size + 1):
            window = " ".join(transcript_words[i:i + window_size])
            similarity = SequenceMatcher(None, evidence, window).ratio()
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_segment = window
        
        # Also check with slightly larger/smaller windows
        for offset in [-2, -1, 1, 2]:
            adjusted_size = window_size + offset
            if adjusted_size < 3:
                continue
            
            for i in range(len(transcript_words) - adjusted_size + 1):
                window = " ".join(transcript_words[i:i + adjusted_size])
                similarity = SequenceMatcher(None, evidence, window).ratio()
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_segment = window
        
        return {
            "similarity": best_similarity,
            "matched_segment": best_segment if best_similarity >= self.fuzzy_threshold else None
        }
    
    def _keyword_match(self, evidence: str, transcript: str) -> Dict[str, Any]:
        """
        Match based on keyword overlap.
        
        Useful for short evidence snippets.
        """
        evidence_words = set(evidence.split())
        transcript_words = set(transcript.split())
        
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        evidence_keywords = evidence_words - stop_words
        transcript_keywords = transcript_words - stop_words
        
        if not evidence_keywords:
            return {"overlap_ratio": 0.0, "matched_segment": None}
        
        overlap = evidence_keywords.intersection(transcript_keywords)
        overlap_ratio = len(overlap) / len(evidence_keywords)
        
        # Find segment containing most keywords
        matched_segment = None
        if overlap_ratio >= 0.8:
            # Find a segment in transcript containing these keywords
            transcript_text = transcript
            for keyword in overlap:
                if keyword in transcript_text:
                    # Extract context around keyword
                    idx = transcript_text.find(keyword)
                    start = max(0, idx - 50)
                    end = min(len(transcript_text), idx + 50)
                    matched_segment = transcript_text[start:end]
                    break
        
        return {
            "overlap_ratio": overlap_ratio,
            "matched_segment": matched_segment
        }
    
    def generate_validation_summary(self, report: ValidationReport) -> str:
        """Generate human-readable validation summary."""
        if report.total_claims == 0:
            return "No evidence claims to validate."
        
        quality_rating = (
            "Excellent" if report.evidence_quality_score >= 90 else
            "Good" if report.evidence_quality_score >= 75 else
            "Fair" if report.evidence_quality_score >= 60 else
            "Poor"
        )
        
        summary = f"""Evidence Validation Summary:
- Total Claims: {report.total_claims}
- Verified Claims: {report.verified_claims} ({report.verified_claims/report.total_claims*100:.1f}%)
- Hallucinated Claims: {report.hallucinated_claims}
- Fuzzy Matches: {report.fuzzy_matches}
- Evidence Quality Score: {report.evidence_quality_score:.1f}/100 ({quality_rating})
"""
        
        if report.unsupported_claims:
            summary += f"\nUnsupported Claims ({len(report.unsupported_claims)}):\n"
            for claim in report.unsupported_claims[:5]:  # Show first 5
                summary += f"  - {claim['type']}: {claim['claim'][:100]}\n"
        
        return summary


# Singleton instance
_evidence_service: Optional[EvidenceValidationService] = None


def get_evidence_service() -> EvidenceValidationService:
    """Get or create singleton evidence validation service."""
    global _evidence_service
    if _evidence_service is None:
        _evidence_service = EvidenceValidationService()
    return _evidence_service
