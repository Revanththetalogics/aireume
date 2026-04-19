"""
LLM-based contact information extractor for resumes.

Uses the existing Ollama/Gemma infrastructure to extract contact info
with high accuracy, handling any resume format, language, or layout.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:9b")

# Import Ollama Cloud authentication helper
from app.backend.services.llm_service import get_ollama_headers


async def extract_contact_with_llm(resume_text: str, timeout: float = 15.0) -> Optional[Dict[str, str]]:
    """
    Extract contact information from resume text using LLM.
    
    This is more accurate than regex for:
    - Non-standard name formats (all caps, lowercase, hyphenated, etc.)
    - International names (Indian, Chinese, Arabic, etc.)
    - Names with titles/suffixes (Dr., Jr., III, etc.)
    - Creative resume layouts
    
    Args:
        resume_text: First ~1000 chars of resume (header section)
        timeout: LLM call timeout in seconds
        
    Returns:
        Dict with keys: name, email, phone, linkedin (or None on failure)
    """
    logger.info("[LLM Contact Extractor] Starting extraction...")
    # Only use first 1000 characters (header section) to save tokens
    header = resume_text[:1000]
    logger.debug("[LLM Contact Extractor] Header text (first 200 chars): %s", header[:200])
    
    system_prompt = """You are a contact information extractor. Extract contact details from resume text and return ONLY valid JSON."""
    
    user_prompt = f"""Extract the candidate's contact information from this resume header.
Return ONLY a valid JSON object with these exact keys: name, email, phone, linkedin.
If a field is not found, use null for that field.

Rules:
- name: Full name as written (preserve capitalization, hyphens, apostrophes)
- email: Email address
- phone: Phone number (preserve formatting)
- linkedin: LinkedIn profile URL or username

Resume header:
{header}

JSON output:"""

    try:
        # Get authentication headers for Ollama Cloud
        headers = get_ollama_headers(OLLAMA_BASE_URL)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                headers=headers,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 200,
                    }
                }
            )
            response.raise_for_status()
            
            result = response.json()
            llm_output = result.get("message", {}).get("content", "").strip()
            logger.debug("[LLM Contact Extractor] Raw LLM output (first 300 chars): %s", llm_output[:300])
            
            # Try to parse JSON from LLM output
            # LLM might wrap JSON in markdown code blocks
            if "```json" in llm_output:
                llm_output = llm_output.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_output:
                llm_output = llm_output.split("```")[1].split("```")[0].strip()
            
            contact_info = json.loads(llm_output)
            logger.debug("[LLM Contact Extractor] Parsed contact_info: %s", contact_info)
            
            # Validate structure
            if not isinstance(contact_info, dict):
                logger.warning("LLM contact extraction returned non-dict: %s", type(contact_info))
                return None
            
            # Clean up null values
            cleaned = {}
            for key in ["name", "email", "phone", "linkedin"]:
                value = contact_info.get(key)
                if value and value != "null" and str(value).strip():
                    cleaned[key] = str(value).strip()
            
            if cleaned:
                logger.info("[LLM Contact Extractor] SUCCESS - Extracted: name=%s, email=%s, phone=%s", 
                           cleaned.get("name"), cleaned.get("email"), cleaned.get("phone"))
                return cleaned
            else:
                logger.warning("[LLM Contact Extractor] No valid fields extracted from LLM response")
            
            return None
            
    except json.JSONDecodeError as e:
        logger.warning("[LLM Contact Extractor] JSON parse error: %s | Output: %s", e, llm_output[:200])
        return None
    except httpx.TimeoutException:
        logger.warning("[LLM Contact Extractor] Timed out after %.1fs", timeout)
        return None
    except Exception as e:
        logger.warning("[LLM Contact Extractor] Failed: %s: %s", type(e).__name__, str(e)[:200])
        import traceback
        logger.debug("[LLM Contact Extractor] Traceback: %s", traceback.format_exc())
        return None


def merge_contact_info(regex_result: Dict[str, str], llm_result: Optional[Dict[str, str]]) -> Dict[str, str]:
    """
    Merge regex and LLM contact extraction results.
    
    Strategy:
    - Prefer LLM result for name (more accurate with edge cases)
    - Prefer regex for email/phone (faster, equally accurate for standard formats)
    - Use LLM as fallback if regex missed something
    
    Args:
        regex_result: Contact info from regex extraction
        llm_result: Contact info from LLM extraction (may be None)
        
    Returns:
        Merged contact info dict
    """
    merged = dict(regex_result)
    
    if llm_result:
        # Prefer LLM name if available (better with edge cases)
        if llm_result.get("name") and not merged.get("name"):
            merged["name"] = llm_result["name"]
        elif llm_result.get("name") and len(llm_result["name"]) > len(merged.get("name", "")):
            # Use LLM name if it's more complete
            merged["name"] = llm_result["name"]
        
        # Use LLM as fallback for missing fields
        for field in ["email", "phone", "linkedin"]:
            if llm_result.get(field) and not merged.get(field):
                merged[field] = llm_result[field]
    
    return merged
