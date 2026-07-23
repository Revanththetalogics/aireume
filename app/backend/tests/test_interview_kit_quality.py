from app.backend.services.interview_kit_quality import (
    FORBIDDEN_STEMS,
    get_spoken_line,
    lint_interview_kit,
)


def test_flags_repeated_walk_me_through():
    kit = {
        "kit_version": 3,
        "threads": [{
            "steps": [
                {"text": "Walk me through your SAP work."},
                {"text": "Walk me through your team setup."},
            ],
        }],
    }
    result = lint_interview_kit(kit)
    assert result["ok"] is False
    assert any("walk me" in i["message"].lower() for i in result["issues"])


def test_flags_this_role_needs_stem():
    kit = {"threads": [{"steps": [{"text": "This role needs Kubernetes in production."}]}]}
    result = lint_interview_kit(kit)
    assert result["ok"] is False


def test_passes_personalized_question():
    kit = {
        "threads": [{
            "steps": [{
                "spoken_text": (
                    "At Acme you ran the S/4 cutover — what did you personally own through go-live?"
                ),
            }],
        }],
    }
    result = lint_interview_kit(kit)
    assert result["ok"] is True


def test_get_spoken_line_prefers_spoken_text():
    assert get_spoken_line({"text": "OLD", "spoken_text": "NEW"}) == "NEW"


def test_forbidden_stems_tuple_not_empty():
    assert len(FORBIDDEN_STEMS) >= 3
