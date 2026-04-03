import json
import os
import httpx
from typing import Dict, Any, Optional


class LLMService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = "llama3"
        self.max_retries = 1

    async def analyze_resume(
        self,
        resume_text: str,
        job_description: str,
        skill_match_percent: float,
        total_years: float,
        gaps: list,
        risks: list
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(
            resume_text=resume_text,
            job_description=job_description,
            skill_match_percent=skill_match_percent,
            total_years=total_years,
            gaps=gaps,
            risks=risks
        )

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._call_ollama(prompt)
                parsed = self._parse_json_response(response)
                if parsed:
                    return self._validate_and_normalize(parsed)
            except Exception as e:
                if attempt == self.max_retries:
                    return self._fallback_response(str(e))

        return self._fallback_response("Max retries exceeded")

    async def _call_ollama(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    def _build_prompt(
        self,
        resume_text: str,
        job_description: str,
        skill_match_percent: float,
        total_years: float,
        gaps: list,
        risks: list
    ) -> str:
        return f"""You are an expert recruiter AI.

Analyze the candidate strictly based on provided data.
DO NOT hallucinate.
DO NOT add assumptions.
ONLY use given data.

=== JOB DESCRIPTION ===
{job_description}

=== RESUME TEXT ===
{resume_text[:3000]}

=== COMPUTED METRICS ===
- Skill Match: {skill_match_percent:.1f}%
- Total Experience: {total_years:.1f} years
- Employment Gaps Detected: {len(gaps)}
- Risk Signals: {[r.get('type') for r in risks]}

Return STRICT JSON ONLY with this exact schema:
{{
    "fit_score": <number 0-100>,
    "strengths": ["max 5 bullet points"],
    "weaknesses": ["max 5 bullet points"],
    "education_analysis": "brief assessment of education fit",
    "risk_signals": ["identified risks"],
    "final_recommendation": "Shortlist" | "Consider" | "Reject"
}}

JSON response:"""

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        # Try to find JSON in the response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            json_match = re.search(r'```\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

        return None

    def _validate_and_normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure fit_score is within bounds
        fit_score = max(0, min(100, int(data.get("fit_score", 0))))

        # Ensure arrays have max 5 items
        strengths = data.get("strengths", [])[:5]
        weaknesses = data.get("weaknesses", [])[:5]

        # Validate recommendation
        valid_recommendations = ["Shortlist", "Consider", "Reject"]
        recommendation = data.get("final_recommendation", "Consider")
        if recommendation not in valid_recommendations:
            recommendation = "Consider"

        return {
            "fit_score": fit_score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "education_analysis": data.get("education_analysis", ""),
            "risk_signals": data.get("risk_signals", []),
            "final_recommendation": recommendation
        }

    def _fallback_response(self, error_message: str) -> Dict[str, Any]:
        return {
            "fit_score": 50,
            "strengths": ["Analysis temporarily unavailable"],
            "weaknesses": ["Unable to complete detailed analysis"],
            "education_analysis": "Education analysis could not be completed.",
            "risk_signals": [{"type": "analysis_error", "description": error_message}],
            "final_recommendation": "Consider"
        }


async def analyze_with_llm(
    resume_text: str,
    job_description: str,
    skill_match_percent: float,
    total_years: float,
    gaps: list,
    risks: list
) -> Dict[str, Any]:
    service = LLMService()
    return await service.analyze_resume(
        resume_text=resume_text,
        job_description=job_description,
        skill_match_percent=skill_match_percent,
        total_years=total_years,
        gaps=gaps,
        risks=risks
    )
