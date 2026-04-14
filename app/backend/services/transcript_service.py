"""
Transcript analysis service.
Supports plain .txt, WebVTT (.vtt from Zoom/Teams), and .srt subtitle formats.
Parses the transcript to clean text, then asks the LLM for an unbiased
evaluation of the candidate against the provided job description.
"""
import json
import re
import os
import httpx
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.backend.services.llm_service import get_ollama_semaphore, get_ollama_headers
from app.backend.services.pii_redaction_service import get_pii_service
from app.backend.services.evidence_validation_service import get_evidence_service

logger = logging.getLogger(__name__)


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")


def _is_ollama_cloud_local(base_url: str) -> bool:
    """Check if the base URL points to Ollama Cloud (ollama.com)."""
    return "ollama.com" in base_url.lower()


# ─── Transcript parsers ───────────────────────────────────────────────────────

def _parse_vtt(text: str) -> str:
    """Strip WebVTT headers, cue timestamps, and speaker labels."""
    lines: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        # Skip file header and NOTE blocks
        if line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("STYLE"):
            continue
        # Skip cue timings  e.g. "00:00:01.000 --> 00:00:05.000"
        if re.match(r'^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->', line):
            continue
        # Skip numeric cue IDs
        if re.match(r'^\d+$', line):
            continue
        # Strip speaker labels like "John Doe: " or "[John]: "
        line = re.sub(r'^[\[\(]?[A-Za-z ]+[\]\)]?\s*:', '', line).strip()
        if line:
            lines.append(line)
    return " ".join(lines)


