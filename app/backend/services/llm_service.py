import json
import os
import httpx
import enum
import asyncio
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OllamaState(str, enum.Enum):
    COLD = "cold"        # Model not loaded in RAM
    WARMING = "warming"  # Warmup in progress
    HOT = "hot"          # Model loaded and responsive
    ERROR = "error"      # Ollama unreachable or failing


class OllamaHealthSentinel:
    def __init__(self, ollama_base_url: str = None, model_name: str = "qwen3.5:4b", probe_interval: int = 60):
        self.base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.model_name = model_name
        self.probe_interval = probe_interval
        self.state = OllamaState.COLD
        self.last_probe_time: float = 0
        self.last_latency_ms: float = 0
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start the sentinel background loop."""
        self._running = True
        self._task = asyncio.create_task(self._probe_loop())
        logger.info("Ollama health sentinel started (interval=%ds)", self.probe_interval)

    async def stop(self):
        """Stop the sentinel gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Ollama health sentinel stopped")

    async def _probe_loop(self):
        """Main probe loop — runs every probe_interval seconds."""
        while self._running:
            await self._probe_once()
            await asyncio.sleep(self.probe_interval)

    async def _probe_once(self):
        """Single health probe: lightweight generate with num_predict=1."""
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Check if model is loaded via /api/ps
                resp = await client.get(f"{self.base_url}/api/ps")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_hot = any(self.model_name in m.get("name", "") for m in models)
                else:
                    model_hot = False

                if not model_hot:
                    # Model not in RAM — trigger warmup
                    self.state = OllamaState.WARMING
                    logger.info("Ollama model %s not hot, triggering warmup", self.model_name)
                    await client.post(
                        f"{self.base_url}/api/generate",
                        json={"model": self.model_name, "prompt": "warmup", "stream": False, "options": {"num_predict": 1}},
                        timeout=120.0
                    )
                    self.state = OllamaState.HOT
                    logger.info("Ollama model %s warmed up successfully", self.model_name)
                else:
                    # Model is hot — /api/ps confirmed it's loaded, no need for generate probe
                    self.state = OllamaState.HOT

                self.last_latency_ms = (time.monotonic() - start) * 1000
                self.last_probe_time = time.time()

        except Exception as e:
            self.state = OllamaState.ERROR
            self.last_latency_ms = (time.monotonic() - start) * 1000
            self.last_probe_time = time.time()
            logger.warning("Ollama health probe failed: %s: %s", type(e).__name__, e)

    def get_status(self) -> dict:
        return {
            "state": self.state.value,
            "model": self.model_name,
            "last_probe_time": self.last_probe_time,
            "last_latency_ms": round(self.last_latency_ms, 1),
            "healthy": self.state == OllamaState.HOT,
        }


# Module-level singleton
_sentinel: OllamaHealthSentinel | None = None


def get_sentinel() -> OllamaHealthSentinel | None:
    return _sentinel


class LLMService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")  # Faster 3B model
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

        _timeout = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "150")) + 30
        async with httpx.AsyncClient(timeout=_timeout) as client:  # respects LLM_NARRATIVE_TIMEOUT env var
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
