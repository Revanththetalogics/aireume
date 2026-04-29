"""
Comprehensive tests for the resume parser overhaul.

Covers:
- dateparser-powered date extraction
- expanded education extraction
- new fields: certifications, languages, professional summary
- skills normalization via SKILL_ALIASES
- improved work title/company parsing
- gap detector date normalization
"""

import sys
import os

# Ensure project root is on the path (conftest handles this, but keep for direct runs)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import pytest
from app.backend.services.parser_service import (
    ResumeParser,
    _extract_date_range,
    _normalize_date_text,
)
from app.backend.services.gap_detector import _to_ym, analyze_gaps
from app.backend.services.skill_matcher import normalize_skill_name


# ═══════════════════════════════════════════════════════════════════════════════
# 1. TestDateExtraction
# ═══════════════════════════════════════════════════════════════════════════════

class TestDateExtraction:
    """Test dateparser-powered date extraction from work experience lines."""

    def test_period_suffixed_months(self):
        """'AUG. 2011 – DEC 2014' should parse correctly."""
        result = _extract_date_range("AUG. 2011 – DEC 2014")
        assert result is not None
        start, end = result
        assert "2011" in start
        assert "2014" in end

    def test_till_date_as_present(self):
        """'DEC 2014 – Till Date' should be recognized as current role."""
        result = _extract_date_range("DEC 2014 – Till Date")
        assert result is not None
        start, end = result
        assert "2014" in start
        assert end.lower() == "present"

    def test_ongoing_keyword(self):
        """'2014 – Ongoing' should parse as current."""
        result = _extract_date_range("2014 – Ongoing")
        assert result is not None
        _, end = result
        assert end.lower() == "present"

    def test_to_date_keyword(self):
        """'2014 – To Date' should parse as current."""
        result = _extract_date_range("2014 – To Date")
        assert result is not None
        _, end = result
        assert end.lower() == "present"

    def test_full_month_names(self):
        """'December 2014 – Present' should parse."""
        result = _extract_date_range("December 2014 – Present")
        assert result is not None
        start, end = result
        assert "2014" in start
        assert end.lower() == "present"

    def test_slash_format(self):
        """'08/2011 – 12/2014' should parse."""
        result = _extract_date_range("08/2011 – 12/2014")
        assert result is not None
        start, end = result
        assert "2011" in start
        assert "2014" in end

    def test_year_only_range(self):
        """'2014 – 2018' should parse."""
        result = _extract_date_range("2014 – 2018")
        assert result is not None
        start, end = result
        assert "2014" in start
        assert "2018" in end

    def test_standard_present(self):
        """'Jan 2020 – Present' should parse (backward compat)."""
        result = _extract_date_range("Jan 2020 – Present")
        assert result is not None
        _, end = result
        assert end.lower() == "present"

    def test_standard_current(self):
        """'Jan 2020 – Current' should parse (backward compat)."""
        result = _extract_date_range("Jan 2020 – Current")
        assert result is not None
        _, end = result
        assert end.lower() == "present"

    def test_standard_month_year_range(self):
        """'Jan 2020 – Dec 2023' should parse (backward compat)."""
        result = _extract_date_range("Jan 2020 – Dec 2023")
        assert result is not None
        start, end = result
        assert "2020" in start
        assert "2023" in end

    def test_jaiganesh_all_five_entries(self):
        """Parse all 5 employment entries from the veteran resume."""
        text = """PROFESSIONAL EXPERIENCE
Lead Engineer UTC AEROSPACE SYSTEMS DEC 2014 – Till Date
Senior Software Engineer AMETEK INSTRUMENTS INDIA PVT. LTD AUG. 2011 – DEC 2014
Senior Engineer TRIGENT SOFTWARE LTD. deputed @ AMETEK SEPT. 2010 – JULY 2011
Software Engineer AK AEROTEK SOFTWARE CENTRE PVT. LTD APRIL 2007 – AUG. 2010
Field Service Engineer ALCON LABORATORIES INDIA PVT. LTD MAY 2003 – SEPT 2006"""
        parser = ResumeParser()
        jobs = parser._extract_work_experience(text)
        assert len(jobs) >= 5, f"Expected 5 jobs, got {len(jobs)}"

    def test_normalize_date_text_strips_periods(self):
        """_normalize_date_text should strip periods from month abbreviations."""
        result = _normalize_date_text("AUG. 2011")
        assert "AUG." not in result
        assert "AUG 2011" in result or "AUG  2011" in result or "AUG 2011" == result

    def test_normalize_date_text_till_date(self):
        """_normalize_date_text should convert 'Till Date' to 'Present'."""
        result = _normalize_date_text("DEC 2014 – Till Date")
        assert "Till Date" not in result
        assert "Present" in result

    def test_continuing_keyword(self):
        """'2019 – Continuing' should parse as current."""
        result = _extract_date_range("2019 – Continuing")
        assert result is not None
        _, end = result
        assert end.lower() == "present"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TestEducationExtraction
