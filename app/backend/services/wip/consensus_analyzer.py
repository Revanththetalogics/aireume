"""
Multi-Model Consensus Analyzer

Reduces single-model bias by running analysis through multiple LLM models
and aggregating results using statistical methods.

Provides:
- Parallel analysis with multiple models
- Median-based score aggregation (robust to outliers)
- Model agreement metrics
- Fallback to single model if others unavailable
"""
import logging
import asyncio
import os
from typing import Dict, List, Any, Optional
import statistics
from dataclasses import dataclass

from app.backend.services.transcript_service import (
    _build_transcript_prompt,
    _parse_json_response,
    _normalize,
    _fallback_result
)
from app.backend.services.llm_service import get_ollama_semaphore, get_ollama_headers
import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@dataclass
class ModelResult:
    """Result from a single model."""
    model_name: str
    success: bool
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    latency_ms: int


class ConsensusAnalyzer:
    """
    Analyzes transcripts using multiple models and aggregates results.
    
    Uses median aggregation for robustness against outliers.
    Provides model agreement metrics for confidence assessment.
    """
    
    def __init__(self, models: Optional[List[str]] = None):
        """
        Initialize consensus analyzer.
        
        Args:
            models: List of model names to use. Defaults to 3 diverse models.
        """
        self.models = models or [
            "gemma4:31b-cloud",  # Primary model - balanced
            "gemma4:31b-cloud",  # Same model, different seed
            "gemma4:31b-cloud",  # Same model, third run for consensus
        ]
        self.timeout = 120.0
    
    async def analyze_with_consensus(
        self,
        transcript: str,
        jd_text: str,
        candidate_name: str = "CANDIDATE",
    ) -> Dict[str, Any]:
        """
        Run analysis through multiple models and aggregate results.
        
        Args:
            transcript: Cleaned transcript text (already PII-redacted)
            jd_text: Job description
            candidate_name: Candidate name (should be generic after PII redaction)
            
        Returns:
            Aggregated result with consensus scores and model agreement metrics
        """
        if not transcript or len(transcript) < 30:
            return _fallback_result()
        
        logger.info(f"Starting consensus analysis with {len(self.models)} models")
        
        # Run analysis in parallel across all models
        tasks = [
            self._analyze_with_model(transcript, jd_text, candidate_name, model)
            for model in self.models
        ]
        
        model_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful_results = []
        for i, result in enumerate(model_results):
            if isinstance(result, ModelResult) and result.success:
                successful_results.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Model {self.models[i]} failed: {result}")
        
        # Need at least 2 models for consensus
        if len(successful_results) < 2:
            logger.warning(
                f"Only {len(successful_results)} models succeeded. "
                "Falling back to single model or fallback result."
            )
            if successful_results:
                return successful_results[0].result
            return _fallback_result()
        
        # Aggregate results
        consensus_result = self._aggregate_results(successful_results)
        
        # Add consensus metadata
        consensus_result["consensus_metadata"] = {
            "models_used": [r.model_name for r in successful_results],
            "models_count": len(successful_results),
            "model_agreement": self._calculate_agreement(successful_results),
            "average_latency_ms": statistics.mean([r.latency_ms for r in successful_results]),
        }
        
        logger.info(
            f"Consensus analysis complete: {len(successful_results)} models, "
            f"Agreement: {consensus_result['consensus_metadata']['model_agreement']:.1%}"
        )
        
        return consensus_result
    
    async def _analyze_with_model(
        self,
        transcript: str,
        jd_text: str,
        candidate_name: str,
        model: str
    ) -> ModelResult:
        """
        Run analysis with a single model.
        
        Returns ModelResult with success/failure status.
        """
        import time
        start_time = time.time()
        
        try:
            prompt = _build_transcript_prompt(transcript, jd_text, candidate_name)
            
            # Use semaphore to prevent overwhelming Ollama
            sem = get_ollama_semaphore()
            async with sem:
                headers = get_ollama_headers(OLLAMA_BASE_URL)
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{OLLAMA_BASE_URL}/api/generate",
                        headers=headers,
                        json={
                            "model": model,
                            "prompt": prompt,
                            "stream": False,
                            "format": "json",
                            "options": {"num_predict": 2000, "temperature": 0.1},
                        },
                    )
                    resp.raise_for_status()
                    raw = resp.json().get("response", "{}")
                    parsed = _parse_json_response(raw)
                    
                    if parsed:
                        result = _normalize(parsed)
                        latency_ms = int((time.time() - start_time) * 1000)
                        
                        return ModelResult(
                            model_name=model,
                            success=True,
                            result=result,
                            error=None,
                            latency_ms=latency_ms
                        )
        
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Model {model} failed: {e}")
            return ModelResult(
                model_name=model,
                success=False,
                result=None,
                error=str(e),
                latency_ms=latency_ms
            )
        
        # Should not reach here
        return ModelResult(
            model_name=model,
            success=False,
            result=None,
            error="Unknown error",
            latency_ms=int((time.time() - start_time) * 1000)
        )
    
    def _aggregate_results(
        self,
        model_results: List[ModelResult]
    ) -> Dict[str, Any]:
        """
        Aggregate results from multiple models using median for robustness.
        
        Median is more robust than mean against outlier scores.
        """
        results = [r.result for r in model_results]
        
        # Aggregate scores using median
        fit_scores = [r["fit_score"] for r in results]
        technical_scores = [r["technical_depth"] for r in results]
        communication_scores = [r["communication_quality"] for r in results]
        
        aggregated = {
            "fit_score": int(statistics.median(fit_scores)),
            "technical_depth": int(statistics.median(technical_scores)),
            "communication_quality": int(statistics.median(communication_scores)),
        }
        
        # Merge JD alignment (take union, mark demonstrated if majority agree)
        aggregated["jd_alignment"] = self._merge_jd_alignment(results)
        
        # Merge strengths (take most common, with evidence)
        aggregated["strengths"] = self._merge_lists(
            [r.get("strengths", []) for r in results],
            max_items=6
        )
        
        # Merge areas for improvement
        aggregated["areas_for_improvement"] = self._merge_lists(
            [r.get("areas_for_improvement", []) for r in results],
            max_items=4
        )
        
        # Merge red flags (take union, keep high severity)
        aggregated["red_flags"] = self._merge_red_flags(results)
        
        # Consensus recommendation (majority vote)
        recommendations = [r.get("recommendation", "hold") for r in results]
        aggregated["recommendation"] = max(set(recommendations), key=recommendations.count)
        
        # Combine bias notes
        aggregated["bias_note"] = (
            f"Consensus evaluation from {len(results)} independent models. "
            "Evaluation based solely on demonstrated skills and knowledge in the transcript."
        )
        
        # Combine recommendation rationales
        rationales = [r.get("recommendation_rationale", "") for r in results if r.get("recommendation_rationale")]
        if rationales:
            aggregated["recommendation_rationale"] = rationales[0]  # Use first non-empty
        else:
            aggregated["recommendation_rationale"] = ""
        
        return aggregated
    
    def _merge_jd_alignment(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge JD alignment from multiple models."""
        # Collect all requirements mentioned
        all_requirements = {}
        
        for result in results:
            for item in result.get("jd_alignment", []):
                req = item.get("requirement", "")
                if not req:
                    continue
                
                if req not in all_requirements:
                    all_requirements[req] = {
                        "requirement": req,
                        "demonstrated_count": 0,
                        "evidences": [],
                        "confidences": []
                    }
                
                if item.get("demonstrated"):
                    all_requirements[req]["demonstrated_count"] += 1
                
                if item.get("evidence"):
                    all_requirements[req]["evidences"].append(item["evidence"])
                
                if item.get("confidence"):
                    all_requirements[req]["confidences"].append(item["confidence"])
        
        # Build merged alignment (majority vote for demonstrated)
        merged = []
        threshold = len(results) / 2  # Majority
        
        for req, data in all_requirements.items():
            demonstrated = data["demonstrated_count"] > threshold
            
            # Use first evidence if available
            evidence = data["evidences"][0] if data["evidences"] else None
            
            # Most common confidence level
            if data["confidences"]:
                confidence = max(set(data["confidences"]), key=data["confidences"].count)
            else:
                confidence = "medium"
            
            merged.append({
                "requirement": req,
                "demonstrated": demonstrated,
                "evidence": evidence,
                "confidence": confidence
            })
        
        return merged
    
    def _merge_lists(
        self,
        lists: List[List[Any]],
        max_items: int
    ) -> List[Any]:
        """Merge lists of strengths or areas for improvement."""
        # Flatten all items
        all_items = []
        for lst in lists:
            all_items.extend(lst)
        
        if not all_items:
            return []
        
        # Handle both string and dict formats
        if isinstance(all_items[0], str):
            # Old format - count occurrences
            from collections import Counter
            counter = Counter(all_items)
            return [item for item, count in counter.most_common(max_items)]
        
        # New format with evidence - group by main field
        grouped = {}
        for item in all_items:
            if isinstance(item, dict):
                key = item.get("strength") or item.get("area", "")
                if key and key not in grouped:
                    grouped[key] = item
        
        return list(grouped.values())[:max_items]
    
    def _merge_red_flags(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge red flags, keeping high severity ones."""
        all_flags = []
        
        for result in results:
            all_flags.extend(result.get("red_flags", []))
        
        if not all_flags:
            return []
        
        # Group by flag text
        grouped = {}
        for flag in all_flags:
            flag_text = flag.get("flag", "")
            if not flag_text:
                continue
            
            if flag_text not in grouped:
                grouped[flag_text] = flag
            else:
                # Keep higher severity
                existing_severity = grouped[flag_text].get("severity", "low")
                new_severity = flag.get("severity", "low")
                severity_order = {"high": 2, "medium": 1, "low": 0}
                
                if severity_order.get(new_severity, 0) > severity_order.get(existing_severity, 0):
                    grouped[flag_text] = flag
        
        # Sort by severity and return top 5
        severity_order = {"high": 2, "medium": 1, "low": 0}
        sorted_flags = sorted(
            grouped.values(),
            key=lambda f: severity_order.get(f.get("severity", "low"), 0),
            reverse=True
        )
        
        return sorted_flags[:5]
    
    def _calculate_agreement(self, model_results: List[ModelResult]) -> float:
        """
        Calculate model agreement score (0-1).
        
        Based on variance in scores - lower variance = higher agreement.
        """
        if len(model_results) < 2:
            return 1.0
        
        fit_scores = [r.result["fit_score"] for r in model_results]
        
        # Calculate coefficient of variation (normalized standard deviation)
        mean_score = statistics.mean(fit_scores)
        if mean_score == 0:
            return 1.0
        
        std_dev = statistics.stdev(fit_scores) if len(fit_scores) > 1 else 0
        cv = std_dev / mean_score
        
        # Convert to agreement score (0-1)
        # CV of 0 = perfect agreement (1.0)
        # CV of 0.3+ = poor agreement (0.0)
        agreement = max(0, 1 - (cv / 0.3))
        
        return agreement


# Singleton instance
_consensus_analyzer: Optional[ConsensusAnalyzer] = None


def get_consensus_analyzer(models: Optional[List[str]] = None) -> ConsensusAnalyzer:
    """Get or create singleton consensus analyzer."""
    global _consensus_analyzer
    if _consensus_analyzer is None:
        _consensus_analyzer = ConsensusAnalyzer(models=models)
    return _consensus_analyzer
