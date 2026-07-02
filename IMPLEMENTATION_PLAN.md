# Multi-Industry Enhancement Implementation Plan

## Objective
Transform the Resume AI application from tech-focused to a go-to solution for any industry recruiters, targeting 90% accuracy across all domains.

---

## Phase 1: Industry-Specific Scoring Weights (Items 1-3)

### Why
Currently all industries use the same weights (30% skills, 20% experience, etc.). This doesn't reflect real-world priorities:
- **Sales**: Quota attainment > years of experience
- **Healthcare**: Certifications > specific tools
- **Finance**: CPA/CFA > generic accounting skills

### Implementation

#### 1.1 Add Industry Weight Profiles to constants.py
```python
INDUSTRY_WEIGHTS = {
    "default": {
        "skills": 0.30, "experience": 0.20, "architecture": 0.15,
        "education": 0.10, "timeline": 0.10, "domain": 0.10, "risk": 0.15,
    },
    "healthcare": {
        "skills": 0.20, "experience": 0.25, "certifications": 0.25,
        "education": 0.15, "domain": 0.10, "risk": 0.05,
    },
    "finance": {
        "skills": 0.15, "experience": 0.20, "certifications": 0.30,
        "education": 0.20, "domain": 0.10, "risk": 0.05,
    },
    "sales": {
        "skills": 0.15, "experience": 0.20, "achievements": 0.30,
        "domain": 0.15, "education": 0.10, "risk": 0.10,
    },
    "hr": {
        "skills": 0.20, "experience": 0.30, "certifications": 0.20,
        "education": 0.15, "domain": 0.10, "risk": 0.05,
    },
    "legal": {
        "skills": 0.15, "experience": 0.30, "certifications": 0.25,
        "education": 0.20, "domain": 0.05, "risk": 0.05,
    },
    "manufacturing": {
        "skills": 0.25, "experience": 0.25, "certifications": 0.15,
        "education": 0.15, "domain": 0.15, "risk": 0.05,
    },
    "operations": {
        "skills": 0.20, "experience": 0.30, "education": 0.15,
        "domain": 0.20, "risk": 0.15,
    },
}
```

#### 1.2 Update fit_scorer.py
- Add `industry` parameter to `compute_fit_score`
- Look up industry-specific weights
- Fall back to default if industry not found

#### 1.3 Update hybrid_pipeline.py
- Pass detected industry to scoring functions
- Add industry detection from JD domain

---

## Phase 2: Non-Tech JD Parsing Validation (Items 4-6)

### Why
Domain keywords exist but aren't validated. Need tests to ensure parsing works for real-world non-tech JDs.

### Implementation

#### 2.1 Add JD Parsing Tests for Each Industry
Create test cases in `test_hybrid_pipeline.py`:

```python
class TestNonTechJDParsing:
    """Test JD parsing for non-technical industries."""

    def test_hr_manager_jd_parsing(self):
        """HR Manager JD should extract: domain=hr, relevant skills."""
        jd = """
        HR Manager
        We are looking for an experienced HR Manager to lead our people operations.
        Requirements:
        - 5+ years HR experience
        - SHRM-CP or PHR certification preferred
        - Experience with Workday, BambooHR
        - Strong knowledge of employment law
        """
        result = parse_jd_rules(jd)
        assert result["domain"] == "hr"
        assert result["required_years"] >= 5
        # ... more assertions

    def test_financial_analyst_jd_parsing(self):
        """Financial Analyst JD should extract: domain=finance, skills."""
        # ... similar structure

    def test_sales_representative_jd_parsing(self):
        """Sales Rep JD should extract: domain=sales, skills."""
        # ... similar structure
```

#### 2.2 Add End-to-End Tests
Test the full pipeline with real non-tech JDs and resumes.

#### 2.3 Add Edge Case Tests
- Empty JD
- Very short JD (<50 chars)
- JD with multiple domains (ambiguous)
- JD with typos

---

## Phase 3: Skill Taxonomy Expansion (Items 7-9)

### Why
Current taxonomy is tech-focused. Non-tech industries need:
- Certifications as first-class (PMP, CPA, RN)
- Industry-specific tools (Epic, QuickBooks)
- Soft skills scoring

### Implementation

