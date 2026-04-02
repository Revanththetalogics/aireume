import pytest
from app.backend.services.parser_service import ResumeParser, parse_resume


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
January 2020 – Present
Leading development teams

Software Engineer | StartupCo
June 2017 – December 2019
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
Senior Engineer | TechCorp
January 2020 – Present
Leading teams and building products

Software Engineer | Startup
June 2017 – December 2019
Full stack development
"""
        parser = ResumeParser()
        result = parser.parse_resume(sample_text.encode(), "resume.txt")

        jobs = result["work_experience"]
        assert len(jobs) >= 1

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

    def test_parse_resume_function(self):
        sample_text = "Simple resume text with Python and JavaScript skills"
        result = parse_resume(sample_text.encode(), "resume.txt")

        assert isinstance(result, dict)
        assert "raw_text" in result
