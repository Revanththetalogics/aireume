import pytest


@pytest.mark.asyncio
async def test_personalize_kit_sets_spoken_text(monkeypatch):
    async def fake_llm(prompts, **kwargs):
        return {
            "threads": [{
                "id": "thread_ownership",
                "steps": [{
                    "intent": "Verify SAP MM ownership",
                    "spoken_text": "At Acme you were on the MM rollout — what did you personally configure?",
                    "follow_up_intents": ["If they say 'we', ask what they did personally"],
                }],
            }],
        }

    monkeypatch.setattr(
        "app.backend.services.llm_json_service.invoke_llm_json_resilient",
        fake_llm,
    )
    from app.backend.services.recruiter_voice_personalizer import personalize_kit

    kit = {
        "kit_version": 3,
        "threads": [{
            "id": "thread_ownership",
            "steps": [{"text": "Walk me through your SAP work at Acme."}],
        }],
    }
    result = await personalize_kit(kit, {"resume_anchors": {"current_company": "Acme"}})
    step = result["threads"][0]["steps"][0]
    assert "Acme" in step["spoken_text"]
    assert step.get("intent")


def test_minimal_personalization_injects_company():
    from app.backend.services.recruiter_voice_personalizer import _apply_minimal_personalization

    kit = {
        "threads": [{
            "id": "thread_ownership",
            "kind": "ownership",
            "steps": [{"text": "Tell me about your recent role."}],
        }],
    }
    out = _apply_minimal_personalization(kit, {"resume_anchors": {"current_company": "Acme", "current_role": "Consultant"}})
    spoken = out["threads"][0]["steps"][0]["spoken_text"]
    assert "Acme" in spoken
