"""
PII Redaction Service for Transcript Analysis

Removes personally identifiable information (PII) from transcripts before analysis
to eliminate bias based on names, locations, organizations, and other identifiers.

Uses Presidio for enterprise-grade PII detection and anonymization.
"""
import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RedactionResult:
    """Result of PII redaction operation."""
    redacted_text: str
    redaction_map: Dict[str, List[str]]
    redaction_count: int
    confidence_scores: Dict[str, float]


class PIIRedactionService:
    """
    Service for detecting and redacting PII from transcripts.
    
    Fallback implementation using regex patterns when Presidio is unavailable.
    For production, install: pip install presidio-analyzer presidio-anonymizer spacy
    """
    
    def __init__(self):
        self.use_presidio = False
        self.analyzer = None
        self.anonymizer = None
        
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            self.use_presidio = True
            logger.info("Presidio PII redaction initialized successfully")
        except ImportError:
            logger.warning(
                "Presidio not available. Using regex fallback for PII redaction. "
                "Install with: pip install presidio-analyzer presidio-anonymizer"
            )
    
    def redact_pii(self, text: str) -> RedactionResult:
        """
        Redact PII from text while maintaining context for evaluation.
        
        Args:
            text: Original transcript text
            
        Returns:
            RedactionResult with redacted text and audit trail
        """
        if self.use_presidio:
            return self._redact_with_presidio(text)
        else:
            return self._redact_with_regex(text)
    
    def _redact_with_presidio(self, text: str) -> RedactionResult:
        """Redact using Presidio (enterprise-grade)."""
        try:
            # Analyze text for PII entities
            results = self.analyzer.analyze(
                text=text,
                entities=[
                    "PERSON",
                    "EMAIL_ADDRESS", 
                    "PHONE_NUMBER",
                    "LOCATION",
                    "ORG",
                    "URL",
                    "US_SSN",
                    "CREDIT_CARD",
                ],
                language="en"
            )
            
            # Build redaction map for audit trail
            redaction_map = {}
            confidence_scores = {}
            
            for result in results:
                entity_type = result.entity_type
                original_value = text[result.start:result.end]
                
                if entity_type not in redaction_map:
                    redaction_map[entity_type] = []
                    confidence_scores[entity_type] = []
                
                redaction_map[entity_type].append(original_value)
                confidence_scores[entity_type].append(result.score)
            
            # Anonymize with context-preserving placeholders
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "PERSON": {"type": "replace", "new_value": "CANDIDATE"},
                    "EMAIL_ADDRESS": {"type": "replace", "new_value": "EMAIL"},
                    "PHONE_NUMBER": {"type": "replace", "new_value": "PHONE"},
                    "LOCATION": {"type": "replace", "new_value": "LOCATION"},
                    "ORG": {"type": "replace", "new_value": "ORGANIZATION"},
                    "URL": {"type": "replace", "new_value": "URL"},
                    "US_SSN": {"type": "replace", "new_value": "SSN"},
                    "CREDIT_CARD": {"type": "replace", "new_value": "CARD"},
                }
            )
            
            # Calculate average confidence per entity type
            avg_confidence = {
                entity: sum(scores) / len(scores)
                for entity, scores in confidence_scores.items()
                if scores
            }
            
            return RedactionResult(
                redacted_text=anonymized.text,
                redaction_map=redaction_map,
                redaction_count=len(results),
                confidence_scores=avg_confidence
            )
            
        except Exception as e:
            logger.error(f"Presidio redaction failed: {e}. Falling back to regex.")
            return self._redact_with_regex(text)
    
    def _redact_with_regex(self, text: str) -> RedactionResult:
        """Fallback redaction using regex patterns."""
        redaction_map = {}
        redacted = text
        total_redactions = 0
        
        # Pattern: Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, redacted)
        if emails:
            redaction_map["EMAIL_ADDRESS"] = emails
            redacted = re.sub(email_pattern, "EMAIL", redacted)
            total_redactions += len(emails)
        
        # Pattern: Phone numbers (various formats)
        phone_pattern = r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'
        phones = re.findall(phone_pattern, redacted)
        if phones:
            redaction_map["PHONE_NUMBER"] = [f"{p[0]}-{p[1]}-{p[2]}" for p in phones]
            redacted = re.sub(phone_pattern, "PHONE", redacted)
            total_redactions += len(phones)
        
        # Pattern: URLs
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, redacted)
        if urls:
            redaction_map["URL"] = urls
            redacted = re.sub(url_pattern, "URL", redacted)
            total_redactions += len(urls)
        
        # Pattern: Common name patterns (capitalized words, but preserve technical terms)
        # This is conservative - only redacts obvious name patterns
        name_pattern = r'\b(Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        names = re.findall(name_pattern, redacted)
        if names:
            redaction_map["PERSON"] = [f"{title} {name}" for title, name in names]
            redacted = re.sub(name_pattern, r'\1 CANDIDATE', redacted)
            total_redactions += len(names)
        
        # Pattern: University names (common patterns)
        university_pattern = r'\b(University of [A-Z][a-z]+|[A-Z][a-z]+ University|MIT|Stanford|Harvard|Yale|Princeton)\b'
        universities = re.findall(university_pattern, redacted)
        if universities:
            redaction_map["ORG"] = universities
            redacted = re.sub(university_pattern, "UNIVERSITY", redacted)
            total_redactions += len(universities)
        
        # Pattern: Company names (ending with Inc, LLC, Corp, etc.)
        company_pattern = r'\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)\s+(Inc\.|LLC|Corp\.|Corporation|Ltd\.)\b'
        companies = re.findall(company_pattern, redacted)
        if companies:
            redaction_map["ORG"] = redaction_map.get("ORG", []) + [f"{name} {suffix}" for name, suffix in companies]
            redacted = re.sub(company_pattern, r'ORGANIZATION \2', redacted)
            total_redactions += len(companies)
        
        return RedactionResult(
            redacted_text=redacted,
            redaction_map=redaction_map,
            redaction_count=total_redactions,
            confidence_scores={}  # Regex doesn't provide confidence scores
        )
    
    def validate_redaction(self, original: str, redacted: str) -> Dict[str, any]:
        """
        Validate that redaction was successful and didn't remove critical content.
        
        Returns validation metrics.
        """
        original_words = set(original.lower().split())
        redacted_words = set(redacted.lower().split())
        
        # Calculate content preservation ratio
        preserved_words = original_words.intersection(redacted_words)
        preservation_ratio = len(preserved_words) / len(original_words) if original_words else 0
        
        # Check for placeholder presence
        placeholders = ["CANDIDATE", "EMAIL", "PHONE", "LOCATION", "ORGANIZATION", "URL"]
        placeholder_count = sum(redacted.count(p) for p in placeholders)
        
        return {
            "preservation_ratio": preservation_ratio,
            "original_word_count": len(original_words),
            "redacted_word_count": len(redacted_words),
            "placeholder_count": placeholder_count,
            "quality": "high" if preservation_ratio > 0.7 else "medium" if preservation_ratio > 0.5 else "low"
        }


# Singleton instance
_pii_service: Optional[PIIRedactionService] = None


def get_pii_service() -> PIIRedactionService:
    """Get or create singleton PII redaction service."""
    global _pii_service
    if _pii_service is None:
        _pii_service = PIIRedactionService()
    return _pii_service