def _parse_srt(text: str) -> str:
    """Strip SRT sequence numbers, timestamps, and speaker labels."""
    lines: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r'^\d+$', line):
            continue
        if re.match(r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->', line):
            continue
        # Strip HTML tags sometimes present in SRT
        line = re.sub(r'<[^>]+>', '', line)
        # Strip speaker labels
        line = re.sub(r'^[\[\(]?[A-Za-z ]+[\]\)]?\s*:', '', line).strip()
        if line:
            lines.append(line)
    return " ".join(lines)


def parse_transcript(raw_text: str, filename: str = "") -> str:
    """
    Auto-detect format from filename extension and return clean plain text
    suitable for LLM analysis.
    """
    ext = Path(filename).suffix.lower() if filename else ""
    if ext == ".vtt":
        return _parse_vtt(raw_text)
    if ext == ".srt":
        return _parse_srt(raw_text)
    # Plain text — still strip any leading speaker labels per line
    lines = []
    for line in raw_text.splitlines():
        line = re.sub(r'^[\[\(]?[A-Za-z ]+[\]\)]?\s*:', '', line).strip()
        if line:
            lines.append(line)
    return " ".join(lines) if lines else raw_text.strip()


# ─── LLM analysis ─────────────────────────────────────────────────────────────

def _build_transcript_prompt(
    transcript: str,
    jd_text: str,
    candidate_name: str,
) -> str:
    jd_summary = jd_text[:600] if len(jd_text) > 600 else jd_text
    transcript_summary = transcript[:3000] if len(transcript) > 3000 else transcript

    return f"""You are a fair and unbiased hiring analyst. Evaluate ONLY the content, skills, and knowledge demonstrated in this interview transcript.

CRITICAL REQUIREMENTS:
1. Every strength MUST include a direct quote from the transcript as evidence
2. Every JD alignment item MUST cite specific transcript evidence
3. If you cannot find evidence for a requirement, mark demonstrated=false
4. Do NOT infer skills not explicitly discussed
5. Do NOT make assumptions based on candidate background
6. All evidence quotes must be EXACT quotes from the transcript

JOB DESCRIPTION:
{jd_summary}

INTERVIEW TRANSCRIPT:
{transcript_summary}

Return ONLY valid JSON with this exact structure:
{{
  "fit_score": <integer 0-100>,
  "technical_depth": <integer 0-100>,
  "communication_quality": <integer 0-100>,
  "jd_alignment": [
    {{
      "requirement": "<JD requirement>",
      "demonstrated": true/false,
      "evidence": "<exact quote from transcript or null>",
      "confidence": "<high|medium|low>"
    }}
  ],
  "strengths": [
    {{
      "strength": "<identified strength>",
      "evidence": "<exact quote supporting this strength>"
    }}
  ],
  "areas_for_improvement": [
    {{
      "area": "<improvement area>",
      "reason": "<why this is an area for improvement>",
      "evidence": "<quote showing gap or null>"
    }}
  ],
  "red_flags": [
    {{
      "flag": "<concerning statement or behavior>",
      "evidence": "<exact quote>",
      "severity": "<high|medium|low>"
    }}
  ],
  "bias_note": "Evaluation based solely on demonstrated skills and knowledge in the transcript.",
  "recommendation": "<proceed|hold|reject>",
  "recommendation_rationale": "<2-3 sentence explanation citing specific evidence>"
}}

JSON:"""


def _parse_json_response(raw: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    for pattern in [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
        r'(\{.*\})',
    ]:
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    return None


def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
    fit_score           = max(0, min(100, int(data.get("fit_score", 50))))
    technical_depth     = max(0, min(100, int(data.get("technical_depth", 50))))
    communication_quality = max(0, min(100, int(data.get("communication_quality", 50))))

    # Normalize JD alignment with confidence
    jd_alignment = [
        {
            "requirement":  item.get("requirement", ""),
            "demonstrated": bool(item.get("demonstrated", False)),
            "evidence":     item.get("evidence"),
            "confidence":   item.get("confidence", "medium"),
        }
        for item in data.get("jd_alignment", [])
    ]

    # Normalize strengths (support both old and new format)
    raw_strengths = data.get("strengths", [])
    strengths = []
    for s in raw_strengths:
        if isinstance(s, dict):
            strengths.append(s)
        elif isinstance(s, str) and s:
            # Old format - convert to new format
            strengths.append({"strength": s, "evidence": None})
    strengths = strengths[:6]

    # Normalize areas for improvement
    raw_areas = data.get("areas_for_improvement", [])
    areas = []
    for a in raw_areas:
        if isinstance(a, dict):
            areas.append(a)
        elif isinstance(a, str) and a:
            # Old format - convert to new format
            areas.append({"area": a, "reason": None, "evidence": None})
    areas = areas[:4]

    # Normalize red flags
    red_flags = [
        {
            "flag": item.get("flag", ""),
            "evidence": item.get("evidence"),
            "severity": item.get("severity", "medium"),
        }
        for item in data.get("red_flags", [])
    ][:5]  # Max 5 red flags

    rec = data.get("recommendation", "hold").lower()
    if rec not in ("proceed", "hold", "reject"):
        rec = "hold"

    return {
        "fit_score":            fit_score,
        "technical_depth":      technical_depth,
        "communication_quality": communication_quality,
        "jd_alignment":         jd_alignment,
        "strengths":            strengths,
        "areas_for_improvement": areas,
        "red_flags":            red_flags,
        "bias_note":            data.get(
            "bias_note",
            "Evaluation based solely on demonstrated skills and knowledge in the transcript."
        ),
        "recommendation":       rec,
        "recommendation_rationale": data.get("recommendation_rationale", ""),
    }


def _fallback_result() -> Dict[str, Any]:
    return {
        "fit_score":            50,
        "technical_depth":      50,
        "communication_quality": 50,
        "jd_alignment":         [],
        "strengths":            [{"strength": "Analysis temporarily unavailable", "evidence": None}],
        "areas_for_improvement": [{"area": "Could not complete detailed analysis", "reason": None, "evidence": None}],
        "red_flags":            [],
        "bias_note":            "Evaluation based solely on demonstrated skills and knowledge in the transcript.",
        "recommendation":       "hold",
        "recommendation_rationale": "Analysis could not be completed.",
        "pii_redacted":         False,
        "evidence_quality_score": 0,
    }


async def analyze_transcript(
    transcript: str,
    jd_text: str,
    candidate_name: str = "",
    enable_pii_redaction: bool = True,
    enable_evidence_validation: bool = True,
) -> Dict[str, Any]:
    """
    Enterprise-grade transcript analysis with PII redaction and evidence validation.
    
    Args:
        transcript: Cleaned transcript text
        jd_text: Job description
        candidate_name: Candidate name (will be redacted if PII redaction enabled)
        enable_pii_redaction: Redact PII before analysis (default: True)
        enable_evidence_validation: Validate evidence citations (default: True)
        
    Returns:
        Analysis result with scores, evidence, and validation metrics
    """
    if not transcript or len(transcript) < 30:
        return _fallback_result()

    original_transcript = transcript
    redaction_result = None
    
    # Step 1: PII Redaction
    if enable_pii_redaction:
        try:
            pii_service = get_pii_service()
            redaction_result = pii_service.redact_pii(transcript)
            transcript = redaction_result.redacted_text
            candidate_name = "CANDIDATE"  # Always use generic name after redaction
            logger.info(f"PII redaction: {redaction_result.redaction_count} entities redacted")
        except Exception as e:
            logger.warning(f"PII redaction failed: {e}. Proceeding without redaction.")
    
    # Step 2: LLM Analysis
    prompt = _build_transcript_prompt(transcript, jd_text, candidate_name)

    try:
        sem = get_ollama_semaphore()
        if sem.locked():
            logger.info("Waiting for Ollama slot (another request in progress)...")
        async with sem:
            headers = get_ollama_headers(OLLAMA_BASE_URL)
            # Cloud models need more tokens for structured output with evidence
            _is_cloud = _is_ollama_cloud_local(OLLAMA_BASE_URL)
            _num_predict = 2000 if _is_cloud else 1000  # Increased for evidence citations
            async with httpx.AsyncClient(timeout=120.0) as client:  # Increased timeout
                resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    headers=headers,
                    json={
                        "model":   OLLAMA_MODEL,
                        "prompt":  prompt,
                        "stream":  False,
                        "format":  "json",
                        "options": {"num_predict": _num_predict, "temperature": 0.1},
                    },
                )
                resp.raise_for_status()
                raw = resp.json().get("response", "{}")
                parsed = _parse_json_response(raw)
                if parsed:
                    result = _normalize(parsed)
                    
                    # Step 3: Evidence Validation
                    if enable_evidence_validation:
                        try:
                            evidence_service = get_evidence_service()
                            validation_report = evidence_service.validate_analysis_result(
                                result, transcript
                            )
                            
                            # Add validation metrics to result
                            result["evidence_validation"] = {
                                "total_claims": validation_report.total_claims,
                                "verified_claims": validation_report.verified_claims,
                                "hallucinated_claims": validation_report.hallucinated_claims,
                                "fuzzy_matches": validation_report.fuzzy_matches,
                                "unsupported_claims": validation_report.unsupported_claims[:3],  # First 3
                            }
                            result["evidence_quality_score"] = validation_report.evidence_quality_score
                            
                            logger.info(
                                f"Evidence validation: {validation_report.verified_claims}/{validation_report.total_claims} "
                                f"claims verified (score: {validation_report.evidence_quality_score:.1f})"
                            )
                        except Exception as e:
                            logger.warning(f"Evidence validation failed: {e}")
                            result["evidence_quality_score"] = 0
                    
                    # Add PII redaction metadata
                    if redaction_result:
                        result["pii_redacted"] = True
                        result["pii_redaction_count"] = redaction_result.redaction_count
                        result["bias_note"] = (
                            "Evaluation performed on anonymized transcript with all identifying "
                            "information redacted. Assessment based purely on demonstrated skills and knowledge."
                        )
                    else:
                        result["pii_redacted"] = False
                    
                    return result
    except Exception as e:
        logger.error(f"Transcript analysis failed: {e}")

    return _fallback_result()
