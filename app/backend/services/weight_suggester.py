"""
LLM Weight Suggester Service

Analyzes job descriptions and suggests optimal scoring weights based on:
- Role category detection (technical/sales/hr/marketing/operations/leadership)
- Seniority level analysis
- Key requirements identification
- Company culture signals

Provides intelligent, context-aware weight recommendations with reasoning.
"""

import json
import logging
from typing import Dict, Optional, Any
from langchain_ollama import ChatOllama
from app.backend.services.weight_mapper import NEW_DEFAULT_WEIGHTS, normalize_weights
import os

log = logging.getLogger(__name__)


# ─── LLM Configuration ────────────────────────────────────────────────────────

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
# Use same model as main application (gemma4:31b-cloud for Ollama Cloud)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")

def _get_llm() -> ChatOllama:
    """Get LLM instance for weight suggestion"""
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        format="json",
        num_predict=800,
        num_ctx=4096,
        request_timeout=60.0,
    )


# ─── LLM Prompt for Weight Suggestion ────────────────────────────────────────

WEIGHT_SUGGESTER_PROMPT = """Analyze this job description and suggest optimal scoring weights for candidate evaluation.

JOB DESCRIPTION:
{jd_text}

TASK:
1. Detect the role category (technical/sales/hr/marketing/operations/leadership/other)
2. Identify seniority level (junior/mid/senior/lead/executive)
3. Determine key success factors for this role
4. Suggest optimal scoring weights

OUTPUT VALID JSON ONLY (no markdown, no explanation outside JSON):
{{
  "role_category": "technical|sales|hr|marketing|operations|leadership|other",
  "seniority_level": "junior|mid|senior|lead|executive",
  "key_requirements": ["requirement1", "requirement2", "requirement3"],
  "suggested_weights": {{
    "core_competencies": 0.25-0.40,
    "experience": 0.15-0.30,
    "domain_fit": 0.15-0.25,
    "education": 0.05-0.15,
    "career_trajectory": 0.10-0.15,
    "role_excellence": 0.10-0.20,
    "risk": -0.05 to -0.15
  }},
  "weight_evidence": {{
    "core_competencies": ["Verbatim JD phrase justifying this weight"],
    "experience": ["Verbatim JD phrase justifying this weight"],
    "domain_fit": ["Verbatim JD phrase justifying this weight"],
    "education": ["Verbatim JD phrase justifying this weight"],
    "career_trajectory": ["Verbatim JD phrase justifying this weight"],
    "role_excellence": ["Verbatim JD phrase justifying this weight"],
    "risk": ["Verbatim JD phrase justifying this weight"]
  }},
  "weight_delta_reasons": {{
    "core_competencies": "Why this differs from default (1 sentence)",
    "experience": "Why this differs from default (1 sentence)",
    "domain_fit": "Why this differs from default (1 sentence)",
    "education": "Why this differs from default (1 sentence)",
    "career_trajectory": "Why this differs from default (1 sentence)",
    "role_excellence": "Why this differs from default (1 sentence)",
    "risk": "Why this differs from default (1 sentence)"
  }},
  "role_excellence_label": "What this measures for this specific role",
  "reasoning": "Brief explanation of why these weights (2-3 sentences)",
  "confidence": 0.0-1.0
}}

GUIDELINES:
- Weights must sum to 1.0 (excluding negative risk penalty)
- Junior roles: Higher education/skills, lower experience
- Senior roles: Higher experience/role_excellence, lower education
- Technical roles: Higher role_excellence (architecture/design)
- Sales roles: Higher core_competencies, role_excellence = revenue achievement
- HR roles: Higher education (certifications), role_excellence = strategic impact
- Startup culture: Lower career_trajectory (job hopping OK)
- Enterprise culture: Higher career_trajectory (stability valued)
- weight_evidence: Use VERBATIM phrases from the JD (exact words) to justify each weight. Never paraphrase.
- weight_delta_reasons: Compare your suggested weight to the default (Core Comp 30%, Exp 20%, Domain 20%, Edu 10%, Career 10%, Role Excel 10%, Risk -10%). Explain WHY you changed it in one sentence per dimension. If you kept it the same, say "Aligned with default — [reason]".
"""


