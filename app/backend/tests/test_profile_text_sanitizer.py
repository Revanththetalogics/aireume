"""Tests for profile text sanitization."""

from app.backend.services.profile_text_sanitizer import (
    is_actionable_responsibility,
    is_plausible_skill_name,
    normalize_work_entry,
    sanitize_candidate_profile,
    sanitize_jd_analysis,
    sanitize_jd_responsibilities,
    sanitize_parsed_resume_data,
    sanitize_profile_text,
    sanitize_skill_list,
    sanitize_work_experience,
)


class TestSanitizeProfileText:
    def test_strips_dangling_braces(self):
        assert sanitize_profile_text("ValueLabs {") == "ValueLabs"
        assert sanitize_profile_text("Acme { Corp }") == "Acme Corp"

    def test_strips_job_description_prefix(self):
        assert sanitize_profile_text("job description: Talent Acquisition Specialist") == (
            "Talent Acquisition Specialist"
        )


class TestSkillSanitization:
    def test_rejects_sentence_skills(self):
        assert not is_plausible_skill_name("5-12 years IT recruitment experience")
        assert not is_plausible_skill_name("job description: talent acquisition specialist")

    def test_keeps_real_skills(self):
        assert is_plausible_skill_name("Stakeholder Management")
        assert is_plausible_skill_name("Business Analyst")
        assert is_plausible_skill_name("SAP S/4HANA")
        assert sanitize_skill_list(
            ["Python", "5-12 years IT recruitment experience", "Python", "Full-Cycle Recruitment"]
        ) == ["Python", "Full-Cycle Recruitment"]


class TestWorkExperienceNormalization:
    def test_company_only_title_moves_to_company(self):
        entry = normalize_work_entry({"title": "ValueLabs {", "company": ""})
        assert entry["company"] == "ValueLabs"
        assert entry["title"] == ""

    def test_sanitize_work_experience_batch(self):
        entries = sanitize_work_experience(
            [{"title": "Recruiter", "company": "ValueLabs {"}, {"title": "Lead { Dev", "company": "Acme"}]
        )
        assert entries[0]["company"] == "ValueLabs"
        assert entries[1]["title"] == "Lead Dev"


class TestJdResponsibilities:
    def test_rejects_header_lines(self):
        assert not is_actionable_responsibility(
            "job description: talent acquisition specialist / lead talent"
        )

    def test_keeps_action_lines(self):
        assert is_actionable_responsibility(
            "Lead end-to-end recruitment for technical roles and partner with hiring managers"
        )

    def test_sanitize_filters_bad_lines(self):
        cleaned = sanitize_jd_responsibilities(
            [
                "job description: talent acquisition specialist / lead talent",
                "Drive full-cycle hiring for engineering teams across India and EMEA",
            ]
        )
        assert len(cleaned) == 1
        assert cleaned[0].startswith("Drive full-cycle hiring")


class TestStructuredSanitizers:
    def test_sanitize_parsed_resume_data(self):
        data = sanitize_parsed_resume_data(
            {
                "skills": ["Python", "8 years of experience in Java"],
                "work_experience": [{"title": "ValueLabs {", "company": ""}],
                "contact_info": {"name": "Jane { Doe"},
            }
        )
        assert data["skills"] == ["Python"]
        assert data["work_experience"][0]["company"] == "ValueLabs"
        assert data["contact_info"]["name"] == "Jane Doe"

    def test_sanitize_jd_analysis(self):
        jd = sanitize_jd_analysis(
            {
                "role_title": "Talent Acquisition {",
                "required_skills": ["Stakeholder Management", "5-12 years IT recruitment experience"],
                "key_responsibilities": [
                    "job description: talent acquisition specialist / lead talent",
                    "Manage stakeholder expectations during offer negotiations",
                ],
            }
        )
        assert jd["role_title"] == "Talent Acquisition"
        assert jd["required_skills"] == ["Stakeholder Management"]
        assert len(jd["key_responsibilities"]) == 1

    def test_sanitize_candidate_profile(self):
        profile = sanitize_candidate_profile(
            {
                "name": "Kalpana {",
                "current_role": "Recruiter {",
                "current_company": "ValueLabs {",
                "skills_identified": ["Python", "years of experience in HR"],
                "work_experience": [{"title": "ValueLabs {", "company": ""}],
            }
        )
        assert profile["name"] == "Kalpana"
        assert profile["current_company"] == "ValueLabs"
        assert profile["skills_identified"] == ["Python"]
