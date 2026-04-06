import json
import os
import httpx
from typing import Dict, Any, Optional


class LLMService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "gemma4:e4b")  # Faster 3B model
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

        async with httpx.AsyncClient(timeout=60.0) as client:  # 1 minute timeout
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
        # Truncate text for faster processing
        jd_summary = job_description[:500] if len(job_description) > 500 else job_description
        resume_summary = resume_text[:1000] if len(resume_text) > 1000 else resume_text
        
        return f"""Analyze this candidate for the job. Be concise.

JOB: {jd_summary}

RESUME: {resume_summary}

METRICS: Match {skill_match_percent:.0f}%, Exp {total_years:.1f}y, Gaps {len(gaps)}, Risks {len(risks)}

Return JSON: {{"fit_score": 0-100, "strengths": ["3-5 items"], "weaknesses": ["3-5 items"], "education_analysis": "brief", "risk_signals": ["list"], "final_recommendation": "Shortlist|Consider|Reject"}}

JSON:"""

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
