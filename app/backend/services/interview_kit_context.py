"""
Load requisition-driven inputs for Live Screen Kit generation.

HM screen-focus topics, calibrated criteria, and intake deal-breakers feed both
LLM and deterministic kit paths.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger("aria.enrichment")


def _parse_json_list(raw: Any) -> List[Any]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _parse_json_obj(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_screen_topics(items: List[Any]) -> List[Dict[str, str]]:
    """Normalize must_ask / screen_focus entries to {question, category, rationale}."""
    out: List[Dict[str, str]] = []
    for item in items:
        if isinstance(item, str) and item.strip():
            out.append({
                "question": item.strip(),
                "category": "hm_focus",
                "rationale": "HM screen-focus topic",
            })
        elif isinstance(item, dict):
            q = (item.get("question") or item.get("topic") or item.get("text") or "").strip()
            if not q:
                continue
            out.append({
                "question": q,
                "category": (item.get("category") or "hm_focus").strip(),
                "rationale": (item.get("rationale") or item.get("why") or "HM screen-focus topic").strip(),
            })
    return out[:12]


def load_kit_inputs_for_requisition(db, requisition_id: int, tenant_id: int) -> Dict[str, Any]:
    """Load HM topics and calibrated intake fields for kit generation."""
    from app.backend.models.db_models import Requisition

    req = db.query(Requisition).filter(
        Requisition.id == requisition_id,
        Requisition.tenant_id == tenant_id,
    ).first()
    if not req:
        return {}

    intake = _parse_json_obj(req.intake_json)
    calibrated = _parse_json_obj(req.calibrated_criteria_json)

    must_ask_raw = _parse_json_list(req.must_ask_questions_json)
    screen_focus = intake.get("screen_focus_topics") or []
    hm_topics = _normalize_screen_topics(must_ask_raw or screen_focus)

    deal_breakers = (
        intake.get("deal_breakers")
        or calibrated.get("deal_breakers")
        or []
    )
    if isinstance(deal_breakers, str):
        deal_breakers = [s.strip() for s in deal_breakers.split("\n") if s.strip()]

    calibrated_must = (
        calibrated.get("must_haves")
        or intake.get("must_haves")
        or []
    )
    if isinstance(calibrated_must, str):
        calibrated_must = [s.strip() for s in calibrated_must.split("\n") if s.strip()]

    hm_notes = (intake.get("hm_notes") or calibrated.get("hm_notes") or "").strip()
    success_90d = (intake.get("success_criteria_90d") or "").strip()

    return {
        "requisition_id": requisition_id,
        "requisition_title": req.title or "",
        "hm_screen_topics": hm_topics,
        "deal_breakers": [str(x).strip() for x in deal_breakers if str(x).strip()][:10],
        "calibrated_must_haves": [str(x).strip() for x in calibrated_must if str(x).strip()][:15],
        "hm_notes": hm_notes[:500],
        "success_criteria_90d": success_90d[:300],
    }


def load_kit_inputs_for_screening(db, screening_result_id: int, tenant_id: int) -> Dict[str, Any]:
    from app.backend.models.db_models import ScreeningResult

    row = db.query(ScreeningResult).filter(
        ScreeningResult.id == screening_result_id,
        ScreeningResult.tenant_id == tenant_id,
    ).first()
    if not row or not row.requisition_id:
        return {}
    return load_kit_inputs_for_requisition(db, row.requisition_id, tenant_id)


def sync_must_ask_from_intake(intake_json: Dict[str, Any]) -> Optional[str]:
    """Build must_ask_questions_json from intake screen_focus_topics."""
    topics = intake_json.get("screen_focus_topics") or []
    normalized = _normalize_screen_topics(topics if isinstance(topics, list) else [])
    if not normalized:
        return None
    return json.dumps(normalized)
