"""
LLM-based contact information extractor for resumes.

Uses Gemini (when configured) with Ollama fallback.
"""

import logging
from typing import Dict, Optional

from app.backend.services.app_llm_client import generate_app_json

logger = logging.getLogger(__name__)


async def extract_contact_with_llm(resume_text: str, timeout: float = 15.0) -> Optional[Dict[str, str]]:
    """
    Extract contact information from resume text using LLM.

    Returns dict with keys: name, email, phone, linkedin (or None on failure).
    """
    logger.info("[LLM Contact Extractor] Starting extraction...")
    header = resume_text[:1000]
    logger.info("[LLM Contact Extractor] Header text (first 200 chars): %s", header[:200])

    system_prompt = (
        "You are a contact information extractor. Extract ONLY the candidate's personal "
        "contact details from resume text and return ONLY valid JSON. Be precise and conservative."
    )

    user_prompt = f"""Extract the candidate's contact information from this resume header.
Return ONLY a valid JSON object with these exact keys: name, email, phone, linkedin.
If a field is not found, use null for that field.

CRITICAL RULES:
- name: Full name of the person (e.g., "John Smith", "Priya Patel", "Jean-Luc Dubois"). Do NOT extract company names, job titles, or section headers like "Domain" or "Experience".
- email: Valid email address containing @ symbol (e.g., "john@email.com")
- phone: Phone number with digits, optionally with +, -, spaces, or parentheses. Must look like a real phone number (e.g., "+1-555-123-4567", "(555) 123-4567"). Do NOT extract years like "2008" or "2020".
- linkedin: LinkedIn profile URL or username (e.g., "linkedin.com/in/johnsmith" or "@johnsmith")

Resume header:
{header}

JSON output:"""

    try:
        contact_info = await generate_app_json(
            user_prompt,
            system=system_prompt,
            max_output_tokens=200,
            temperature=0.1,
            timeout=timeout,
            log_label="contact_extractor",
        )
        if not contact_info:
            logger.warning("[LLM Contact Extractor] No response from LLM")
            return None

        logger.info("[LLM Contact Extractor] Parsed contact_info: %s", contact_info)

        if not isinstance(contact_info, dict):
            logger.warning("LLM contact extraction returned non-dict: %s", type(contact_info))
            return None

        cleaned = {}
        for key in ["name", "email", "phone", "linkedin"]:
            value = contact_info.get(key)
            if value and value != "null" and str(value).strip():
                cleaned[key] = str(value).strip()

        if cleaned:
            logger.info(
                "[LLM Contact Extractor] SUCCESS - Extracted: name=%s, email=%s, phone=%s",
                cleaned.get("name"),
                cleaned.get("email"),
                cleaned.get("phone"),
            )
            return cleaned

        logger.warning("[LLM Contact Extractor] No valid fields extracted from LLM response")
        return None

    except Exception as e:
        logger.warning("[LLM Contact Extractor] Failed: %s: %s", type(e).__name__, str(e)[:200])
        return None


def merge_contact_info(regex_result: Dict[str, str], llm_result: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Merge regex and LLM contact extraction results."""
    merged = dict(regex_result)

    if llm_result:
        if llm_result.get("name") and not merged.get("name"):
            merged["name"] = llm_result["name"]
        elif llm_result.get("name") and len(llm_result["name"]) > len(merged.get("name", "")):
            merged["name"] = llm_result["name"]

        for field in ["email", "phone", "linkedin"]:
            if llm_result.get(field) and not merged.get(field):
                merged[field] = llm_result[field]

    return merged
