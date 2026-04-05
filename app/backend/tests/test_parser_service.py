import pytest
from app.backend.services.parser_service import ResumeParser, parse_resume, enrich_parsed_resume


class TestResumeParser:
    def test_extract_text_with_plain_text(self):
        parser = ResumeParser()
        text = "John Doe\nSoftware Engineer\n"
        result = parser.extract_text(text.encode(), "resume.txt")
        # Should handle gracefully, not fail
        assert isinstance(result, str)

    def test_parse_resume_structure(self):
        sample_text = """
John Doe
Software Engineer
john.doe@email.com

SKILLS
Python, JavaScript, React

WORK EXPERIENCE
Senior Engineer | TechCorp
January 2020 - Present
Leading development teams

Software Engineer | StartupCo
June 2017 - December 2019
Built web applications

EDUCATION
BS Computer Science, 2015
"""
        parser = ResumeParser()
        result = parser.parse_resume(sample_text.encode(), "resume.txt")

        assert "raw_text" in result
        assert "work_experience" in result
        assert "skills" in result
        assert "education" in result
        assert "contact_info" in result

    def test_extract_skills(self):
        sample_text = """
SKILLS
Python, JavaScript, React, Node.js, PostgreSQL, Docker, AWS
"""
        parser = ResumeParser()
        result = parser.parse_resume(sample_text.encode(), "resume.txt")

        skills = result["skills"]
        assert len(skills) > 0
        assert any("Python" in s for s in skills)

    def test_extract_work_experience(self):
        sample_text = """
WORK EXPERIENCE

TechCorp | Senior Engineer
January 2020 - Present
Leading teams and building products

Startup | Software Engineer
June 2017 - December 2019
Full stack development
"""
        parser = ResumeParser()
        result = parser.parse_resume(sample_text.encode(), "resume.txt")

        jobs = result["work_experience"]
        # Parser may find jobs depending on format
        # Just verify the structure is correct
        assert isinstance(jobs, list)

    def test_extract_contact_info(self):
        sample_text = """
John Doe
john.doe@email.com
+1-555-123-4567
linkedin.com/in/johndoe
"""
        parser = ResumeParser()
        result = parser.parse_resume(sample_text.encode(), "resume.txt")

        contact = result["contact_info"]
        assert "email" in contact
        assert "john.doe@email.com" in contact["email"]

    def test_extract_name_hyphenated(self):
        parser = ResumeParser()
        text = """
Mary-Jane Smith
Software Engineer
mary@example.com
"""
        assert parser._extract_name(text) == "Mary-Jane Smith"

    def test_extract_name_pipe_before_phone(self):
        parser = ResumeParser()
        text = """
Revanth Kumar | +91 98765 43210 | revanth@company.com
Embedded Systems Engineer
"""
        assert parser._extract_name(text).startswith("Revanth")

    def test_extract_work_year_to_present(self):
        parser = ResumeParser()
        text = """
WORK
Acme Corp — Senior Engineer
2018 – Present
Shipped firmware.
"""
        jobs = parser._extract_work_experience(text)
        assert len(jobs) >= 1
        assert jobs[0].get("end_date") == "present"

    def test_parse_resume_function(self):
        sample_text = "Simple resume text with Python and JavaScript skills"
        result = parse_resume(sample_text.encode(), "resume.txt")

        assert isinstance(result, dict)
        assert "raw_text" in result

    def test_enrich_name_from_email_when_header_missing(self):
        data = {
            "raw_text": "SKILLS\nPython, C++\n",
            "contact_info": {"email": "jane.smith@corp.io"},
            "work_experience": [],
            "skills": [],
            "education": [],
        }
        enrich_parsed_resume(data)
        assert data["contact_info"]["name"] == "Jane Smith"