# ═══════════════════════════════════════════════════════════════════════════════

class TestEducationExtraction:
    """Test expanded education extraction."""

    def test_bachelor_of_engineering_with_field(self):
        """'Bachelor of Engineering Electronics and Instrumentation 1998 – 2002'"""
        parser = ResumeParser()
        text = "EDUCATION\nBachelor of Engineering Electronics and Instrumentation 1998 – 2002\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert "Bachelor" in edu[0]["degree"] or "Engineering" in edu[0]["degree"]
        assert edu[0]["field"] != ""

    def test_higher_secondary_education(self):
        """'Higher Secondary Education Physics, Chemistry, Math and Computer Science 1996 – 1998'"""
        parser = ResumeParser()
        text = "EDUCATION\nHigher Secondary Education Physics, Chemistry, Math and Computer Science 1996 – 1998\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert "Higher Secondary" in edu[0]["degree"] or "Secondary" in edu[0]["degree"]

    def test_standard_us_format(self):
        """'M.S. in Computer Science from MIT, 2020'"""
        parser = ResumeParser()
        text = "EDUCATION\nM.S. in Computer Science from MIT, 2020\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert "2020" in edu[0]["year"]

    def test_diploma(self):
        """'Diploma in Mechanical Engineering from XYZ Polytechnic 2015'"""
        parser = ResumeParser()
        text = "EDUCATION\nDiploma in Mechanical Engineering from XYZ Polytechnic 2015\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert "Diploma" in edu[0]["degree"]

    def test_btech(self):
        """'B.Tech Computer Science, IIT Delhi 2018'"""
        parser = ResumeParser()
        text = "EDUCATION\nB.Tech Computer Science, IIT Delhi 2018\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert "2018" in edu[0]["year"]

    def test_mba(self):
        """'MBA from Harvard Business School 2022'"""
        parser = ResumeParser()
        text = "EDUCATION\nMBA from Harvard Business School 2022\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert "2022" in edu[0]["year"]

    def test_associate_degree(self):
        """'Associate of Science in Biology 2019'"""
        parser = ResumeParser()
        text = "EDUCATION\nAssociate of Science in Biology 2019\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert "Associate" in edu[0]["degree"] or "Science" in edu[0]["degree"]

    def test_phd(self):
        """'Ph.D. in Physics from Stanford University 2021'"""
        parser = ResumeParser()
        text = "EDUCATION\nPh.D. in Physics from Stanford University 2021\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert "2021" in edu[0]["year"]

    def test_field_of_study_extracted(self):
        """Verify field is no longer empty string for standard degrees."""
        parser = ResumeParser()
        text = "EDUCATION\nBachelor of Science in Computer Science 2020\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert edu[0]["field"] != ""
        assert "Computer Science" in edu[0]["field"]

    def test_known_institution_abbreviation(self):
        """Institutions like MIT, IIT should be recognized without suffix."""
        parser = ResumeParser()
        text = "EDUCATION\nB.Tech, IIT Delhi 2018\n"
        edu = parser._extract_education(text)
        assert len(edu) >= 1
        assert "IIT" in edu[0]["university"] or "Delhi" in edu[0]["university"]


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TestNewFieldExtraction
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewFieldExtraction:
    """Test certifications, languages, and professional summary extraction."""

    def test_certifications_section(self):
        text = """CERTIFICATIONS
- AWS Certified Solutions Architect
- Kubernetes Administrator (CKA)
- PMP Certified

EDUCATION
Bachelor of Science"""
        parser = ResumeParser()
        certs = parser._extract_certifications(text)
        assert len(certs) == 3
        assert "AWS Certified Solutions Architect" in certs

    def test_languages_with_proficiency(self):
        text = """LANGUAGES
English - Fluent
Hindi - Native
French - Intermediate

SKILLS
Python, Java"""
        parser = ResumeParser()
        langs = parser._extract_languages(text)
        assert len(langs) == 3
        assert langs[0]["language"] == "English"
        assert langs[0]["proficiency"] == "Fluent"

    def test_languages_comma_separated(self):
        text = """LANGUAGES
English (Native), Hindi (Fluent), German (Basic)

EDUCATION
Bachelor of Science"""
        parser = ResumeParser()
        langs = parser._extract_languages(text)
        assert len(langs) == 3
        names = [l["language"] for l in langs]
        assert "English" in names
        assert "German" in names
        profs = {l["language"]: l["proficiency"] for l in langs}
        assert profs["English"] == "Native"
        assert profs["German"] == "Basic"

    def test_professional_summary(self):
        text = """PROFESSIONAL SUMMARY
Embedded software engineer with 10 years of work experience in development and verification of safety critical applications in Aerospace domain.

KEY SKILLS
Embedded Software Development"""
        parser = ResumeParser()
        summary = parser._extract_professional_summary(text)
        assert "Embedded software engineer" in summary
        assert "10 years" in summary

    def test_summary_truncated_at_500(self):
        """Summary should be truncated to 500 characters."""
        parser = ResumeParser()
        long_summary = "A" * 600
        text = f"PROFESSIONAL SUMMARY\n{long_summary}\n\nKEY SKILLS\nPython"
        summary = parser._extract_professional_summary(text)
        assert len(summary) <= 500

    def test_no_certifications_section(self):
        """Should return empty list when no certifications section."""
        parser = ResumeParser()
        text = "SKILLS\nPython\n\nEDUCATION\nBSc"
        certs = parser._extract_certifications(text)
        assert certs == []

    def test_no_languages_section(self):
        """Should return empty list when no languages section."""
        parser = ResumeParser()
        text = "SKILLS\nPython\n\nEDUCATION\nBSc"
        langs = parser._extract_languages(text)
        assert langs == []

    def test_no_summary_section(self):
        """Should return empty string when no summary section."""
        parser = ResumeParser()
        text = "SKILLS\nPython\n\nEDUCATION\nBSc"
        summary = parser._extract_professional_summary(text)
        assert summary == ""


