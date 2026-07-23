"""Tests for single-step kit regeneration API."""

import json


def _create_test_result(db, tenant_id: int, analysis: dict | None = None):
    from app.backend.models.db_models import ScreeningResult

    result = ScreeningResult(
        tenant_id=tenant_id,
        candidate_id=None,
        resume_text="test resume",
        jd_text="test jd",
        parsed_data="{}",
        analysis_result=json.dumps(analysis or {}),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def test_regenerate_step_updates_spoken_text(auth_client, db, monkeypatch):
    from app.backend.models.db_models import Tenant

    async def fake_personalize_step(kit, *, thread_id, step_index, context):
        out = json.loads(json.dumps(kit))
        for thread in out.get("threads") or []:
            if thread.get("id") != thread_id:
                continue
            step = thread["steps"][step_index]
            step["spoken_text"] = "At Acme Corp — what did you personally configure in MM?"
            step["intent"] = "Verify MM ownership"
        return out

    monkeypatch.setattr(
        "app.backend.services.recruiter_voice_personalizer.personalize_step",
        fake_personalize_step,
    )

    tenant = db.query(Tenant).first()
    kit = {
        "kit_version": 3,
        "threads": [{
            "id": "thread_ownership",
            "steps": [{"text": "Tell me about your role.", "spoken_text": "Tell me about your role."}],
        }],
    }
    result = _create_test_result(db, tenant.id, analysis={"interview_questions": kit})

    resp = auth_client.post(
        f"/api/interview-kit/{result.id}/regenerate-step",
        json={"thread_id": "thread_ownership", "step_index": 0},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    step = body["kit"]["threads"][0]["steps"][0]
    assert "Acme Corp" in step["spoken_text"]