def suggest_weights_for_jd(jd_text: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    Analyze job description and suggest optimal scoring weights using LLM.
    
    Args:
        jd_text: Job description text
        timeout: LLM timeout in seconds

    Returns:
        Dictionary containing:
        - role_category: Detected role type
        - seniority_level: Detected seniority
        - suggested_weights: Optimal weights for this role
        - role_excellence_label: Adaptive label for role_excellence factor
        - reasoning: Explanation for the suggestions
        - confidence: Confidence score (0.0-1.0)

        Returns None if LLM fails or returns invalid data
    """
    if not jd_text or len(jd_text.strip()) < 50:
        log.warning("JD text too short for weight suggestion, using defaults")
        return None
    
    try:
        llm = _get_llm()
        prompt = WEIGHT_SUGGESTER_PROMPT.format(jd_text=jd_text[:3000])  # Limit JD length
        
        log.info("Requesting weight suggestions from LLM")
        response = llm.invoke(prompt).content
        
        if not response or not response.strip():
            log.warning("Empty response from LLM for weight suggestion")
            return None
        
        # Parse JSON response
        try:
            result = json.loads(response.strip())
        except json.JSONDecodeError as e:
            log.warning(f"Failed to parse LLM weight suggestion as JSON: {e}")
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                if json_end > json_start:
                    try:
                        result = json.loads(response[json_start:json_end].strip())
                    except json.JSONDecodeError:
                        return None
                else:
                    return None
            else:
                return None
        
        # Validate required fields
        required_fields = ["role_category", "suggested_weights", "reasoning"]
        if not all(field in result for field in required_fields):
            log.warning(f"LLM response missing required fields: {result}")
            return None
        
        # Validate and normalize weights
        suggested_weights = result.get("suggested_weights", {})
        if not isinstance(suggested_weights, dict):
            log.warning("suggested_weights is not a dictionary")
            return None
        
        # Ensure all required weight keys are present
        required_weight_keys = ["core_competencies", "experience", "domain_fit", 
                                "education", "career_trajectory", "role_excellence", "risk"]
        
        for key in required_weight_keys:
            if key not in suggested_weights:
                log.warning(f"Missing weight key: {key}, using default")
                suggested_weights[key] = NEW_DEFAULT_WEIGHTS.get(key, 0.10)
        
        # Normalize weights to ensure they sum to 1.0
        normalized_weights = normalize_weights(suggested_weights)
        result["suggested_weights"] = normalized_weights
        
        # Set defaults for optional fields
        result.setdefault("seniority_level", "unknown")
        result.setdefault("key_requirements", [])
        result.setdefault("role_excellence_label", "Role-Specific Excellence")
        result.setdefault("confidence", 0.75)
        
        # Ensure weight_evidence and weight_delta_reasons exist with defaults
        result.setdefault("weight_evidence", {})
        result.setdefault("weight_delta_reasons", {})
        for key in required_weight_keys:
            if key not in result["weight_evidence"]:
                result["weight_evidence"][key] = []
            if key not in result["weight_delta_reasons"]:
                result["weight_delta_reasons"][key] = ""
        
        log.info(f"Weight suggestion successful: {result['role_category']} role, "
                f"confidence: {result['confidence']}")
        
        return result
        
    except Exception as e:
        log.exception(f"Error getting weight suggestions from LLM: {e}")
        return None


def get_default_weights_for_category(role_category: str) -> Dict[str, float]:
    """
    Get sensible default weights for a role category when LLM is unavailable.
    
    Args:
        role_category: Role type (technical/sales/hr/marketing/etc)
        
    Returns:
        Dictionary of default weights for this category
    """
    defaults = {
        "technical": {
            "core_competencies": 0.30,
            "experience": 0.20,
            "domain_fit": 0.20,
            "education": 0.05,
            "career_trajectory": 0.10,
            "role_excellence": 0.15,  # Architecture/design
            "risk": -0.10,
        },
        "sales": {
            "core_competencies": 0.35,
            "experience": 0.25,
            "domain_fit": 0.15,
            "education": 0.05,
            "career_trajectory": 0.10,
            "role_excellence": 0.10,  # Revenue achievement
            "risk": -0.10,
        },
        "hr": {
            "core_competencies": 0.30,
            "experience": 0.25,
            "domain_fit": 0.15,
            "education": 0.10,  # Certifications matter
            "career_trajectory": 0.15,
            "role_excellence": 0.05,  # Strategic impact
            "risk": -0.10,
        },
        "marketing": {
            "core_competencies": 0.35,
            "experience": 0.20,
            "domain_fit": 0.20,
            "education": 0.05,
            "career_trajectory": 0.10,
            "role_excellence": 0.10,  # Campaign strategy
            "risk": -0.10,
        },
        "operations": {
            "core_competencies": 0.30,
            "experience": 0.25,
            "domain_fit": 0.15,
            "education": 0.10,
            "career_trajectory": 0.15,
            "role_excellence": 0.05,  # Process optimization
            "risk": -0.10,
        },
        "leadership": {
            "core_competencies": 0.25,
            "experience": 0.30,  # Experience critical
            "domain_fit": 0.20,
            "education": 0.05,
            "career_trajectory": 0.10,
            "role_excellence": 0.10,  # Strategic vision
            "risk": -0.10,
        },
    }
    
    return defaults.get(role_category.lower(), NEW_DEFAULT_WEIGHTS.copy())


def get_role_excellence_label(role_category: str) -> str:
    """
    Get the appropriate label for role_excellence factor based on role category.
    
    Args:
        role_category: Role type
        
    Returns:
        Human-readable label for role_excellence
    """
    labels = {
        "technical": "System Design & Architecture",
        "sales": "Revenue Achievement & Quota Attainment",
        "hr": "Strategic HR Impact & Culture Building",
        "marketing": "Campaign Strategy & Brand Impact",
        "operations": "Process Optimization & Efficiency",
        "leadership": "Strategic Vision & Leadership Impact",
    }
    
    return labels.get(role_category.lower(), "Role-Specific Excellence")


def create_fallback_suggestion(jd_text: str, role_category: str = "technical") -> Dict[str, Any]:
    """
    Create a fallback weight suggestion when LLM is unavailable.
    
    Args:
        jd_text: Job description text (for basic analysis)
        role_category: Assumed role category
        
    Returns:
        Basic weight suggestion with defaults
    """
    # Simple keyword-based role detection
    jd_lower = jd_text.lower()
    
    if any(word in jd_lower for word in ["engineer", "developer", "architect", "devops", "backend", "frontend"]):
        detected_category = "technical"
    elif any(word in jd_lower for word in ["sales", "account executive", "bdr", "revenue"]):
        detected_category = "sales"
    elif any(word in jd_lower for word in ["hr", "human resources", "recruiter", "talent"]):
        detected_category = "hr"
    elif any(word in jd_lower for word in ["marketing", "brand", "campaign", "growth"]):
        detected_category = "marketing"
    else:
        detected_category = role_category
    
    return {
        "role_category": detected_category,
        "seniority_level": "unknown",
        "key_requirements": [],
        "suggested_weights": get_default_weights_for_category(detected_category),
        "weight_evidence": {},
        "weight_delta_reasons": {},
        "role_excellence_label": get_role_excellence_label(detected_category),
        "reasoning": f"Using default weights for {detected_category} role (LLM unavailable)",
        "confidence": 0.50,
        "fallback": True,
    }