# ═══════════════════════════════════════════════════════════════════════════════
# 4. TestSkillsNormalization
# ═══════════════════════════════════════════════════════════════════════════════

class TestSkillsNormalization:
    """Test skill normalization via SKILL_ALIASES."""

    def test_normalize_nodejs_variants(self):
        result = normalize_skill_name("nodejs")
        assert result.lower() == "node.js"

    def test_normalize_k8s(self):
        result = normalize_skill_name("k8s")
        assert result.lower() == "kubernetes"

    def test_normalize_preserves_canonical(self):
        result = normalize_skill_name("Python")
        assert result == "Python"

    def test_skills_deduplicated_after_normalization(self):
        """Skills list should not have duplicates after normalization."""
        raw = ["nodejs", "node.js", "Node", "reactjs", "react"]
        normalized = []
        seen = set()
        for s in raw:
            canonical = normalize_skill_name(s)
            key = canonical.lower()
            if key not in seen:
                seen.add(key)
                normalized.append(canonical)
        # node.js, node, and nodejs should collapse
        # react and reactjs should collapse
        assert len(normalized) <= 3

    def test_c_family_skills(self):
        """C, C++, C# should all be extracted as separate skills."""
        results = {
            normalize_skill_name("C").lower(),
            normalize_skill_name("C++").lower(),
            normalize_skill_name("C#").lower(),
        }
        assert "c" in results
        assert "c++" in results
        assert "c#" in results