#### 3.1 Expand MASTER_SKILLS
Add to `skill_matcher.py`:
```python
# Healthcare certifications
"registered nurse", "rn", "licensed practical nurse", "lpn",
"certified medical assistant", "cma", "cpc", "rhit", "rhia",
"Epic", "Cerner", "Meditech", "eClinicalWorks",

# Finance certifications
"cpa", "cfa", "cma", "cfp", "enrolled agent",
"QuickBooks", "Xero", "Sage", "NetSuite",

# HR certifications
"shrm-cp", "shrm-scp", "phr", "sphr", "aPHR",
"Workday", "BambooHR", "ADP", "Greenhouse", "Lever",

# Project management
"pmp", "prince2", "capm", "msp", "pmo",
```

#### 3.2 Add Certification Scoring
Update scoring to weight certifications higher in relevant industries.

#### 3.3 Soft Skills for Non-Tech
Add soft skills to nice-to-have scoring for non-tech roles (leadership, communication).

---

## Phase 4: Accuracy Monitoring (Items 10-12)

### Why
No visibility into real-world accuracy. Need metrics to validate 90% target.

### Implementation

#### 4.1 Track Recruiter Overrides
Add to database:
```python
class ScreeningResultOverride(Base):
    """Tracks when recruiters override AI recommendation."""
    original_recommendation = Column(String)  # shortlist/consider/reject
    final_recommendation = Column(String)
    override_reason = Column(String)
    industry = Column(String)
    tenant_id = Column(Integer)
```

#### 4.2 A/B Testing Framework
Add feature flag system for scoring variants:
```python
# Track which variant performed better
class ScoringExperiment(Base):
    experiment_name = Column(String)
    variant = Column(String)  # "control" or "treatment"
    recommendation = Column(String)
    override_occurred = Column(Boolean)
```

#### 4.3 Accuracy Dashboard Data
Add endpoints to query:
- Override rate by industry
- Fit score distribution by industry
- Time to hire correlation

---

## Phase 5: Quick UX Wins (Items 13-16)

### Why
High impact, low effort improvements that immediately add value.

### Implementation

#### 5.1 Industry Selector Dropdown
Add to analyze endpoint:
```python
class AnalyzeRequest(BaseModel):
    # ... existing fields
    industry: Optional[str] = None  # auto-detected if not provided
```

Frontend adds dropdown with options: "Auto-detect", "Technology", "Healthcare", "Finance", "Sales", "HR", "Legal", "Manufacturing", "Operations", "Other"

#### 5.2 Confidence Scores on Matches
Update skill matching to return:
```python
{
    "matched_skills": [
        {"skill": "python", "confidence": 1.0},  # exact match
        {"skill": "postgresql", "confidence": 0.95},  # alias match
        {"skill": "react", "confidence": 0.8},  # substring match
    ]
}
```

#### 5.3 Skill Evidence Quotes
When confirming skills in resume text, capture the matching snippet:
```python
{
    "skill": "project management",
    "found": True,
    "evidence": "Led cross-functional project teams...",
    "location": "line 45"
}
```

#### 5.4 Missing Skill Explanations
Add adjacent skill suggestions:
```python
{
    "missing_required": ["python"],
    "suggestions": {
        "python": ["django", "flask"]  # adjacent skills candidate has
    }
}
```

---

## Phase 6: JD Templates (Item 17)

### Why
Non-technical recruiters need help writing JDs that the system can parse effectively.

### Implementation

Create template library:
```python
JD_TEMPLATES = {
    "hr_manager": {
        "title": "HR Manager",
        "description": "Lead people operations...",
        "required_skills": ["employee relations", "performance management"],
        "nice_to_have": ["shrm-cp", "workday"],
    },
    "sales_representative": {
        "title": "Account Executive",
        "description": "Drive revenue growth...",
        "required_skills": ["crm", "pipeline management"],
        "nice_to_have": ["salesforce", "hubspot"],
    },
    # ... more templates
}
```

Expose via API: `GET /api/jd-templates` and `POST /api/jd-templates/generate`

---

## Execution Order

| Week | Focus | Items |
|------|-------|-------|
| 1 | Industry Weights | 1, 2, 3 |
| 2 | Test Coverage | 4, 5, 6 |
| 3 | Skill Taxonomy | 7, 8, 9 |
| 4 | Monitoring | 10, 11, 12 |
| 5 | UX Improvements | 13, 14, 15, 16 |
| 6 | Templates + Regression | 17, 18, 19 |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Override rate | <20% (80% accuracy) |
| Domain detection accuracy | >90% |
| Non-tech JD parsing success | >85% |
| Recruiter satisfaction | >4/5 |
