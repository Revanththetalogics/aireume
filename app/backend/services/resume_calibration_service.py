"""
Resume Analysis Calibration & RAG Learning Service

Provides statistical insights from past resume analyses to improve LLM consistency.
Implements Retrieval-Augmented Generation (RAG) by injecting historical context
into LLM prompts for better calibration and pattern recognition.

Features:
- Role-specific calibration data (average scores, thresholds)
- Similar analysis retrieval for few-shot learning
- Common pattern extraction (strengths, red flags)
- Tenant-specific learning
"""
import logging
import json
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from collections import Counter
import re

logger = logging.getLogger(__name__)


def get_role_calibration(
    role_category: str,
    tenant_id: int,
    db: Session,
    min_samples: int = 5
) -> Dict[str, Any]:
    """
    Get calibration data for a specific role category.
    Returns statistical insights from past analyses.
    
    Args:
        role_category: Role category (technical, sales, hr, etc.)
        tenant_id: Tenant ID for tenant-specific calibration
        db: Database session
        min_samples: Minimum number of samples required for calibration
        
    Returns:
        Dictionary with calibration metrics
    """
    from app.backend.models.db_models import ScreeningResult
    
    try:
        # Query active screening results for this role category
        results = db.query(ScreeningResult).filter(
            and_(
                ScreeningResult.role_category == role_category,
                ScreeningResult.tenant_id == tenant_id,
                ScreeningResult.is_active == True,
                ScreeningResult.fit_score.isnot(None)
            )
        ).all()
        
        if len(results) < min_samples:
            logger.info(f"Insufficient data for {role_category}: {len(results)} samples (need {min_samples})")
            return get_default_calibration(role_category)
        
        # Extract fit scores
        fit_scores = [r.fit_score for r in results if r.fit_score is not None]
        
        if not fit_scores:
            return get_default_calibration(role_category)
        
        # Calculate statistics
        sorted_scores = sorted(fit_scores)
        avg_score = sum(fit_scores) / len(fit_scores)
        median_score = sorted_scores[len(sorted_scores) // 2]
        
        # Calculate percentiles for thresholds
        p75_idx = int(len(sorted_scores) * 0.75)
        p25_idx = int(len(sorted_scores) * 0.25)
        shortlist_threshold = sorted_scores[p75_idx] if p75_idx < len(sorted_scores) else 70
        reject_threshold = sorted_scores[p25_idx] if p25_idx < len(sorted_scores) else 45
        
        # Extract common patterns
        common_strengths = extract_common_patterns(results, "key_strengths", top_n=5)
        common_concerns = extract_common_patterns(results, "concerns", top_n=5)
        common_red_flags = extract_common_patterns(results, "red_flags", top_n=3)
        
        # Recommendation distribution
        rec_distribution = {
            "Shortlist": sum(1 for r in results if r.recommendation == "Shortlist"),
            "Consider": sum(1 for r in results if r.recommendation == "Consider"),
            "Reject": sum(1 for r in results if r.recommendation == "Reject")
        }
        
        calibration = {
            "role_category": role_category,
            "total_analyzed": len(results),
            "avg_fit_score": round(avg_score, 1),
            "median_fit_score": median_score,
            "shortlist_threshold": shortlist_threshold,
            "reject_threshold": reject_threshold,
            "common_strengths": common_strengths,
            "common_concerns": common_concerns,
            "common_red_flags": common_red_flags,
            "recommendation_distribution": rec_distribution,
            "has_sufficient_data": True
        }
        
        logger.info(f"Calibration for {role_category}: {len(results)} samples, avg={avg_score:.1f}")
        return calibration
        
    except Exception as e:
        logger.error(f"Error getting calibration for {role_category}: {e}")
        return get_default_calibration(role_category)


def get_default_calibration(role_category: str) -> Dict[str, Any]:
    """
    Return default calibration when no historical data exists.
    
    Args:
        role_category: Role category
        
    Returns:
        Default calibration dictionary
    """
    return {
        "role_category": role_category,
        "total_analyzed": 0,
        "avg_fit_score": None,
        "median_fit_score": None,
        "shortlist_threshold": 70,  # Default threshold
        "reject_threshold": 45,     # Default threshold
        "common_strengths": [],
        "common_concerns": [],
        "common_red_flags": [],
        "recommendation_distribution": {},
        "has_sufficient_data": False
    }


def extract_common_patterns(
    results: List[Any],
    field: str,
    top_n: int = 5
) -> List[str]:
    """
    Extract most common patterns from a field across results.
    
    Args:
        results: List of ScreeningResult objects
        field: Field name to extract (key_strengths, concerns, red_flags)
        top_n: Number of top patterns to return
        
    Returns:
        List of most common patterns
    """
    all_items = []
    
    for result in results:
        try:
            # Parse analysis_json if it exists
            if result.analysis_json:
                data = json.loads(result.analysis_json) if isinstance(result.analysis_json, str) else result.analysis_json
                items = data.get(field, [])
                
                if isinstance(items, list):
                    # Clean and normalize items
                    for item in items:
                        if isinstance(item, str):
                            cleaned = clean_pattern(item)
                            if cleaned:
                                all_items.append(cleaned)
        except Exception as e:
            logger.debug(f"Error extracting {field}: {e}")
            continue
    
    if not all_items:
        return []
    
    # Count occurrences
    counter = Counter(all_items)
    
    # Return top N most common
    return [item for item, count in counter.most_common(top_n)]


def clean_pattern(text: str) -> str:
    """
    Clean and normalize a pattern string.
    
    Args:
        text: Raw pattern text
        
    Returns:
        Cleaned pattern text
    """
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Truncate very long patterns
    if len(text) > 100:
        text = text[:97] + "..."
    
    return text.strip()


def get_similar_analyses(
    jd_text: str,
    role_category: str,
    tenant_id: int,
    db: Session,
    limit: int = 3,
    min_similarity: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Retrieve similar past analyses for RAG context.
    Uses keyword-based similarity (can be upgraded to embeddings later).
    
    Args:
        jd_text: Job description text
        role_category: Role category
        tenant_id: Tenant ID
        db: Database session
        limit: Maximum number of similar analyses to return
        min_similarity: Minimum similarity threshold (0-1)
        
    Returns:
        List of similar analysis summaries
    """
    from app.backend.models.db_models import ScreeningResult
    
    try:
        # Extract key terms from JD
        key_terms = extract_key_terms(jd_text)
        
        if not key_terms:
            logger.debug("No key terms extracted from JD")
            return []
        
        # Query recent analyses in same category
        results = db.query(ScreeningResult).filter(
            and_(
                ScreeningResult.role_category == role_category,
                ScreeningResult.tenant_id == tenant_id,
                ScreeningResult.is_active == True,
                ScreeningResult.jd_text.isnot(None),
                ScreeningResult.fit_score.isnot(None)
            )
        ).order_by(ScreeningResult.created_at.desc()).limit(50).all()
        
        if not results:
            return []
        
        # Calculate similarity for each result
        scored_results = []
        for result in results:
            if not result.jd_text:
                continue
                
            similarity = calculate_jd_similarity(jd_text, result.jd_text, key_terms)
            
            if similarity >= min_similarity:
                scored_results.append((similarity, result))
        
        # Sort by similarity and take top N
        scored_results.sort(reverse=True, key=lambda x: x[0])
        
        # Format results
        similar_analyses = []
        for similarity, result in scored_results[:limit]:
            try:
                # Parse analysis JSON
                analysis_data = {}
                if result.analysis_json:
                    analysis_data = json.loads(result.analysis_json) if isinstance(result.analysis_json, str) else result.analysis_json
                
                similar_analyses.append({
                    "fit_score": result.fit_score,
                    "recommendation": result.recommendation or "Consider",
                    "key_strengths": analysis_data.get("key_strengths", [])[:3],
                    "concerns": analysis_data.get("concerns", [])[:2],
                    "similarity": round(similarity, 2)
                })
            except Exception as e:
                logger.debug(f"Error formatting similar analysis: {e}")
                continue
        
        logger.info(f"Found {len(similar_analyses)} similar analyses for {role_category}")
        return similar_analyses
        
    except Exception as e:
        logger.error(f"Error retrieving similar analyses: {e}")
        return []


def extract_key_terms(text: str, max_terms: int = 20) -> set:
    """
    Extract important keywords from text.
    Simple implementation - can be upgraded to NLP later.
    
    Args:
        text: Input text
        max_terms: Maximum number of terms to extract
        
    Returns:
        Set of key terms
    """
    # Convert to lowercase
    text = text.lower()
    
    # Extract words (alphanumeric, 3+ chars)
    words = re.findall(r'\b[a-z0-9]{3,}\b', text)
    
    # Common stopwords to filter
    stopwords = {
        'the', 'and', 'for', 'with', 'have', 'will', 'this', 'that',
        'from', 'they', 'been', 'were', 'are', 'has', 'had', 'but',
        'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out',
        'day', 'get', 'may', 'use', 'who', 'him', 'how', 'man', 'new',
        'now', 'old', 'see', 'two', 'way', 'she', 'did', 'its', 'let',
        'put', 'say', 'too', 'any'
    }
    
    # Filter stopwords and get unique terms
    terms = set(w for w in words if w not in stopwords)
    
    # Limit to max_terms most common
    if len(terms) > max_terms:
        # Simple frequency-based selection
        word_freq = Counter(w for w in words if w in terms)
        terms = set(word for word, _ in word_freq.most_common(max_terms))
    
    return terms


def calculate_jd_similarity(jd1: str, jd2: str, key_terms: set) -> float:
    """
    Calculate similarity between two job descriptions.
    Uses Jaccard similarity on key terms.
    
    Args:
        jd1: First job description
        jd2: Second job description
        key_terms: Pre-extracted key terms from jd1
        
    Returns:
        Similarity score (0-1)
    """
    # Extract terms from second JD
    terms2 = extract_key_terms(jd2)
    
    if not key_terms or not terms2:
        return 0.0
    
    # Jaccard similarity: intersection / union
    intersection = len(key_terms & terms2)
    union = len(key_terms | terms2)
    
    return intersection / union if union > 0 else 0.0


def format_calibration_context(calibration: Dict[str, Any]) -> str:
    """
    Format calibration data into LLM prompt context.
    
    Args:
        calibration: Calibration dictionary
        
    Returns:
        Formatted context string for LLM prompt
    """
    if not calibration.get("has_sufficient_data"):
        return ""
    
    context = f"""
CALIBRATION DATA (based on {calibration['total_analyzed']} past {calibration['role_category']} analyses):
- Average fit score: {calibration['avg_fit_score']}
- Typical shortlist threshold: {calibration['shortlist_threshold']}+
- Typical reject threshold: Below {calibration['reject_threshold']}"""
    
    if calibration.get("common_strengths"):
        context += f"\n- Common strengths in successful candidates: {', '.join(calibration['common_strengths'][:3])}"
    
    if calibration.get("common_concerns"):
        context += f"\n- Common concerns to watch for: {', '.join(calibration['common_concerns'][:3])}"
    
    if calibration.get("common_red_flags"):
        context += f"\n- Common red flags: {', '.join(calibration['common_red_flags'][:2])}"
    
    return context


def format_similar_analyses_context(similar_analyses: List[Dict[str, Any]]) -> str:
    """
    Format similar analyses into LLM prompt context.
    
    Args:
        similar_analyses: List of similar analysis summaries
        
    Returns:
        Formatted context string for LLM prompt
    """
    if not similar_analyses:
        return ""
    
    context = "\nSIMILAR PAST ANALYSES FOR REFERENCE:\n"
    
    for i, analysis in enumerate(similar_analyses, 1):
        context += f"""
{i}. Fit Score: {analysis['fit_score']} | {analysis['recommendation']}
   Strengths: {', '.join(analysis['key_strengths']) if analysis['key_strengths'] else 'N/A'}
   Concerns: {', '.join(analysis['concerns']) if analysis['concerns'] else 'N/A'}"""
    
    return context
