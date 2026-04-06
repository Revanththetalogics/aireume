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
from pathlib import Path
from typing import Dict, Any, List, Optional


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")


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

    return f"""You are a fair and unbiased hiring analyst. Evaluate ONLY the content, skills, and knowledge demonstrated in this interview transcript — do NOT consider names, accents, speech style, or any demographic factors.

JOB DESCRIPTION:
{jd_summary}

INTERVIEW TRANSCRIPT (candidate: {candidate_name or 'Unknown'}):
{transcript_summary}

Analyze the candidate's answers strictly on merit against the job description.

Return ONLY valid JSON with this exact structure:
{{
  "fit_score": <integer 0-100>,
  "technical_depth": <integer 0-100>,
  "communication_quality": <integer 0-100>,
  "jd_alignment": [
    {{"requirement": "<JD requirement>", "demonstrated": true/false, "evidence": "<brief quote or null>"}}
  ],
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "areas_for_improvement": ["<area 1>", "<area 2>"],
  "bias_note": "Evaluation based solely on demonstrated skills and knowledge in the transcript.",
  "recommendation": "<proceed|hold|reject>"
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

    jd_alignment = [
        {
            "requirement":  item.get("requirement", ""),
            "demonstrated": bool(item.get("demonstrated", False)),
            "evidence":     item.get("evidence"),
        }
        for item in data.get("jd_alignment", [])
    ]

    strengths = [s for s in data.get("strengths", []) if s][:6]
    areas     = [a for a in data.get("areas_for_improvement", []) if a][:4]

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
        "bias_note":            data.get(
            "bias_note",
            "Evaluation based solely on demonstrated skills and knowledge in the transcript."
        ),
        "recommendation":       rec,
    }


def _fallback_result() -> Dict[str, Any]:
    return {
        "fit_score":            50,
        "technical_depth":      50,
        "communication_quality": 50,
        "jd_alignment":         [],
        "strengths":            ["Analysis temporarily unavailable"],
        "areas_for_improvement": ["Could not complete detailed analysis"],
        "bias_note":            "Evaluation based solely on demonstrated skills and knowledge in the transcript.",
        "recommendation":       "hold",
    }


async def analyze_transcript(
    transcript: str,
    jd_text: str,
    candidate_name: str = "",
) -> Dict[str, Any]:
    """
    Send the cleaned transcript + job description to Ollama and return a
    structured, unbiased analysis result dict.
    """
    if not transcript or len(transcript) < 30:
        return _fallback_result()

    prompt = _build_transcript_prompt(transcript, jd_text, candidate_name)

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model":   OLLAMA_MODEL,
                    "prompt":  prompt,
                    "stream":  False,
                    "format":  "json",
                    "options": {"num_predict": 600, "temperature": 0.1},
                },
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "{}")
            parsed = _parse_json_response(raw)
            if parsed:
                return _normalize(parsed)
    except Exception:
        pass

    return _fallback_result()