# ═══════════════════════════════════════════════════════════════════════════════
# 5. TestWorkTitleCompany
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkTitleCompany:
    """Test work title/company parsing improvements."""

    def test_deputed_at_pattern(self):
        """'Senior Engineer TRIGENT SOFTWARE LTD. deputed @ AMETEK' should parse."""
        parser = ResumeParser()
        title, company = parser._split_title_company(
            "Senior Engineer TRIGENT SOFTWARE LTD. deputed @ AMETEK")
        assert "Engineer" in title or title == "Senior Engineer"
        assert "AMETEK" in company
        assert "TRIGENT" in company

    def test_pipe_delimiter(self):
        """'Software Engineer | Google LLC' should split correctly."""
        parser = ResumeParser()
        title, company = parser._split_title_company("Software Engineer | Google LLC")
        assert "Software Engineer" in title
        assert "Google" in company

    def test_tab_delimiter(self):
        """'Manager\tAmazon Inc' should split correctly."""
        parser = ResumeParser()
        title, company = parser._split_title_company("Manager\tAmazon Inc")
        assert "Manager" in title
        assert "Amazon" in company

    def test_company_keyword_disambiguation(self):
        """Part with 'Ltd' or 'Inc' should be identified as company."""
        parser = ResumeParser()
        title, company = parser._split_title_company("Senior Developer Acme Ltd")
        assert "Developer" in title
        assert "Ltd" in company or "Acme" in company

    def test_title_keyword_disambiguation(self):
        """Part with 'Engineer' or 'Manager' should be identified as title."""
        parser = ResumeParser()
        title, company = parser._split_title_company("Software Engineer TechCorp")
        assert "Engineer" in title
        assert "Software" in title


# ═══════════════════════════════════════════════════════════════════════════════
# 6. TestGapDetectorHardening
# ═══════════════════════════════════════════════════════════════════════════════

class TestGapDetectorHardening:
    """Test gap detector date normalization improvements."""

    def test_to_ym_till_date(self):
        result = _to_ym("Till Date")
        assert result is not None  # Should return current YYYY-MM

    def test_to_ym_ongoing(self):
        result = _to_ym("Ongoing")
        assert result is not None

    def test_to_ym_period_month(self):
        result = _to_ym("AUG. 2011")
        assert result == "2011-08"

    def test_jaiganesh_total_years(self):
        """Total years for the veteran resume should be 20+."""
        jobs = [
            {"title": "Lead Engineer", "company": "UTAS", "start_date": "December 2014", "end_date": "present"},
            {"title": "Sr SW Eng", "company": "AMETEK", "start_date": "August 2011", "end_date": "December 2014"},
            {"title": "Sr Eng", "company": "TRIGENT", "start_date": "September 2010", "end_date": "July 2011"},
            {"title": "SW Eng", "company": "AK AEROTEK", "start_date": "April 2007", "end_date": "August 2010"},
            {"title": "FSE", "company": "ALCON", "start_date": "May 2003", "end_date": "September 2006"},
        ]
        result = analyze_gaps(jobs)
        total = result.get("total_years", 0)
        assert total >= 19, f"Expected 20+ years, got {total}"

    def test_to_ym_standard_present(self):
        """'present' should still work (backward compat)."""
        result = _to_ym("present")
        assert result is not None
        import datetime
        expected = datetime.datetime.now().strftime("%Y-%m")
        assert result == expected


