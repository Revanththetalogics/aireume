# Agent Pipeline (LangGraph)

<cite>
**Referenced Files in This Document**
- [agent_pipeline.py](file://app/backend/services/agent_pipeline.py)
- [skill_matcher.py](file://app/backend/services/skill_matcher.py)
- [onet_validator.py](file://app/backend/services/onet/onet_validator.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [llm_service.py](file://app/backend/services/llm_service.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [main.py](file://app/backend/main.py)
- [test_agent_pipeline.py](file://app/backend/tests/test_agent_pipeline.py)
- [test_onet_integration.py](file://app/backend/tests/test_onet_integration.py)
- [pii_redaction_service.py](file://app/backend/services/pii_redaction_service.py)
- [guardrail_service.py](file://app/backend/services/guardrail_service.py)
- [weight_mapper.py](file://app/backend/services/weight_mapper.py)
- [constants.py](file://app/backend/services/constants.py)
- [fit_scorer.py](file://app/backend/services/fit_scorer.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced agent pipeline integration with new structured skills approach, passing both structured and text-scanned skills to the matching system
- Improved integration with enhanced skill matching validation mechanisms and ONET validation system
- Added comprehensive O*NET occupation-aware validation for skill matching with high-collision skill filtering
- Implemented sophisticated three-tier skill matching architecture with structured, text-scanned, and fuzzy matching
- Enhanced anti-hallucination guardrails with occupation-aware skill validation
- Integrated ONET validation into the agent pipeline result assembly for enriched skill analysis

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Enhanced Interview Kit Generation System](#enhanced-interview-kit-generation-system)
7. [Anti-Hallucination Guardrails](#anti-hallucination-guardrails)
8. [PII Redaction Integration](#pii-redaction-integration)
9. [Deterministic LLM Behavior](#deterministic-llm-behavior)
10. [Enhanced Truncation Limits](#enhanced-truncation-limits)
11. [Cloud-Aware Configuration Management](#cloud-aware-configuration-management)
12. [Timeout Configuration and Management](#timeout-configuration-and-management)
13. [JSON Serialization Handling](#json-serialization-handling)
14. [Dependency Analysis](#dependency-analysis)
15. [Performance Considerations](#performance-considerations)
16. [Troubleshooting Guide](#troubleshooting-guide)
17. [Conclusion](#conclusion)
18. [Appendices](#appendices)

## Introduction
This document describes the LangGraph-based multi-agent analysis pipeline that powers complex, step-by-step reasoning workflows for resume and job description evaluation. The pipeline integrates with Ollama models to enable structured extraction, matching, scoring, and comprehensive interview kit generation. It emphasizes deterministic, schema-bound outputs, robust fallbacks, and graceful degradation when LLM calls fail. The system is designed to support both non-streaming batch processing and streaming SSE responses, while complementing a hybrid approach that combines Python-first determinism with a single LLM narrative.

**Updated** Enhanced with sophisticated three-tier skill matching architecture that integrates structured skills, text-scanned skills, and fuzzy matching with comprehensive O*NET occupation-aware validation for improved accuracy and reduced false positives.

## Project Structure
The agent pipeline is implemented as a LangGraph StateGraph with three sequential nodes:
- Stage 1 (parallel within stage): jd_parser
- Stage 2 (parallel): resume_analyser (combines resume parsing, skill matching, and education/timeline analysis)
- Stage 3 (parallel): scorer (interview question generation with fallback scoring)

```mermaid
graph TB
subgraph "LangGraph Pipeline"
A["START"] --> B["jd_parser"]
B --> C["resume_analyser"]
C --> D["scorer"]
D --> E["END"]
end
```

**Diagram sources**
- [agent_pipeline.py:1022-1037](file://app/backend/services/agent_pipeline.py#L1022-L1037)

**Section sources**
- [agent_pipeline.py:4-24](file://app/backend/services/agent_pipeline.py#L4-L24)
- [agent_pipeline.py:1022-1037](file://app/backend/services/agent_pipeline.py#L1022-L1037)

## Core Components
- StateGraph and State: The pipeline defines a strongly-typed state interface that carries inputs, intermediate outputs, and accumulated errors across nodes.
- LLM singletons: Fast and reasoning LLM clients are created once and reused to reduce connection overhead and improve throughput.
- **Updated** Enhanced skill matching system: Three-tier architecture with structured skills (Tier 0), text-scanned skills (Tier 2), and fuzzy matching with O*NET validation for improved accuracy.
- **Updated** O*NET integration: Occupation-aware skill validation that filters high-collision skills and prevents false positives through authoritative skill validation.
- **Updated** Enhanced interview kit generation: Sophisticated scoring prompts that incorporate comprehensive role and candidate context for targeted question generation.
- Anti-hallucination guardrails: Comprehensive systems to prevent hallucinations including cache versioning, circuit breakers, and rule-based fallbacks.
- PII redaction integration: Automatic removal of personally identifiable information to eliminate bias from personal identifiers in resume analysis.
- Deterministic LLM behavior: Fixed seeds and controlled temperature settings for reproducible results.
- Enhanced truncation limits: Increased character limits for job descriptions and resumes to capture complete context.
- Intelligent keep_alive management: Cost-efficient cloud deployments disable keep_alive to avoid unnecessary charges.
- Timeout management: Consistent timeout handling using `_llm_request_timeout` constant for predictable LLM behavior.
- Node implementations:
  - jd_parser: Extracts structured job requirements from raw job descriptions with hallucination detection.
  - resume_analyser: Parses candidate profiles, identifies skills using enhanced three-tier matching, and computes education and timeline scores with PII redaction.
  - **Updated** scorer: Generates comprehensive interview questions with fallback mechanisms, delegating numerical scoring to deterministic components.
- Result assembly: Converts the final state into a unified response compatible with the existing API schema, including O*NET validation enrichment.
- JSON serialization: Comprehensive handling of datetime, date, and Decimal objects for proper serialization.

**Section sources**
- [agent_pipeline.py:209-226](file://app/backend/services/agent_pipeline.py#L209-L226)
- [agent_pipeline.py:137-204](file://app/backend/services/agent_pipeline.py#L137-L204)
- [agent_pipeline.py:357-473](file://app/backend/services/agent_pipeline.py#L357-L473)
- [agent_pipeline.py:581-654](file://app/backend/services/agent_pipeline.py#L581-L654)
- [agent_pipeline.py:731-955](file://app/backend/services/agent_pipeline.py#L731-L955)
- [agent_pipeline.py:1068-1158](file://app/backend/services/agent_pipeline.py#L1068-L1158)

## Architecture Overview
The agent pipeline orchestrates three specialized agents with comprehensive anti-hallucination guardrails, enhanced skill matching, and cloud-aware configuration management:
- Agent 1 (jd_parser): Parses job descriptions into canonical fields with hallucination detection and rule-based fallback.
- Agent 2 (resume_analyser): Builds a candidate profile with PII redaction, matches skills using three-tier architecture with O*NET validation, and evaluates education and timeline.
- **Updated** Agent 3 (scorer): Generates comprehensive interview questions with fallback mechanisms, while delegating numerical scoring to deterministic components.

```mermaid
sequenceDiagram
participant Client as "Caller"
participant Graph as "StateGraph"
participant JD as "jd_parser"
participant RA as "resume_analyser"
participant SC as "scorer"
participant O1 as "Fast LLM (cloud-aware)"
participant O2 as "Reasoning LLM (cloud-aware)"
Client->>Graph : "run_agent_pipeline(state)"
Graph->>JD : "invoke(state)"
JD->>O1 : "ainvoke(prompt) with hallucination detection"
O1-->>JD : "structured JSON"
JD->>JD : "validate skills against original JD"
JD->>JD : "increment hallucination counter if needed"
JD-->>Graph : "jd_analysis + errors"
Graph->>RA : "invoke(state)"
RA->>RA : "PII redaction service"
RA->>O1 : "ainvoke(prompt) with enhanced truncation"
O1-->>RA : "structured JSON"
RA->>RA : "Enhanced skill matching with O*NET validation"
RA->>RA : "Three-tier skill matching : structured + text-scanned + fuzzy"
RA->>RA : "Filter high-collision skills using O*NET"
RA-->>Graph : "candidate_profile + skill_analysis + edu_timeline_analysis + errors"
Graph->>SC : "invoke(state)"
SC->>SC : "Enhanced scoring prompt with role/candidate context"
SC->>O2 : "ainvoke(prompt) with deterministic settings"
O2-->>SC : "structured JSON with interview questions"
SC->>SC : "Generate fallback questions if LLM fails"
SC->>SC : "Delegate numerical scoring to deterministic components"
SC-->>Graph : "final_scores + interview_questions + errors"
Graph-->>Client : "assemble_result(final_state) with O*NET enrichment"
```

**Diagram sources**
- [agent_pipeline.py:1163-1190](file://app/backend/services/agent_pipeline.py#L1163-L1190)
- [agent_pipeline.py:357-473](file://app/backend/services/agent_pipeline.py#L357-L473)
- [agent_pipeline.py:581-654](file://app/backend/services/agent_pipeline.py#L581-L654)
- [agent_pipeline.py:731-955](file://app/backend/services/agent_pipeline.py#L731-L955)

## Detailed Component Analysis

### State Management and Graph Construction
- State schema: Defines inputs (raw texts, employment timeline, scoring weights), intermediate outputs (jd_analysis, candidate_profile, skill_analysis, edu_timeline_analysis, final_scores, interview_questions), and an errors accumulator.
- Graph edges: Sequential edges from START to jd_parser, then to resume_analyser, then to scorer, and finally to END.
- Compilation: The graph is compiled once at module load to reuse the compiled graph across requests.

```mermaid
classDiagram
class PipelineState {
+string raw_jd_text
+string raw_resume_text
+list employment_timeline
+dict scoring_weights
+dict jd_analysis
+dict candidate_profile
+dict skill_analysis
+dict edu_timeline_analysis
+dict final_scores
+dict interview_questions
+list errors
}
class StateGraph {
+add_node(id, callable)
+add_edge(src, dst)
+compile()
}
PipelineState <.. StateGraph : "typed state"
```

**Diagram sources**
- [agent_pipeline.py:209-226](file://app/backend/services/agent_pipeline.py#L209-L226)
- [agent_pipeline.py:1022-1037](file://app/backend/services/agent_pipeline.py#L1022-L1037)

**Section sources**
- [agent_pipeline.py:209-226](file://app/backend/services/agent_pipeline.py#L209-L226)
- [agent_pipeline.py:1022-1037](file://app/backend/services/agent_pipeline.py#L1022-L1037)

### Node: jd_parser
- Purpose: Extract canonical job requirements from raw job descriptions with hallucination detection and rule-based fallback.
- Behavior:
  - Uses a fast LLM with strict JSON schema and deterministic settings.
  - Implements an in-memory cache keyed by MD5 of the first 8000 characters of the job description plus prompt version to avoid repeated LLM calls for identical inputs.
  - Implements hallucination detection by comparing raw LLM output with validated skills and increments a counter when hallucinations are detected.
  - Uses circuit breaker mechanism that triggers rule-based fallback when hallucination threshold is exceeded.
  - On LLM failure, returns typed-null defaults and appends an error to the state's errors list.

```mermaid
flowchart TD
Start(["Call jd_parser_node(state)"]) --> LoadJD["Load raw_jd_text (8000 char limit)"]
LoadJD --> CacheKey["Compute MD5 of first 8000 chars + prompt version"]
CacheKey --> CacheHit{"Cache hit?"}
CacheHit --> |Yes| ReturnCache["Return cached jd_analysis"]
CacheHit --> |No| CheckCounter{"Hallucination counter < threshold?"}
CheckCounter --> |Yes| CallLLM["Call fast LLM with prompt"]
CheckCounter --> |No| RuleFallback["Use rule-based fallback"]
CallLLM --> Parse["Parse JSON with fallback"]
Parse --> ValidateSkills["Validate skills against original JD"]
ValidateSkills --> DetectHallucination{"Raw skills > Validated skills?"}
DetectHallucination --> |Yes| IncrementCounter["Increment hallucination counter"]
DetectHallucination --> |No| NoCounterChange["No counter change"]
RuleFallback --> Sanitize["Sanitize output"]
IncrementCounter --> Sanitize
NoCounterChange --> Sanitize
Sanitize --> StoreCache["Store in cache"]
StoreCache --> ReturnState["Return {jd_analysis}"]
ReturnCache --> End(["Exit"])
ReturnState --> End
```

**Diagram sources**
- [agent_pipeline.py:357-473](file://app/backend/services/agent_pipeline.py#L357-L473)

**Section sources**
- [agent_pipeline.py:357-473](file://app/backend/services/agent_pipeline.py#L357-L473)

### Node: resume_analyser
- Purpose: Combine resume parsing, enhanced skill matching with O*NET validation, education scoring, and timeline analysis into a single LLM call with PII redaction.
- Behavior:
  - Uses a fast LLM with a comprehensive prompt that includes role, domain, seniority, required skills, resume text, and employment timeline.
  - Integrates PII redaction service to eliminate bias from names, emails, phones, and other personal identifiers.
  - **Updated** Implements three-tier skill matching architecture:
    - Tier 0: Structured skills (from Skills section) - always accepted with highest confidence
    - Tier 1: Candidate skills (parser output) - accepted with validation
    - Tier 2: Text-scanned skills (low confidence) - promoted only with strict domain-context validation
  - **Updated** Integrates O*NET validation to filter high-collision skills and prevent false positives
  - Splits the flat combined output into three sub-dictionaries: candidate_profile, skill_analysis, and edu_timeline_analysis.
  - Applies defaults for missing or null fields to ensure schema completeness.
  - On LLM failure, returns typed-null defaults for all three sub-dictionaries and appends an error.
  - Properly serializes complex data structures using the `_json_default` function for datetime, date, and Decimal objects.

```mermaid
flowchart TD
Start(["Call resume_analyser_node(state)"]) --> BuildPrompt["Build combined prompt with JD + resume + timeline"]
BuildPrompt --> PII["PII redaction service"]
PII --> CallLLM["Call fast LLM"]
CallLLM --> Parse["Parse JSON with fallback"]
Parse --> Split["Split into CP/SA/ETA dicts"]
Split --> EnhancedSkills["Enhanced skill matching with O*NET validation"]
EnhancedSkills --> ThreeTier["Three-tier matching: structured + text-scanned + fuzzy"]
ThreeTier --> FilterHighCollision["Filter high-collision skills using O*NET"]
FilterHighCollision --> ApplyDefaults["Apply defaults for missing fields"]
ApplyDefaults --> ReturnState["Return {candidate_profile, skill_analysis, edu_timeline_analysis, errors}"]
ReturnState --> End(["Exit"])
```

**Diagram sources**
- [agent_pipeline.py:581-654](file://app/backend/services/agent_pipeline.py#L581-L654)

**Section sources**
- [agent_pipeline.py:581-654](file://app/backend/services/agent_pipeline.py#L581-L654)

### Enhanced Skill Matching Architecture
**Updated** The resume analyser now implements a sophisticated three-tier skill matching system:

#### Tier 0: Structured Skills (Highest Confidence)
- Skills extracted from dedicated Skills sections in resumes
- Always accepted regardless of collision status
- Highest confidence level for validation

#### Tier 1: Candidate Skills (Parser Output)
- Skills extracted from resume parsing with moderate confidence
- Subject to validation against job requirements and domain context

#### Tier 2: Text-Scanned Skills (Lowest Confidence)
- Skills extracted through full-text scanning with lowest confidence
- **Strict validation required**: Must pass domain-context validation to be accepted
- High-collision skills require 2+ context skills from same subcategory
- Non-collision skills require 1+ context skill from same domain

#### O*NET Validation Integration
- Validates matched skills against authoritative O*NET data
- Filters high-collision skills that O*NET deems invalid for the target occupation
- Prevents false positives like "railway" for data engineering roles
- Provides occupation match ratio and hot technology indicators

```mermaid
flowchart TD
A["Candidate Skills"] --> B["Tier 0: Structured Skills"]
A --> C["Tier 1: Candidate Skills"]
A --> D["Tier 2: Text-Scanned Skills"]
B --> E["Accept All"]
C --> F["Validate Against JD + Domain Context"]
D --> G["Strict Domain Validation"]
G --> H{"High-collision skill?"}
H --> |Yes| I["Require 2+ context skills from same subcategory"]
H --> |No| J["Require 1+ context skill from same domain"]
I --> K["Validate via O*NET"]
J --> K
F --> L["Validate via O*NET"]
E --> M["Combined Candidate Set"]
K --> M
L --> M
M --> N["Match Against JD Requirements"]
N --> O["O*NET Validation & Filtering"]
O --> P["Final Matched Skills"]
```

**Diagram sources**
- [skill_matcher.py:816-956](file://app/backend/services/skill_matcher.py#L816-L956)
- [skill_matcher.py:31-71](file://app/backend/services/skill_matcher.py#L31-L71)

**Section sources**
- [skill_matcher.py:816-956](file://app/backend/services/skill_matcher.py#L816-L956)
- [skill_matcher.py:31-71](file://app/backend/services/skill_matcher.py#L31-L71)

### Node: scorer
- Purpose: Generate comprehensive interview questions with fallback mechanisms, while delegating numerical scoring to deterministic components.
- Behavior:
  - Uses a reasoning LLM with a detailed prompt that includes all prior scores and contextual comments.
  - **Updated** Simplified scoring approach: Delegates numerical scoring to deterministic components while focusing on interview question generation.
  - **Updated** Integrates weight mapping system for new universal schema with 7-weight categories.
  - **Updated** Implements context-aware fallback question generation with technical, behavioral, and culture-fit questions.
  - **Updated** Uses deterministic LLM behavior with fixed seed (42) and controlled temperature (0.0) for reproducible results.
  - **Updated** Implements schema validation for interview questions with strict Pydantic models.
  - On LLM failure, computes a deterministic fallback using Python math and returns typed-null defaults for interview questions.

```mermaid
flowchart TD
Start(["Call scorer_node(state)"]) --> BuildPrompt["Build prompt with all prior scores/comments"]
BuildPrompt --> WeightMapping["Convert to new weight schema"]
WeightMapping --> CallLLM["Call reasoning LLM (seed=42, temp=0.0)"]
CallLLM --> Parse["Parse JSON with fallback"]
Parse --> ExtractIQ["Extract interview_questions from combined output"]
ExtractIQ --> ValidateSchema["Validate against ScorerResult schema"]
ValidateSchema --> Override["Override score_breakdown with agent scores"]
Override --> Clamp["Clamp fit_score to 0..100"]
Clamp --> Rec["Derive recommendation from fit_score"]
Rec --> GenerateFallback["Generate context-aware fallback questions"]
GenerateFallback --> ReturnState["Return {final_scores, interview_questions, errors}"]
ReturnState --> End(["Exit"])
```

**Diagram sources**
- [agent_pipeline.py:731-955](file://app/backend/services/agent_pipeline.py#L731-L955)

**Section sources**
- [agent_pipeline.py:731-955](file://app/backend/services/agent_pipeline.py#L731-L955)

### Result Assembly and Backward Compatibility
- The final state is transformed into a unified result dictionary that preserves backward compatibility with the existing AnalysisResponse schema while adding new fields produced by the LangGraph pipeline.
- **Updated** Enhanced with O*NET validation enrichment including occupation details, match ratios, and hot skills identification.
- Ensures that the frontend's "Stability" bar continues to render by mapping timeline to stability in the score breakdown.

**Section sources**
- [agent_pipeline.py:1068-1158](file://app/backend/services/agent_pipeline.py#L1068-L1158)

### Integration with Hybrid Approach
- While the LangGraph pipeline focuses on structured, schema-bound outputs and deterministic fallbacks, the hybrid pipeline provides a complementary approach:
  - Python-first deterministic scoring (skills, education, experience, domain/architecture, risk signals).
  - Single LLM call for narrative synthesis with robust fallbacks.
  - SSE streaming for progressive updates.
- The hybrid pipeline is used by the main API routes, while the LangGraph pipeline remains available for specialized use cases requiring strict schema-bound outputs and multi-step reasoning.

**Section sources**
- [hybrid_pipeline.py:1-11](file://app/backend/services/hybrid_pipeline.py#L1-L11)
- [analyze.py:304-311](file://app/backend/routes/analyze.py#L304-L311)

## Enhanced Interview Kit Generation System

**Updated** The agent pipeline now includes a sophisticated interview kit generation system that creates highly targeted, non-generic questions based on comprehensive role and candidate context, while simplifying the scoring framework.

### Comprehensive Scoring Prompt with Interview Kit Rules
The scorer node uses an enhanced prompt that incorporates detailed role context and candidate context:

```mermaid
flowchart TD
A["Enhanced Scoring Prompt"] --> B["ROLE CONTEXT"]
B --> B1["Title: {role_title}"]
B --> B2["Domain: {domain}"]
B --> B3["Seniority: {seniority}"]
B --> B4["Key Responsibilities: {key_responsibilities}"]
B --> B5["Required Skills: {required_skills}"]
B --> B6["Nice-to-Have Skills: {nice_to_have_skills}"]
A --> C["CANDIDATE CONTEXT"]
C --> C1["Current Role: {current_role} at {current_company}"]
C --> C2["Career Summary: {career_summary}"]
C --> C3["Years Experience: {years_actual}y (role requires: {years_required}y)"]
C --> C4["Matched Skills: {matched_skills}"]
C --> C5["Missing Skills: {missing_skills}"]
C --> C6["Adjacent Skills: {adjacent_skills}"]
C --> C7["Architecture Assessment: {architecture_comment}"]
C --> C8["Domain Fit Assessment: {domain_fit_comment}"]
C --> C9["Timeline/Gap Assessment: {gap_interpretation}"]
A --> D["INTERVIEW KIT RULES"]
D --> D1["TECHNICAL QUESTIONS (5)"]
D --> D2["BEHAVIORAL QUESTIONS (3)"]
D --> D3["CULTURE-FIT QUESTIONS (2)"]
```

**Diagram sources**
- [agent_pipeline.py:660-728](file://app/backend/services/agent_pipeline.py#L660-L728)

### Context-Aware Fallback Question Generation
The system generates comprehensive fallback questions when LLM calls fail or produce invalid output:

#### Technical Questions (5 questions)
- **Missing Skills**: For each missing skill, create a scenario-based question that ties the skill to specific job responsibilities
- **Critical Matched Skills**: For 1-2 critical matched skills, create depth-probing questions testing expertise level
- **System Design**: Include system design questions when architecture comments mention gaps or role requires architecture decisions
- **Difficulty Calibration**: Use domain and seniority to calibrate question difficulty

#### Behavioral Questions (3 questions, STAR format)
- **Timeline Gap Address**: Address the biggest risk signal from gap/timeline assessment: {gap_interpretation}
- **Seniority-Specific Challenges**: Target senior roles (leadership/mentorship), mid roles (ownership), junior roles (learning agility)
- **Role Transition**: Probe motivation for moving from current role to target role

#### Culture-Fit Questions (2 questions)
- **Motivation**: Why this specific role given candidate's career trajectory
- **Work-Style Alignment**: Question tied to role context (fast-paced startup vs. structured enterprise, remote vs. on-site)

### Schema Validation for Interview Questions
The system implements strict schema validation for interview questions:

```python
class InterviewQuestions(BaseModel):
    technical_questions: List[str] = Field(default_factory=list, max_length=20)
    behavioral_questions: List[str] = Field(default_factory=list, max_length=20)
    culture_fit_questions: List[str] = Field(default_factory=list, max_length=20)
```

### Benefits of Enhanced Interview Kit Generation
- **Highly Targeted Questions**: Every question references specific skills, role responsibilities, or candidate resume context
- **Non-Generic Questions**: Avoids standard interview boilerplate like "Tell me about yourself"
- **Context Awareness**: Questions adapt to candidate's background, timeline gaps, and role requirements
- **Comprehensive Coverage**: Addresses technical competency, behavioral fit, and cultural alignment
- **Fallback Resilience**: Generates meaningful questions even when LLM calls fail
- **Schema Compliance**: Ensures interview questions meet strict validation requirements

**Section sources**
- [agent_pipeline.py:660-728](file://app/backend/services/agent_pipeline.py#L660-L728)
- [agent_pipeline.py:838-842](file://app/backend/services/agent_pipeline.py#L838-L842)
- [guardrail_service.py:107-126](file://app/backend/services/guardrail_service.py#L107-L126)

## Anti-Hallucination Guardrails

The agent pipeline now includes comprehensive anti-hallucination guardrails to ensure reliable and unbiased analysis results.

### Cache Versioning System
The pipeline implements a sophisticated cache versioning system to automatically invalidate cached results when prompts change:

```python
# Guardrail: Phase 2 — cache versioning. Changing the prompt invalidates old cache entries.
_PROMPT_VERSION = hashlib.md5(_JD_PARSER_PROMPT.encode()).hexdigest()[:8]
```

This system:
- Generates a hash of the current prompt to serve as a version identifier
- Includes the prompt version in cache keys to ensure cache invalidation when prompts change
- Prevents stale cached results from being used with updated prompts
- Automatically handles cache cleanup when prompt modifications occur

### Hallucination Detection and Circuit Breaker
The pipeline monitors hallucination rates and automatically falls back to rule-based parsing when thresholds are exceeded:

```python
# Guardrail: Phase 4 — circuit breaker for JD parser hallucinations.
_hallucination_counter: Dict[str, int] = {"count": 0, "last_reset": datetime.now().timestamp()}
_CIRCUIT_BREAKER_THRESHOLD = 5  # max hallucinations per hour before fallback to rules
```

Detection mechanism:
- Compares raw LLM output skills with validated skills against original job description
- Increments hallucination counter when raw skills exceed validated skills
- Resets counter hourly to prevent permanent fallback states
- Triggers rule-based fallback when threshold (5 hallucinations per hour) is exceeded

### Skill Validation Against Original Job Description
The pipeline validates extracted skills against the original job description to prevent hallucinations:

```python
def _validate_skills_against_text(skills: List[str], text: str) -> List[str]:
    """Filter out skills not found in the original text (hallucination guard)."""
    if not skills or not text:
        return []

    text_lower = text.lower()
    validated = []

    for skill in skills:
        if not skill or not isinstance(skill, str):
            continue

        skill_lower = skill.lower()

        # Direct substring match
        if skill_lower in text_lower:
            validated.append(skill)
            continue

        # Check aliases from the skill registry
        try:
            from app.backend.services.hybrid_pipeline import SKILL_ALIASES
            aliases = SKILL_ALIASES.get(skill_lower, [])
            if any(alias.lower() in text_lower for alias in aliases):
                validated.append(skill)
                continue
        except Exception:
            pass

        # Multi-word skill: check if any significant word (3+ chars) matches
        words = [w for w in skill_lower.split() if len(w) > 2]
        if words and any(word in text_lower for word in words):
            validated.append(skill)
            continue

    return validated
```

### Sanitization of JD Parser Output
The pipeline sanitizes extracted job requirements to ensure they meet predefined standards:

```python
def _sanitize_jd_output(data: dict, original_text: str) -> dict:
    """Post-process and sanitize JD parser output to remove hallucinations."""
    fallback = {
        "role_title": "", "domain": "other", "seniority": "mid",
        "required_skills": [], "required_years": 0,
        "nice_to_have_skills": [], "key_responsibilities": [],
    }

    if not isinstance(data, dict):
        return fallback

    # Ensure all expected keys exist
    for key, default in fallback.items():
        if key not in data or data[key] is None:
            data[key] = default

    # Validate skills against original text (hallucination guard)
    data["required_skills"] = _validate_skills_against_text(
        data.get("required_skills", []), original_text
    )
    data["nice_to_have_skills"] = _validate_skills_against_text(
        data.get("nice_to_have_skills", []), original_text
    )

    # Normalize seniority
    valid_seniority = set(SENIORITY_RANGES.keys()) | {"principal"}
    if data.get("seniority") not in valid_seniority:
        years = data.get("required_years", 0)
        if years >= SENIORITY_RANGES["senior"][0]:
            data["seniority"] = "senior"
        elif years >= SENIORITY_RANGES["mid"][0]:
            data["seniority"] = "mid"
        else:
            data["seniority"] = "junior"

    # Normalize domain
    valid_domains = {
        "backend", "frontend", "fullstack", "data_science", "ml_ai",
        "devops", "embedded", "mobile", "design", "management", "other"
    }
    if data.get("domain") not in valid_domains:
        data["domain"] = "other"

    # Clamp required_years
    try:
        data["required_years"] = max(0, min(50, int(data.get("required_years", 0))))
    except (ValueError, TypeError):
        data["required_years"] = 0

    # Ensure key_responsibilities is a list of strings
    responsibilities = data.get("key_responsibilities", [])
    if isinstance(responsibilities, list):
        data["key_responsibilities"] = [
            str(r) for r in responsibilities if r is not None
        ]
    else:
        data["key_responsibilities"] = []

    return data
```

### **Updated** O*NET Validation Integration
The pipeline now integrates comprehensive O*NET validation to prevent hallucinations and false positives:

```python
def match_skills_with_onet(
    candidate_skills, jd_skills, jd_text="", jd_nice_to_have=None, job_title=None,
    structured_skills=None, text_scanned_skills=None
):
    """Enhanced skill matching with O*NET occupation context.
    
    Falls back to standard match_skills if O*NET data is unavailable
    or no job_title is provided.
    """
    result = match_skills(candidate_skills, jd_skills, jd_nice_to_have,
                          structured_skills=structured_skills,
                          text_scanned_skills=text_scanned_skills)

    validator = _get_onet_validator()
    if validator is not None and validator.available and job_title:
        try:
            onet_result = validator.validate_skills_batch(
                [m for m in result.get("matched_skills", [])],
                job_title,
            )
            result["onet_validation"] = onet_result

            # Filter: remove high-collision skills that O*NET says are NOT valid for this occupation
            if onet_result.get("skill_validations"):
                invalid_high_collision = set()
                for skill_name, validation in onet_result["skill_validations"].items():
                    norm = _normalize_skill(skill_name)
                    if norm in HIGH_COLLISION_SKILLS and not validation.get("valid", True):
                        invalid_high_collision.add(skill_name)
                if invalid_high_collision:
                    result["matched_skills"] = [s for s in result["matched_skills"]
                                                if s not in invalid_high_collision]
                    result["onet_filtered"] = list(invalid_high_collision)
        except Exception as e:
            logger.warning("O*NET validation failed (non-fatal): %s", e)

    return result
```

### Benefits of Enhanced Anti-Hallucination Guardrails
- **Comprehensive Protection**: Multiple layers of hallucination prevention including cache versioning, skill validation, and circuit breakers
- **Automatic Fallback**: Seamless transition to rule-based parsing when hallucination thresholds are exceeded
- **Prompt Evolution Support**: Cache versioning ensures compatibility with prompt updates without manual intervention
- **Bias Elimination**: Skill validation prevents hallucinations that could lead to incorrect job requirements
- **Reliability**: Circuit breaker prevents cascading failures when hallucinations become frequent
- **Audit Trail**: Hallucination counter provides visibility into guardrail effectiveness
- **Enhanced Accuracy**: O*NET validation prevents false positives and improves skill matching precision

**Section sources**
- [agent_pipeline.py:349-350](file://app/backend/services/agent_pipeline.py#L349-L350)
- [agent_pipeline.py:357-473](file://app/backend/services/agent_pipeline.py#L357-L473)
- [agent_pipeline.py:246-304](file://app/backend/services/agent_pipeline.py#L246-L304)
- [agent_pipeline.py:262-268](file://app/backend/services/agent_pipeline.py#L262-L268)
- [skill_matcher.py:31-71](file://app/backend/services/skill_matcher.py#L31-L71)

## PII Redaction Integration

The agent pipeline now integrates comprehensive PII redaction to eliminate bias from personal identifiers in analysis results.

### PII Redaction Service Integration
The resume analyzer integrates with a dedicated PII redaction service to remove personally identifiable information:

```python
# Guardrail: Phase 3 — PII redaction to eliminate bias from names, emails, phones
raw_resume = state["raw_resume_text"]
try:
    from app.backend.services.pii_redaction_service import get_pii_service
    pii_service = get_pii_service()
    redaction_result = pii_service.redact_pii(raw_resume)
    resume_text = redaction_result.redacted_text
except Exception:
    resume_text = raw_resume  # fallback to raw text if redaction fails
```

### Enterprise-Grade PII Detection
The PII redaction service provides two modes of operation:

1. **Presidio Mode** (Enterprise-grade):
   - Uses advanced NLP libraries for accurate PII detection
   - Supports comprehensive entity types including PERSON, EMAIL_ADDRESS, PHONE_NUMBER, LOCATION, ORG, URL, US_SSN, CREDIT_CARD
   - Provides confidence scores for detection accuracy
   - Context-preserving anonymization with meaningful placeholders

2. **Regex Fallback Mode**:
   - Uses pattern matching for basic PII detection
   - Falls back automatically when Presidio is unavailable
   - Covers common patterns for emails, phone numbers, URLs, universities, and company names

### Redaction Result Tracking
The service provides comprehensive tracking of redaction activities:

```python
@dataclass
class RedactionResult:
    """Result of PII redaction operation."""
    redacted_text: str
    redaction_map: Dict[str, List[str]]
    redaction_count: int
    confidence_scores: Dict[str, float]
```

### Benefits of PII Redaction Integration
- **Bias Elimination**: Removes names, emails, phone numbers, and other identifiers that could introduce bias
- **Privacy Compliance**: Ensures candidate privacy is maintained throughout the analysis process
- **Enterprise-Grade Security**: Advanced detection algorithms with confidence scoring
- **Fallback Resilience**: Automatic fallback to regex patterns when advanced libraries are unavailable
- **Audit Trail**: Comprehensive tracking of redacted entities and confidence levels
- **Content Preservation**: Maintains analytical value while removing sensitive information

**Section sources**
- [agent_pipeline.py:603-611](file://app/backend/services/agent_pipeline.py#L603-L611)
- [pii_redaction_service.py:17-233](file://app/backend/services/pii_redaction_service.py#L17-L233)

## Deterministic LLM Behavior

The agent pipeline now ensures deterministic LLM behavior through fixed seeds and controlled temperature settings.

### Fixed Seed Implementation
Both LLM instances use fixed seeds to ensure reproducible results:

```python
# Fast LLM with fixed seed
_llm_kwargs = {
    "model": OLLAMA_FAST_MODEL,
    "base_url": OLLAMA_BASE_URL,
    "temperature": 0.0,
    "seed": 42,
    "format": "json",
    # ... other settings
}

# Reasoning LLM with fixed seed  
_llm_kwargs = {
    "model": OLLAMA_REASONING_MODEL,
    "base_url": OLLAMA_BASE_URL,
    "temperature": 0.0,
    "seed": 42,
    "format": "json",
    # ... other settings
}
```

### Controlled Temperature Settings
Temperature is set to 0.0 for both models to ensure deterministic behavior:

- **Temperature 0.0**: Produces the same output for the same input
- **Deterministic Results**: Eliminates randomness in LLM responses
- **Reproducible Analysis**: Ensures consistent results across runs

### Benefits of Deterministic LLM Behavior
- **Reproducibility**: Same inputs always produce same outputs
- **Debugging Support**: Easier to debug and trace analysis steps
- **Quality Control**: Consistent results for validation and testing
- **Audit Trail**: Predictable behavior enables comprehensive logging
- **Performance Optimization**: Eliminates need for multiple inference attempts

**Section sources**
- [agent_pipeline.py:137-204](file://app/backend/services/agent_pipeline.py#L137-L204)

## Enhanced Truncation Limits

The agent pipeline now uses significantly increased truncation limits to capture complete context for analysis.

### Increased Character Limits
The pipeline now processes up to 8000 characters from job descriptions and resumes:

```python
# Guardrail: increased truncation to capture full requirements section
jd_text = raw_jd_text[:8000]

# Guardrail: increased truncation to capture full resume context
resume_text = resume_text[:8000]
```

### Justification for Increased Limits
- **Complete Context**: Captures entire job descriptions and resumes for comprehensive analysis
- **Skill Coverage**: Ensures all required skills and candidate experiences are considered
- **Context Preservation**: Maintains important context for accurate matching and scoring
- **Reduced Ambiguity**: Minimizes the chance of missing critical information

### Benefits of Enhanced Truncation
- **Comprehensive Analysis**: Full context ensures accurate skill matching and evaluation
- **Reduced Errors**: Less likely to miss important requirements or experiences
- **Improved Accuracy**: Complete information leads to better recommendations
- **Bias Reduction**: Full context helps prevent incomplete analysis that could introduce bias

**Section sources**
- [agent_pipeline.py:379](file://app/backend/services/agent_pipeline.py#L379)
- [agent_pipeline.py:622](file://app/backend/services/agent_pipeline.py#L622)

## Cloud-Aware Configuration Management

The agent pipeline now includes comprehensive cloud-aware configuration management for optimal performance and cost efficiency with significantly enhanced token limits for cloud deployments.

### Cloud Detection and Authentication
The pipeline automatically detects Ollama Cloud deployments and handles authentication:

```python
def _is_ollama_cloud(base_url: str) -> bool:
    """Check if the base URL points to Ollama Cloud (ollama.com)."""
    return "ollama.com" in base_url.lower()

def _get_ollama_headers(base_url: str) -> Dict[str, str]:
    """Build headers for Ollama API requests. Adds Authorization header for cloud."""
    headers = {}
    if _is_ollama_cloud(base_url):
        api_key = os.getenv("OLLAMA_API_KEY", "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
    return headers
```

### Enhanced Dynamic Token Limits and Context Windows
The pipeline optimizes LLM configurations based on deployment type with significantly increased capacity for cloud deployments:

#### Fast LLM Configuration (Cloud vs Local)
```python
# Cloud models need significantly more tokens for verbose output
# Local: 600 tokens sufficient for combined schema
# Cloud: 3000 tokens for very large models (480B+) that generate extremely verbose output
_num_predict = 3000 if _is_cloud else 600
_num_ctx = 12288 if _is_cloud else 3072
```

#### Reasoning LLM Configuration (Cloud vs Local)
```python
# Cloud models need significantly more tokens for verbose output
# Local: 800 tokens sufficient for scorer + interview_questions
# Cloud: 4000 tokens for very large models (480B+) that generate extremely verbose output
_num_predict = 4000 if _is_cloud else 800
_num_ctx = 8192 if _is_cloud else 2048
```

### Intelligent Keep-Alive Management
Cost-efficient cloud deployments disable keep_alive to avoid unnecessary charges:

```python
# Keep model hot only for local Ollama
if not _is_cloud:
    _llm_kwargs["keep_alive"] = -1
```

### Enhanced Cloud Authentication Logging
The pipeline now includes comprehensive logging for cloud authentication and debugging:

```python
# Add headers for Ollama Cloud authentication
headers = _get_ollama_headers(OLLAMA_BASE_URL)
if headers:
    _llm_kwargs["headers"] = headers

# Keep model hot only for local Ollama
if not _is_cloud:
    _llm_kwargs["keep_alive"] = -1
```

### Benefits of Enhanced Cloud Configuration
- **Significantly Increased Capacity**: Cloud deployments now support up to 3000 tokens for fast LLM and 4000 tokens for reasoning LLM, representing a 2x increase from previous limits
- **Enhanced Context Windows**: Context windows expanded to 12288 for fast LLM and 8192 for reasoning LLM for cloud deployments
- **Improved Cost Optimization**: Cloud deployments automatically disable keep_alive to prevent unnecessary charges
- **Advanced Authentication Logging**: Comprehensive logging for Ollama Cloud authentication with detailed API key validation and cloud detection messages
- **Better Debugging Capabilities**: Enhanced logging provides better visibility into cloud deployment configuration and authentication status
- **Automatic Authentication**: Seamless Ollama Cloud authentication with API key support and proper error handling
- **Deployment Flexibility**: Transparent switching between cloud and local deployments without code changes
- **Resource Efficiency**: Optimized resource allocation based on deployment characteristics with significantly larger token limits for cloud models

**Section sources**
- [agent_pipeline.py:74-86](file://app/backend/services/agent_pipeline.py#L74-L86)
- [agent_pipeline.py:137-204](file://app/backend/services/agent_pipeline.py#L137-L204)

## Timeout Configuration and Management

The agent pipeline now includes comprehensive timeout management for reliable LLM interactions with enhanced cloud deployment support.

### _llm_request_timeout Constant
The `_llm_request_timeout` constant provides centralized timeout configuration for all LLM interactions:

```python
_llm_request_timeout = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "150")) + 30
```

This configuration:
- Reads timeout from environment variable `LLM_NARRATIVE_TIMEOUT` (default: 150 seconds)
- Adds 30 seconds buffer for HTTP transport overhead
- Provides consistent timeout across all LLM instances

### Fast LLM Timeout Configuration
The fast LLM instance uses the timeout constant for extraction and matching operations:

```python
def get_fast_llm() -> ChatOllama:
    # ... existing configuration ...
    request_timeout=_llm_request_timeout,
```

### Reasoning LLM Timeout Configuration
The reasoning LLM instance uses the same timeout constant for scoring and narrative synthesis:

```python
def get_reasoning_llm() -> ChatOllama:
    # ... existing configuration ...
    request_timeout=_llm_request_timeout,
```

### Timeout Consistency Across Pipelines
The timeout configuration ensures consistency between:
- **LangGraph Pipeline**: All three LLM calls use the same timeout
- **Hybrid Pipeline**: Separate timeout handling maintains compatibility
- **Direct LLM Service**: Independent timeout management for standalone operations

### Benefits of Centralized Timeout Management
- **Predictable Behavior**: Consistent timeout across all LLM interactions
- **Environment Flexibility**: Configurable via environment variables
- **Operational Reliability**: Prevents hanging LLM calls and resource exhaustion
- **Graceful Degradation**: Enables proper fallback mechanisms when timeouts occur
- **Enhanced Cloud Support**: Timeout management works seamlessly with cloud deployments and increased token limits

**Section sources**
- [agent_pipeline.py:127](file://app/backend/services/agent_pipeline.py#L127)
- [agent_pipeline.py:137-204](file://app/backend/services/agent_pipeline.py#L137-L204)

## JSON Serialization Handling

The agent pipeline now includes comprehensive JSON serialization handling for complex data types that are not natively JSON-serializable with enhanced support for cloud deployments.

### _json_default Function
The `_json_default` function serves as a custom JSON encoder that converts non-serializable Python objects to JSON-compatible formats:

```python
def _json_default(obj):
    """Handle non-serializable types for json.dumps (datetime, date, Decimal)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
```

### Usage Throughout the Pipeline
The `_json_default` function is used in multiple locations to ensure proper serialization:

1. **Resume Analyzer Prompt Building**:
   ```python
   required_skills=json.dumps(required_skills[:20], default=_json_default)
   timeline=json.dumps(state.get("employment_timeline", [])[:10], default=_json_default)
   ```

2. **Scorer Prompt Building**:
   ```python
   matched_skills=json.dumps(sa.get("matched_skills", [])[:8], default=_json_default)
   missing_skills=json.dumps(missing_skills[:8], default=_json_default)
   ```

3. **O*NET Validation Enrichment**:
   ```python
   onet_hot_skills=json.dumps([
       s["skill"] for s in onet.get("validated", [])
       if s.get("is_hot")
   ], default=_json_default)
   ```

### Supported Data Types
The JSON serialization handler supports the following non-JSON-serializable types:

- **datetime objects**: Converted to ISO format strings (YYYY-MM-DDTHH:MM:SS.mmmmmm)
- **date objects**: Converted to ISO format strings (YYYY-MM-DD)
- **Decimal objects**: Converted to float values

### Benefits
- **Type Safety**: Prevents JSON serialization errors when dealing with complex data structures
- **Consistency**: Ensures uniform serialization across all pipeline components
- **Backward Compatibility**: Maintains compatibility with existing JSON-based workflows
- **Error Prevention**: Eliminates runtime errors during JSON encoding operations
- **Enhanced Cloud Support**: Works seamlessly with increased token limits and larger context windows in cloud deployments

**Section sources**
- [agent_pipeline.py:49-55](file://app/backend/services/agent_pipeline.py#L49-L55)
- [agent_pipeline.py:620](file://app/backend/services/agent_pipeline.py#L620)
- [agent_pipeline.py:866](file://app/backend/services/agent_pipeline.py#L866)
- [agent_pipeline.py:1140-1144](file://app/backend/services/agent_pipeline.py#L1140-L1144)

## Dependency Analysis
- LangGraph integration: Uses StateGraph with typed state and node callbacks.
- LLM integration: ChatOllama singletons configured with deterministic settings and long-lived connections.
- **Updated** Enhanced skill matching system: Three-tier architecture with structured skills, text-scanned skills, and O*NET validation integration.
- **Updated** O*NET validation integration: Occupation-aware skill validation with high-collision filtering and false positive prevention.
- **Updated** Simplified scoring framework: Removed complex scoring logic in favor of deterministic components through fit_scorer.py and weight_mapper.py.
- **Updated** Enhanced interview kit generation: Sophisticated scoring prompts with comprehensive role and candidate context.
- Anti-hallucination guardrails: Comprehensive systems including cache versioning, circuit breakers, and skill validation.
- PII redaction integration: Automatic removal of personally identifiable information to eliminate bias.
- Deterministic LLM behavior: Fixed seeds and controlled temperature settings for reproducible results.
- Enhanced truncation limits: Increased character limits for job descriptions and resumes.
- Cloud-aware configuration: Automatic detection of Ollama Cloud deployments with optimized token limits and context windows.
- Intelligent keep_alive management: Cost-efficient cloud deployments disable keep_alive to avoid unnecessary charges.
- Timeout management: Centralized `_llm_request_timeout` constant ensures consistent timeout handling across all LLM instances.
- Error propagation: Each node appends typed errors to the state's errors list, enabling centralized diagnostics.
- Route integration: The main analysis route invokes the hybrid pipeline and stores results in the database; the LangGraph pipeline is not currently wired into the main route.
- JSON serialization: Comprehensive handling of datetime, date, and Decimal objects across all pipeline components.
- Enhanced cloud authentication: Improved logging and debugging capabilities for cloud deployments.
- Schema validation: Strict Pydantic models for interview questions and other structured outputs.

```mermaid
graph TB
AP["agent_pipeline.py"] --> LC["LangGraph StateGraph"]
AP --> CO["ChatOllama (fast)"]
AP --> CR["ChatOllama (reasoning)"]
AP --> SM["skill_matcher.py"]
AP --> ON["ONET Validator"]
AP --> JSH["JSON Serialization Handler"]
AP --> TT["Timeout Manager"]
AP --> CD["Cloud Detection"]
AP --> KA["Keep-Alive Manager"]
AP --> AH["Anti-Hallucination Guardrails"]
AP --> PII["PII Redaction Service"]
AP --> IQ["Interview Kit Generator"]
AP --> WM["Weight Mapper"]
AP --> FS["Fit Scorer"]
GS["guardrail_service.py"] --> IQV["Interview Questions Schema"]
HP["hybrid_pipeline.py"] --> CO2["ChatOllama (reasoning)"]
AR["routes/analyze.py"] --> HP
MS["main.py"] --> AR
```

**Diagram sources**
- [agent_pipeline.py:137-204](file://app/backend/services/agent_pipeline.py#L137-L204)
- [agent_pipeline.py:49-55](file://app/backend/services/agent_pipeline.py#L49-L55)
- [agent_pipeline.py:74-86](file://app/backend/services/agent_pipeline.py#L74-L86)
- [agent_pipeline.py:127](file://app/backend/services/agent_pipeline.py#L127)
- [agent_pipeline.py:357-473](file://app/backend/services/agent_pipeline.py#L357-L473)
- [agent_pipeline.py:581-654](file://app/backend/services/agent_pipeline.py#L581-L654)
- [agent_pipeline.py:731-955](file://app/backend/services/agent_pipeline.py#L731-L955)
- [guardrail_service.py:107-126](file://app/backend/services/guardrail_service.py#L107-L126)
- [weight_mapper.py:197-231](file://app/backend/services/weight_mapper.py#L197-L231)
- [fit_scorer.py:12-114](file://app/backend/services/fit_scorer.py#L12-L114)
- [hybrid_pipeline.py:82-105](file://app/backend/services/hybrid_pipeline.py#L82-105)
- [analyze.py:304-311](file://app/backend/routes/analyze.py#L304-L311)
- [main.py:200-214](file://app/backend/main.py#L200-L214)

**Section sources**
- [agent_pipeline.py:137-204](file://app/backend/services/agent_pipeline.py#L137-L204)
- [agent_pipeline.py:49-55](file://app/backend/services/agent_pipeline.py#L49-L55)
- [agent_pipeline.py:74-86](file://app/backend/services/agent_pipeline.py#L74-L86)
- [agent_pipeline.py:127](file://app/backend/services/agent_pipeline.py#L127)
- [agent_pipeline.py:357-473](file://app/backend/services/agent_pipeline.py#L357-L473)
- [agent_pipeline.py:581-654](file://app/backend/services/agent_pipeline.py#L581-L654)
- [agent_pipeline.py:731-955](file://app/backend/services/agent_pipeline.py#L731-L955)
- [guardrail_service.py:107-126](file://app/backend/services/guardrail_service.py#L107-L126)
- [weight_mapper.py:197-231](file://app/backend/services/weight_mapper.py#L197-L231)
- [fit_scorer.py:12-114](file://app/backend/services/fit_scorer.py#L12-L114)
- [hybrid_pipeline.py:82-105](file://app/backend/services/hybrid_pipeline.py#L82-105)
- [analyze.py:304-311](file://app/backend/routes/analyze.py#L304-L311)
- [main.py:200-214](file://app/backend/main.py#L200-L214)

## Performance Considerations
- Model selection:
  - Fast model for extraction and matching (lower latency, smaller context).
  - Reasoning model for scoring and narrative synthesis (higher latency, larger context).
- Connection reuse:
  - LLM singletons are created once and reused to avoid connection overhead and leverage Ollama's keep-alive sessions.
- Prompt sizing:
  - Limits resume text and timeline length to control context size and reduce latency.
- Parallelization strategy:
  - The LangGraph pipeline uses sequential nodes to maximize CPU utilization per call on CPU-bound inference.
- Caching:
  - JD cache avoids repeated LLM calls for identical job descriptions with automatic cache versioning.
- Streaming:
  - The hybrid pipeline supports SSE streaming to provide progressive updates while the LLM narrative is generated.
- **Updated** Enhanced skill matching performance:
  - Three-tier architecture reduces false positives and improves matching accuracy.
  - O*NET validation filters high-collision skills efficiently.
  - Text-scanned skills promotion requires strict domain validation to prevent performance degradation.
- **Updated** Simplified scoring framework:
  - Removed complex scoring logic in favor of deterministic components through fit_scorer.py
  - Reduced computational overhead by delegating numerical scoring to Python-based calculations
  - Improved performance by eliminating redundant scoring computations
- **Updated** Enhanced interview kit generation:
  - Comprehensive scoring prompts with detailed role and candidate context
  - Sophisticated fallback question generation with 5 technical, 3 behavioral, and 2 culture-fit questions
  - Schema validation ensures interview questions meet strict requirements
  - Context-aware question generation adapts to candidate background and timeline gaps
- **Updated** Enhanced cloud-aware optimizations:
  - Significantly increased token limits: Fast LLM from 1500 to 3000 tokens, Reasoning LLM from 2000 to 4000 tokens
  - Expanded context windows: Fast LLM from 6144 to 12288, Reasoning LLM from 4096 to 8192
  - Intelligent keep_alive disables for cloud to prevent unnecessary charges
  - Automatic Ollama Cloud authentication with API key support and enhanced logging
- **Updated** Anti-hallucination guardrails:
  - Cache versioning prevents stale results with updated prompts
  - Circuit breaker prevents cascading failures from hallucinations
  - Skill validation ensures extracted information matches original job descriptions
  - Rule-based fallback maintains system reliability when hallucinations exceed thresholds
  - O*NET validation prevents false positives and improves accuracy
- **Updated** PII redaction integration:
  - Automatic removal of personally identifiable information eliminates bias
  - Enterprise-grade detection with fallback to regex patterns
  - Comprehensive tracking of redaction activities
- **Updated** Deterministic LLM behavior:
  - Fixed seeds (42) and controlled temperature (0.0) ensure reproducible results
  - Eliminates randomness in LLM responses for consistent analysis
- **Updated** Enhanced truncation limits:
  - Increased from 2000 to 8000 characters for job descriptions and resumes
  - Captures complete context for comprehensive analysis
  - Reduces ambiguity and improves accuracy
- **Updated** Timeout management:
  - Centralized timeout configuration prevents resource exhaustion and improves reliability.
  - Consistent timeout handling across all LLM instances ensures predictable performance.
  - Environment-based configuration allows for flexible tuning without code changes.
  - Enhanced timeout handling works seamlessly with increased token limits in cloud deployments.
- **Updated** JSON serialization optimization:
  - Efficient handling of complex data types reduces serialization overhead.
  - Minimal memory footprint for serialized objects.
  - Enhanced support for O*NET validation data structures.
- **Updated** Enhanced cloud deployment support:
  - Improved authentication logging and debugging capabilities
  - Better error handling for cloud-specific configurations
  - Optimized resource allocation for cloud deployments with larger token limits

## Troubleshooting Guide
- LLM unavailability:
  - The pipeline returns typed-null defaults and appends errors to the state. Check Ollama reachability and model readiness.
- JSON parsing failures:
  - The pipeline attempts to extract JSON from various formats and applies fallbacks; if parsing fails, typed-null defaults are returned.
- Weight normalization:
  - Weights are normalized to sum to 1.0; missing keys are filled from defaults.
- Recommendation correction:
  - Invalid recommendations are corrected based on fit score thresholds.
- Error aggregation:
  - Errors from all nodes are accumulated in the state's errors list for centralized diagnostics.
- **Updated** Enhanced skill matching issues:
  - Verify three-tier skill matching is working correctly with structured, text-scanned, and fuzzy skills.
  - Check O*NET validation integration and occupation-aware filtering.
  - Monitor high-collision skill filtering effectiveness.
  - Ensure text-scanned skills promotion follows strict domain validation rules.
- **Updated** Simplified scoring framework issues:
  - Verify weight mapping is working correctly with new universal schema.
  - Check deterministic scoring components are properly integrated.
  - Monitor performance improvements from removed complex scoring logic.
- **Updated** Enhanced interview kit generation issues:
  - Verify interview questions meet schema validation requirements (max 20 questions per category).
  - Check that fallback question generation is working when LLM calls fail.
  - Ensure context-aware questions reference specific skills, role responsibilities, or candidate resume context.
  - Monitor interview kit generation performance with increased token limits.
- **Updated** Anti-hallucination guardrail issues:
  - Verify hallucination counter resets hourly and thresholds are properly configured.
  - Check cache versioning is working correctly with prompt changes.
  - Ensure skill validation is properly comparing against original job descriptions.
  - Monitor circuit breaker triggering and rule-based fallback activation.
  - Verify O*NET validation is properly filtering high-collision skills.
- **Updated** PII redaction problems:
  - Verify PII redaction service is properly integrated and accessible.
  - Check fallback to regex patterns when Presidio is unavailable.
  - Review redaction results for comprehensive tracking and confidence scores.
- **Updated** Deterministic behavior issues:
  - Confirm fixed seeds (42) are properly configured for both LLM instances.
  - Verify temperature settings are set to 0.0 for deterministic results.
  - Check that deterministic behavior is maintained across multiple runs.
- **Updated** Enhanced truncation problems:
  - Verify character limits are properly applied to job descriptions and resumes.
  - Check that truncation is capturing complete context without losing important information.
  - Monitor for performance impacts with increased character limits.
- **Updated** Cloud deployment issues:
  - Verify OLLAMA_BASE_URL points to ollama.com for cloud deployments.
  - Ensure OLLAMA_API_KEY environment variable is set for authenticated cloud access.
  - Check that cloud models have sufficient token limits (3000/4000 vs 600/800).
  - Monitor keep_alive behavior - should be disabled for cloud deployments.
  - Review enhanced cloud authentication logs for detailed debugging information.
- **Updated** Timeout-related issues:
  - Monitor `_llm_request_timeout` configuration to ensure appropriate values for your workload.
  - Check environment variable `LLM_NARRATIVE_TIMEOUT` for proper timeout settings.
  - Verify that the 30-second buffer is sufficient for your network conditions.
  - Consider adjusting timeout values based on model complexity and system resources.
  - Enhanced timeout handling works seamlessly with increased token limits in cloud deployments.
- **Updated** JSON serialization issues:
  - Ensure all data passed to JSON serialization includes proper type conversion using `_json_default`.
  - Verify that datetime, date, and Decimal objects are properly handled in all pipeline components.
  - Check for circular references or self-referencing objects that might cause serialization errors.
  - Monitor O*NET validation data serialization with enhanced JSON handling.
- **Updated** Performance issues with enhanced guardrails:
  - Monitor cloud deployment performance with larger token limits (3000/4000 tokens).
  - Verify that context windows (12288/8192) are appropriate for your workload.
  - Check that cloud authentication logging is functioning properly for debugging.
  - Review hallucination detection performance and circuit breaker effectiveness.
  - Monitor O*NET validation performance and filtering effectiveness.

**Section sources**
- [agent_pipeline.py:127-138](file://app/backend/services/agent_pipeline.py#L127-L138)
- [agent_pipeline.py:647-654](file://app/backend/services/agent_pipeline.py#L647-L654)
- [agent_pipeline.py:949-955](file://app/backend/services/agent_pipeline.py#L949-L955)
- [guardrail_service.py:205-215](file://app/backend/services/guardrail_service.py#L205-L215)

## Conclusion
The LangGraph-based multi-agent analysis pipeline provides a robust, schema-bound, and deterministic approach to complex, multi-step reasoning workflows. By leveraging Ollama models with careful configuration, typed state management, comprehensive fallbacks, and centralized timeout handling, it ensures reliable operation under varied conditions. The enhanced anti-hallucination guardrails including cache versioning, circuit breaker mechanisms, and deterministic LLM behavior with fixed seeds provide comprehensive protection against hallucinations and ensure reliable analysis results. The PII redaction integration eliminates bias from personal identifiers, while the increased truncation limits from 2000 to 8000 characters capture complete context for accurate analysis. The enhanced cloud-aware configuration management with significantly increased token limits (3000/4000 tokens vs 1500/2000) and expanded context windows (12288/8192 vs 6144/4096) provides cost-efficient operations for cloud deployments while maintaining optimal performance. The enhanced timeout management with the `_llm_request_timeout` constant provides predictable behavior and improved reliability across all LLM interactions. The enhanced JSON serialization handling for datetime objects, dates, and Decimal values further strengthens the pipeline's reliability and compatibility with diverse data types. The enhanced cloud authentication logging and debugging capabilities provide better visibility into cloud deployment configurations. The enhanced interview kit generation system creates highly targeted, non-generic questions based on comprehensive role and candidate context, with sophisticated fallback mechanisms for technical, behavioral, and culture-fit questions. **Updated** The enhanced three-tier skill matching architecture with O*NET validation provides superior accuracy and reduces false positives through occupation-aware skill validation. The simplified scoring framework removes complex scoring logic in favor of deterministic components, resulting in more reliable and consistent results while improving performance. While the hybrid pipeline offers a complementary approach with streaming and narrative synthesis, the LangGraph pipeline remains ideal for scenarios requiring strict schema-bound outputs and resilient error handling with comprehensive anti-hallucination protection, sophisticated interview kit generation, and enhanced skill matching with O*NET validation.

## Appendices

### Workflow Definition and Execution
- The pipeline is defined as a StateGraph with three sequential nodes and compiled once at module load.
- Execution proceeds from job description parsing to candidate analysis and finally to scoring and interview question generation.
- **Updated** Enhanced with anti-hallucination guardrails, PII redaction integration, simplified scoring framework, and enhanced skill matching with O*NET validation.

**Section sources**
- [agent_pipeline.py:1022-1037](file://app/backend/services/agent_pipeline.py#L1022-L1037)

### State Persistence and Error Recovery
- State includes an errors accumulator for centralized diagnostics.
- The hybrid pipeline demonstrates persistent storage of analysis results and candidate profiles in the database.
- **Updated** Enhanced error recovery with anti-hallucination guardrails, rule-based fallback mechanisms, comprehensive interview kit fallback generation, and O*NET validation error handling.

**Section sources**
- [agent_pipeline.py:225](file://app/backend/services/agent_pipeline.py#L225)
- [analyze.py:462-472](file://app/backend/routes/analyze.py#L462-L472)

### Performance Monitoring
- The main application exposes health checks and diagnostic endpoints for Ollama status and model readiness.
- Logging captures pipeline stages and errors for operational visibility.
- **Updated** Enhanced monitoring includes hallucination detection metrics, PII redaction statistics, interview kit generation performance, O*NET validation effectiveness, and three-tier skill matching accuracy.

**Section sources**
- [main.py:354-399](file://app/backend/main.py#L354-L399)
- [main.py:228-259](file://app/backend/main.py#L228-L259)

### Example: Running the Agent Pipeline
- The public API entry point constructs initial state, invokes the compiled graph, and assembles the final result.
- **Updated** Enhanced with anti-hallucination guardrails, PII redaction integration, simplified scoring framework, and O*NET validation enrichment.

**Section sources**
- [agent_pipeline.py:1163-1190](file://app/backend/services/agent_pipeline.py#L1163-L1190)

### Cloud Deployment Configuration Best Practices
**Updated** Guidelines for configuring and managing cloud-aware deployments with enhanced token limits:

1. **Environment Configuration**:
   - Set `OLLAMA_BASE_URL` to point to Ollama Cloud (ollama.com) for cloud deployments
   - Set `OLLAMA_API_KEY` environment variable for authenticated cloud access
   - Configure `LLM_NARRATIVE_TIMEOUT` environment variable to control base timeout (default: 150 seconds)
   - The pipeline automatically adds a 30-second buffer for HTTP transport overhead

2. **Enhanced Cloud-Specific Optimizations**:
   - Fast model token limit increases to 3000 tokens for cloud vs 600 for local
   - Reasoning model token limit increases to 4000 tokens for cloud vs 800 for local
   - Context windows expand to 12288 for cloud vs 3072 for local
   - Keep-alive automatically disabled for cloud deployments to prevent charges
   - Enhanced logging provides detailed authentication and configuration information

3. **Consistent Timeout Handling**:
   - All LLM instances use the same `_llm_request_timeout` constant
   - Ensures predictable behavior across fast and reasoning models
   - Prevents resource exhaustion and improves reliability
   - Works seamlessly with increased token limits in cloud deployments

4. **Enhanced Interview Kit Generation Configuration**:
   - Monitor interview kit generation performance with increased token limits
   - Verify fallback question generation is working correctly
   - Check schema validation for interview questions meets requirements
   - Ensure context-aware questions reference specific skills and role responsibilities

5. **Anti-Hallucination Guardrail Configuration**:
   - Monitor hallucination counter for proper operation
   - Verify cache versioning responds to prompt changes
   - Check circuit breaker threshold (5 hallucinations per hour) is appropriate
   - Ensure skill validation is properly configured against original job descriptions
   - Verify O*NET validation is properly filtering high-collision skills

6. **PII Redaction Service Setup**:
   - Install Presidio libraries for enterprise-grade detection (recommended)
   - Configure fallback to regex patterns for basic PII detection
   - Monitor redaction statistics and confidence scores
   - Ensure comprehensive tracking of redacted entities

7. **Deterministic Behavior Configuration**:
   - Verify fixed seeds (42) are properly applied to both LLM instances
   - Confirm temperature settings are set to 0.0 for deterministic results
   - Test reproducibility across multiple runs

8. **Enhanced Truncation Limits**:
   - Verify 8000-character limits for job descriptions and resumes
   - Monitor performance impact with increased character limits
   - Ensure complete context capture without losing important information

9. **Enhanced Skill Matching Configuration**:
   - Verify three-tier skill matching architecture is properly configured
   - Check O*NET validation integration and database connectivity
   - Monitor high-collision skill filtering effectiveness
   - Ensure text-scanned skills promotion follows strict domain validation rules

10. **Monitoring and Adjustment**:
    - Monitor LLM response times and adjust `LLM_NARRATIVE_TIMEOUT` accordingly
    - Consider network latency and model complexity when tuning timeout values
    - Test with representative workloads to determine optimal timeout settings
    - Verify cloud authentication by checking Ollama Cloud status
    - Monitor enhanced cloud authentication logs for debugging and troubleshooting
    - Track hallucination detection effectiveness and adjust thresholds as needed
    - Monitor PII redaction performance and accuracy metrics
    - Review interview kit generation effectiveness and adjust question generation as needed
    - Monitor O*NET validation performance and filtering effectiveness
    - Track three-tier skill matching accuracy improvements

11. **Fallback Mechanisms**:
    - Timeout exceptions trigger graceful fallback to typed-null defaults
    - Hallucination detection triggers rule-based fallback when thresholds are exceeded
    - O*NET validation failures gracefully fall back to standard skill matching
    - Error messages are captured in the state's errors list for diagnostics
    - Pipeline continues operation even when individual LLM calls timeout or hallucinate
    - Enhanced error handling works with increased token limits and context windows
    - Interview kit fallback generation ensures meaningful questions even when LLM fails
    - O*NET validation fallback maintains system reliability when database is unavailable

12. **Performance Optimization**:
    - Leverage increased token limits (3000/4000) for more verbose and accurate outputs
    - Utilize expanded context windows (12288/8192) for complex reasoning tasks
    - Monitor cloud deployment performance with enhanced configuration
    - Optimize for cloud-specific resource allocation and cost efficiency
    - Ensure anti-hallucination guardrails don't introduce significant performance overhead
    - Verify interview kit generation doesn't impact overall pipeline performance
    - Monitor simplified scoring framework performance improvements
    - Track O*NET validation performance and filtering effectiveness
    - Optimize three-tier skill matching for best balance of accuracy and performance

**Section sources**
- [agent_pipeline.py:74-86](file://app/backend/services/agent_pipeline.py#L74-L86)
- [agent_pipeline.py:137-204](file://app/backend/services/agent_pipeline.py#L137-L204)
- [agent_pipeline.py:127](file://app/backend/services/agent_pipeline.py#L127)
- [agent_pipeline.py:357-473](file://app/backend/services/agent_pipeline.py#L357-L473)
- [agent_pipeline.py:581-654](file://app/backend/services/agent_pipeline.py#L581-L654)
- [agent_pipeline.py:731-955](file://app/backend/services/agent_pipeline.py#L731-L955)
- [skill_matcher.py:31-71](file://app/backend/services/skill_matcher.py#L31-L71)

### JSON Serialization Best Practices
**Updated** Guidelines for handling complex data types in the pipeline with enhanced cloud deployment support:

1. **Always use `_json_default`** when serializing data containing datetime, date, or Decimal objects
2. **Test serialization** with representative data samples before deployment
3. **Handle edge cases** where objects might be None or empty collections
4. **Monitor serialization performance** in production environments
5. **Validate deserialization** on the receiving end to ensure data integrity
6. **Work seamlessly with cloud deployments** that support larger token limits and context windows
7. **Utilize enhanced error handling** for serialization issues in cloud environments
8. **Ensure compatibility** with anti-hallucination guardrails, PII redaction processes, interview kit generation, and O*NET validation
9. **Monitor performance improvements** from simplified scoring framework integration
10. **Handle O*NET validation data** with proper JSON serialization for hot skills and validation results

**Section sources**
- [agent_pipeline.py:49-55](file://app/backend/services/agent_pipeline.py#L49-L55)
- [agent_pipeline.py:620](file://app/backend/services/agent_pipeline.py#L620)
- [agent_pipeline.py:866](file://app/backend/services/agent_pipeline.py#L866)
- [agent_pipeline.py:1140-1144](file://app/backend/services/agent_pipeline.py#L1140-L1144)

### O*NET Integration Best Practices
**Updated** Guidelines for implementing and optimizing O*NET validation in the agent pipeline:

1. **Database Setup**:
   - Ensure O*NET cache database is properly initialized and populated
   - Verify database connectivity and file permissions
   - Monitor database performance and query optimization

2. **Validation Configuration**:
   - Configure job title resolution and skill validation thresholds
   - Monitor validation accuracy and false positive rates
   - Track high-collision skill filtering effectiveness

3. **Performance Optimization**:
   - Monitor O*NET validation query performance
   - Optimize database queries for skill validation
   - Implement caching strategies for frequently accessed skills

4. **Error Handling**:
   - Handle O*NET database unavailability gracefully
   - Monitor validation failures and fallback mechanisms
   - Track validation performance metrics

5. **Integration Testing**:
   - Test O*NET validation with various job titles and skill combinations
   - Verify high-collision skill filtering effectiveness
   - Monitor false positive prevention for common scenarios

**Section sources**
- [skill_matcher.py:18-28](file://app/backend/services/skill_matcher.py#L18-L28)
- [skill_matcher.py:31-71](file://app/backend/services/skill_matcher.py#L31-L71)
- [onet_validator.py:18-53](file://app/backend/services/onet/onet_validator.py#L18-L53)
- [test_onet_integration.py:300-350](file://app/backend/tests/test_onet_integration.py#L300-L350)