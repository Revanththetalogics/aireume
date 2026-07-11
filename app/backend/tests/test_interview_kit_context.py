"""Tests for interview kit requisition context loading."""

import json

import pytest

from app.backend.models.db_models import Requisition, ScreeningResult, Tenant, User
from app.backend.services.interview_kit_context import (
    load_kit_inputs_for_requisition,
    sync_must_ask_from_intake,
)


@pytest.fixture
def tenant(db):
    t = Tenant(name="KitCtx", slug="kit-ctx")
    db.add(t)
    db.commit()
    return t


@pytest.fixture
def requisition(db, tenant):
    req = Requisition(
        tenant_id=tenant.id,
        title="Senior Analyst",
        jd_text="Finance analyst JD",
        intake_json=json.dumps({
            "screen_focus_topics": ["Budgeting depth", "Stakeholder management"],
            "deal_breakers": ["No FP&A experience"],
            "must_haves": ["Excel", "Budgeting"],
        }),
        calibrated_criteria_json=json.dumps({
            "must_haves": ["Excel", "Budgeting", "Forecasting"],
        }),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def test_sync_must_ask_from_intake():
    payload = sync_must_ask_from_intake({
        "screen_focus_topics": ["Team leadership", "Cost control"],
    })
    assert payload is not None
    data = json.loads(payload)
    assert len(data) == 2
    assert data[0]["question"] == "Team leadership"


def test_load_kit_inputs_for_requisition(db, tenant, requisition):
    inputs = load_kit_inputs_for_requisition(db, requisition.id, tenant.id)
    assert inputs["requisition_title"] == "Senior Analyst"
    assert len(inputs["hm_screen_topics"]) == 2
    assert inputs["hm_screen_topics"][0]["question"] == "Budgeting depth"
    assert "No FP&A experience" in inputs["deal_breakers"]
    assert "Forecasting" in inputs["calibrated_must_haves"]


def test_load_kit_inputs_for_screening(db, tenant, requisition):
    row = ScreeningResult(
        tenant_id=tenant.id,
        requisition_id=requisition.id,
        resume_text="resume",
        jd_text="jd",
        parsed_data="{}",
        analysis_result="{}",
    )
    db.add(row)
    db.commit()
    from app.backend.services.interview_kit_context import load_kit_inputs_for_screening
    inputs = load_kit_inputs_for_screening(db, row.id, tenant.id)
    assert inputs["hm_screen_topics"][1]["question"] == "Stakeholder management"
