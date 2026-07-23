import pytest


@pytest.mark.asyncio
async def test_phrase_follow_up_heuristic_when_no_llm():
    from app.voice_agent.turn_personalizer import phrase_follow_up

    result = await phrase_follow_up(
        intent="Clarify personal contribution",
        last_question="Tell me about the migration.",
        last_answer="We migrated everything last year.",
        candidate_name="Jane",
    )
    assert "you" in result.lower() or "yourself" in result.lower()


def test_answer_has_specifics():
    from app.voice_agent.turn_personalizer import answer_has_specifics

    assert answer_has_specifics("For example, I built the pipeline and led the team through go-live with three engineers.")
    assert not answer_has_specifics("yes")
