"""Tests for interview kit loader and kit-driven orchestrator."""
import pytest

from app.backend.services.interview_kit_loader import flatten_interview_kit
from app.voice_agent.kit_orchestrator import KitDrivenOrchestrator
from app.voice_agent.orchestrator import OrchestratorContext


class TestFlattenInterviewKit:
    def test_flattens_categories_in_order(self):
        kit = {
            "technical_questions": [{"text": "Tech Q1?", "follow_ups": ["Follow tech"]}],
            "behavioral_questions": ["Behavior Q1?"],
            "culture_fit_questions": [],
            "experience_deep_dive_questions": [{"text": "Exp Q1?"}],
        }
        flat = flatten_interview_kit(kit)
        assert len(flat) == 3
        assert flat[0]["category"] == "technical"
        assert flat[0]["text"] == "Tech Q1?"
        assert flat[1]["category"] == "behavioral"
        assert flat[2]["category"] == "experience_deep_dive"


class TestKitDrivenOrchestrator:
    @pytest.mark.asyncio
    async def test_walks_kit_questions_after_intro(self):
        ctx = OrchestratorContext(
            session_id="99",
            candidate_name="Alex",
            jd_title="Analyst",
            total_duration_s=900,
        )
        questions = [
            {"id": "tech-0", "category": "technical", "text": "Describe your Excel experience."},
            {"id": "beh-0", "category": "behavioral", "text": "Tell me about a deadline you met."},
        ]
        orch = KitDrivenOrchestrator(ctx, questions)

        greeting = await orch.start()
        assert "Alex" in greeting

        r1 = await orch.handle_candidate_response("Yes, I have time.")
        assert "consent" in r1.lower() or "recorded" in r1.lower()

        r2 = await orch.handle_candidate_response("Yes.")
        assert "Excel" in r2

        r3 = await orch.handle_candidate_response(
            "I built financial models in Excel for three years including pivot tables and macros."
        )
        assert "deadline" in r3.lower()

        r4 = await orch.handle_candidate_response(
            "We had a month-end close due Friday and I prioritized reconciliation first."
        )
        assert r4 is not None
        assert "thank you" in r4.lower() or "touch" in r4.lower()

        assert len(ctx.questions_responses) == 2
        assert ctx.questions_responses[0]["question"] == "Describe your Excel experience."

    @pytest.mark.asyncio
    async def test_custom_opening_replaces_default_greeting(self):
        ctx = OrchestratorContext(
            session_id="100",
            candidate_name="Alex",
            jd_title="Analyst",
            company_name="Acme",
            bot_name="ARIA",
            use_custom_interview_opening=True,
            interview_opening_script=(
                "Hello {candidate_first_name}, {bot_name} here from {company_name} "
                "regarding {role_title}. Got a minute?"
            ),
            total_duration_s=900,
        )
        orch = KitDrivenOrchestrator(ctx, [{"id": "t1", "category": "technical", "text": "Q1?"}])
        greeting = await orch.start()
        assert "Hello Alex" in greeting
        assert "Acme" in greeting
        assert "Got a minute" in greeting

    @pytest.mark.asyncio
    async def test_no_filler_during_kit_questions(self):
        ctx = OrchestratorContext(session_id="1", candidate_name="Alex", total_duration_s=600)
        orch = KitDrivenOrchestrator(ctx, [{"id": "t1", "category": "technical", "text": "Q1?"}])
        assert orch.should_play_filler() is False