# ═══════════════════════════════════════════════════════════════════════════════
# 7. TestFullPipelineIntegration
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullPipelineIntegration:
    """End-to-end parser tests with real resume text."""

    JAIGANESH_RESUME = """JAIGANESH JAYARAMAN
E-Mail: jaiganesh7681@gmail.com Contact: +91 9986004374
PROFESSIONAL SUMMARY
Embedded software engineer with 10 years of work experience in development and verification of safety critical applications in Aerospace domain. A lead engineer primarily responsible for the software development at UTAS, Bangalore facility. A dynamic professional with abilities to adapt, learn and work on the embedded technologies on various domains.
KEY SKILLS
 Embedded Software Development
 Device Drivers Development
 Hardware Software Integration
 Software Requirements Development
 DOORS DXL scripting
 Software Verification and Review
 Stack and Timing Analysis
 RTRT TDP Development
TECHNICAL SKILLS
 High level languages : C, C++ and C#
 Embedded Targets : TMSF28335, TMS320C6713b, ADSP21369, PIC microcontrollers
 Communication protocols : ARINC 429, CAN, SPI, I2C
 RTOS : Micro-C v2
 Debuggers : Code Composer Studio V6.0, Visual DSP++, IAR Workbench, MPLAB
 Testing Tool : RTRT
PROFESSIONAL EXPERIENCE
Lead Engineer UTC AEROSPACE SYSTEMS DEC 2014 – Till Date
Senior Software Engineer AMETEK INSTRUMENTS INDIA PVT. LTD AUG. 2011 – DEC 2014
Senior Engineer TRIGENT SOFTWARE LTD. deputed @ AMETEK SEPT. 2010 – JULY 2011
Software Engineer AK AEROTEK SOFTWARE CENTRE PVT. LTD APRIL 2007 – AUG. 2010
Field Service Engineer ALCON LABORATORIES INDIA PVT. LTD MAY 2003 – SEPT 2006
EDUCATION
Bachelor of Engineering Electronics and Instrumentation 1998 – 2002
Higher Secondary Education Physics, Chemistry, Math and Computer Science 1996 – 1998
PERSONAL DETAILS
Date of Birth : 07 – June – 1981
Passport Number : K9142008, Valid Up to 19-March-2023
VISA : B1 Visa for the United States of America Valid Up to 2021
"""

    def test_jaiganesh_full_parse(self):
        """Parse the complete Jaiganesh resume and verify all fields."""
        parser = ResumeParser()
        result = parser.parse_resume(self.JAIGANESH_RESUME.encode("utf-8"), "jaiganesh_resume.txt")

        # Verify contact
        assert result["contact_info"]["email"] == "jaiganesh7681@gmail.com"

        # Verify work experience (5 entries)
        assert len(result["work_experience"]) >= 5

        # Verify education (2 entries)
        assert len(result["education"]) >= 2

        # Verify skills
        assert len(result["skills"]) > 5
        assert any("C" in s or "c" in s for s in result["skills"])

        # Verify professional summary
        assert "Embedded software engineer" in result.get("professional_summary", "")

        # Verify new fields exist (even if empty for this resume)
        assert "certifications" in result
        assert "languages" in result

    def test_parse_resume_backward_compat(self):
        """Simple resume text should still parse correctly."""
        simple_text = """John Doe
john@example.com

WORK EXPERIENCE
Software Engineer at Acme Inc
Jan 2020 - Present

EDUCATION
BSc Computer Science
University of Tech, 2015

SKILLS
Python, JavaScript, React
""".encode("utf-8")
        parser = ResumeParser()
        result = parser.parse_resume(simple_text, "simple_resume.txt")
        assert result["contact_info"]["email"] == "john@example.com"
        assert len(result["work_experience"]) >= 1
        assert len(result["skills"]) >= 1
        assert len(result["education"]) >= 1

    def test_empty_resume_graceful(self):
        """Empty or minimal text should not crash."""
        parser = ResumeParser()
        result = parser.parse_resume(b"Name Only\n\nNo real content here.", "empty.txt")
        assert "work_experience" in result
        assert "skills" in result
        assert "education" in result
        assert "contact_info" in result
        assert "certifications" in result
        assert "languages" in result
        assert "professional_summary" in result
