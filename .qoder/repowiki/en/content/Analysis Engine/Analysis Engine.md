# Analysis Engine

<cite>
**Referenced Files in This Document**
- [main.py](file://app/backend/main.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [agent_pipeline.py](file://app/backend/services/agent_pipeline.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [gap_detector.py](file://app/backend/services/gap_detector.py)
- [analysis_service.py](file://app/backend/services/analysis_service.py)
- [llm_service.py](file://app/backend/services/llm_service.py)
- [llm_contact_extractor.py](file://app/backend/services/llm_contact_extractor.py)
- [weight_mapper.py](file://app/backend/services/weight_mapper.py)
- [weight_suggester.py](file://app/backend/services/weight_suggester.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [README.md](file://README.md)
- [nginx.prod.conf](file://app/nginx/nginx.prod.conf)
- [queue_manager.py](file://app/backend/services/queue_manager.py)
</cite>

## Update Summary
**Changes Made**
- **Enhanced LLM Error Handling**: Implemented comprehensive error handling with exponential backoff retry mechanisms for external LLM services
- **Improved Resource Management**: Added robust semaphore-based concurrency control and health monitoring for Ollama integration
- **Enhanced Retry Logic**: Integrated exponential backoff retry system for rate limiting (429) and connection errors
- **Background Task Management**: Added graceful shutdown handling for background LLM processing tasks
- **Queue System Integration**: Enhanced queue manager with automatic retry mechanisms and exponential backoff

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Enhanced AI Pipeline Capabilities](#enhanced-ai-pipeline-capabilities)
7. [Intelligent Scoring Weights System](#intelligent-scoring-weights-system)
8. [Advanced Contact Extraction](#advanced-contact-extraction)
9. [Enhanced Parser Service](#enhanced-parser-service)
10. [Streaming Endpoint Integration](#streaming-endpoint-integration)
11. [Structured Risk Analysis](#structured-risk-analysis)
12. [Model Configuration and Performance](#model-configuration-and-performance)
13. [Enhanced JSON Serialization Capabilities](#enhanced-json-serialization-capabilities)
14. [Enhanced Error Handling and Retry Systems](#enhanced-error-handling-and-retry-systems)
15. [Resource Management and Concurrency Control](#resource-management-and-concurrency-control)
16. [Dependency Analysis](#dependency-analysis)
17. [Performance Considerations](#performance-considerations)
18. [Troubleshooting Guide](#troubleshooting-guide)
19. [Conclusion](#conclusion)
20. [Appendices](#appendices)

## Introduction
This document explains the analysis engine powering Resume AI by ThetaLogics. It focuses on the hybrid pipeline architecture that combines Python-first deterministic processing with a single LLM call for narrative generation, the LangGraph-based agent pipeline for complex multi-step analysis, the enhanced resume parsing service supporting PDF and DOCX formats with multi-tier extraction strategies, the employment gap detection algorithm, the skills registry system, LLM service integration with Ollama, scoring and recommendation logic, risk assessment criteria, performance optimization techniques, memory management, error handling strategies, and extension points for custom evaluation criteria.

**Updated** The analysis engine now features enhanced error handling and retry mechanisms with comprehensive exponential backoff support for external LLM services. The system includes robust resource management through semaphore-based concurrency control, health monitoring for Ollama integration, and graceful background task handling. These improvements provide significantly enhanced reliability and fault tolerance for production deployments.

## Project Structure
The backend is organized around FastAPI routes, SQLAlchemy models, and modular services. The analysis engine spans:
- Routes orchestrating the end-to-end flow with robust JSON serialization
- Services implementing parsing, gap detection, hybrid scoring, and LLM integration
- Models defining persistence for candidates, screening results, and caches
- Startup and health checks coordinating environment readiness
- Queue management system with automatic retry mechanisms

```mermaid
graph TB
subgraph "Routes"
A["analyze.py<br/>JSON Serialization Utilities<br/>SSE Streaming Endpoints"]
end
subgraph "Services"
B["parser_service.py<br/>Multi-tier Extraction Strategies"]
C["gap_detector.py"]
D["hybrid_pipeline.py<br/>Enhanced Error Handling<br/>Exponential Backoff"]
E["agent_pipeline.py"]
F["analysis_service.py"]
G["llm_service.py<br/>Semaphore Control<br/>Health Monitoring"]
H["llm_contact_extractor.py<br/>Enhanced LLM Contact Extraction"]
I["weight_mapper.py<br/>Schema Conversion"]
J["weight_suggester.py<br/>LLM Weight Suggestions"]
K["queue_manager.py<br/>Automatic Retry<br/>Exponential Backoff"]
end
subgraph "Models"
L["db_models.py"]
end
subgraph "App"
M["main.py<br/>Background Task Management"]
N["nginx.prod.conf<br/>Streaming Configuration"]
end
A --> B
A --> C
A --> D
A --> E
A --> F
A --> G
A --> H
A --> I
A --> J
A --> K
A --> L
M --> A
M --> G
N --> A
```

**Diagram sources**
- [analyze.py:669-868](file://app/backend/routes/analyze.py#L669-L868)
- [parser_service.py:343-492](file://app/backend/services/parser_service.py#L343-L492)
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)
- [weight_mapper.py:20-360](file://app/backend/services/weight_mapper.py#L20-L360)
- [weight_suggester.py:86-177](file://app/backend/services/weight_suggester.py#L86-L177)
- [queue_manager.py:1-200](file://app/backend/services/queue_manager.py#L1-200)
- [nginx.prod.conf:73-98](file://app/nginx/nginx.prod.conf#L73-L98)

**Section sources**
- [README.md:273-333](file://README.md#L273-L333)
- [main.py:174-215](file://app/backend/main.py#L174-L215)

## Core Components
- Hybrid Pipeline: Python-first deterministic scoring (skills, education, experience/timeline, domain/architecture) followed by a single LLM call for narrative synthesis and interview questions with enhanced error handling and retry mechanisms.
- LangGraph Agent Pipeline: Multi-agent, multi-stage workflow with structured nodes for JD parsing, combined resume analysis, and scoring with explainability.
- Enhanced Resume Parser: Robust text extraction from PDF and DOCX with multi-tier fallbacks, deduplication, and normalization.
- Gap Detector: Mechanical date parsing and interval merging to compute objective timeline metrics.
- Skills Registry: Dynamic, DB-backed registry with in-memory flashtext processor and hot reload capability.
- LLM Integration: Ollama-backed ChatOllama clients with singletons, timeouts, JSON parsing utilities, and comprehensive error handling.
- Intelligent Contact Extraction: LLM-powered contact information extraction with merging strategy for accuracy.
- Scoring and Risk: Weighted fit score computation, risk signals, and recommendation logic with intelligent weight mapping.
- Persistence: SQLAlchemy models for candidates, screening results, role templates, usage logs, and caches.
- **Enhanced AI Pipeline**: Sophisticated score rationales and structured risk analysis with detailed explanations.
- **AI-Enhanced Narratives**: Distinction system between LLM-generated and fallback narratives using `ai_enhanced` flag.
- **Enhanced Error Handling**: Comprehensive retry mechanisms with exponential backoff for rate limiting and connection failures.
- **Resource Management**: Semaphore-based concurrency control and health monitoring for external LLM services.

**Section sources**
- [hybrid_pipeline.py:1-1498](file://app/backend/services/hybrid_pipeline.py#L1-L1498)
- [agent_pipeline.py:1-634](file://app/backend/services/agent_pipeline.py#L1-L634)
- [parser_service.py:1-552](file://app/backend/services/parser_service.py#L1-L552)
- [gap_detector.py:1-219](file://app/backend/services/gap_detector.py#L1-L219)
- [llm_service.py:1-332](file://app/backend/services/llm_service.py#L1-L332)
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)
- [weight_mapper.py:20-360](file://app/backend/services/weight_mapper.py#L20-L360)
- [weight_suggester.py:86-177](file://app/backend/services/weight_suggester.py#L86-L177)
- [db_models.py:97-250](file://app/backend/models/db_models.py#L97-L250)
- [queue_manager.py:1-200](file://app/backend/services/queue_manager.py#L1-L200)

## Architecture Overview
The system uses a hybrid approach with enhanced error handling:
- Phase 1 (Python, ~1–2s): parse_jd_rules → parse_resume_rules → match_skills_rules → score_education/experience/domain → compute_fit_score → generate score rationales and risk summary
- Phase 2 (LLM, ~40s): explain_with_llm (generates strengths, weaknesses, rationale, interview questions) with exponential backoff retry for rate limiting
- Fallback: deterministic narrative when LLM is unavailable or times out
- Background Processing: LLM narrative generated as background task with graceful shutdown handling

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "analyze.py"
participant Parser as "parser_service.py"
participant Gap as "gap_detector.py"
participant Hybrid as "hybrid_pipeline.py"
participant Contact as "llm_contact_extractor.py"
participant LLM as "Ollama (ChatOllama)<br/>Enhanced Error Handling"
Client->>Route : POST /api/analyze
Route->>Parser : parse_resume(file)
Parser-->>Route : parsed_data
Route->>Contact : extract_contact_with_llm(raw_text)
Contact-->>Route : contact_info
Route->>Gap : analyze_gaps(work_experience)
Gap-->>Route : gap_analysis
Route->>Hybrid : run_hybrid_pipeline(...)
Hybrid->>Hybrid : _run_python_phase(...)
Hybrid->>Hybrid : _build_score_rationales()
Hybrid->>Hybrid : _build_risk_summary()
Hybrid->>LLM : explain_with_llm(context)<br/>Exponential Backoff Retry
LLM-->>Hybrid : narrative JSON (with retry logic)
Hybrid-->>Route : merged result
Route-->>Client : AnalysisResponse
```

**Diagram sources**
- [analyze.py:268-318](file://app/backend/routes/analyze.py#L268-L318)
- [hybrid_pipeline.py:1262-1407](file://app/backend/services/hybrid_pipeline.py#L1262-L1407)
- [parser_service.py:547-552](file://app/backend/services/parser_service.py#L547-L552)
- [gap_detector.py:217-219](file://app/backend/services/gap_detector.py#L217-L219)
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)

## Detailed Component Analysis

### Hybrid Pipeline
The hybrid pipeline executes deterministic Python logic first, then a single LLM call for narrative with enhanced error handling. It includes:
- Skills registry with canonical skills, aliases, and domain mapping
- JD parsing rules extracting role, domain, seniority, required/nice-to-have skills, and responsibilities
- Resume profile builder combining parser output and gap analysis
- Skill matching with normalization, alias expansion, substring matching, and fuzzy fallback
- Education scoring with degree and field relevance multipliers
- Experience and timeline scoring with gap severity deductions
- Domain and architecture scoring based on keyword hits
- Fit score computation with configurable weights and risk penalties
- LLM narrative generation with robust JSON parsing, fallback, and comprehensive error handling
- **Enhanced**: Score rationales for each dimension and structured risk summary
- **Optimized**: gemma4:31b-cloud model with intelligent token limits for improved performance
- **Robust**: Exponential backoff retry mechanisms for rate limiting and connection failures

```mermaid
flowchart TD
Start(["Start"]) --> ParseJD["parse_jd_rules(job_description)"]
ParseJD --> ParseResume["parse_resume_rules(parsed_data, gap_analysis)"]
ParseResume --> MatchSkills["match_skills_rules(profile, jd, raw_text)"]
MatchSkills --> EduScore["score_education_rules(profile, jd_domain)"]
EduScore --> ExpTimeline["score_experience_rules(profile, jd, gap_analysis)"]
ExpTimeline --> DomainArch["domain_architecture_rules(raw_text, jd_domain, current_role)"]
DomainArch --> ComputeFit["compute_fit_score(scores, weights)"]
ComputeFit --> Rationales["_build_score_rationales()"]
Rationales --> RiskSummary["_build_risk_summary()"]
RiskSummary --> LLMCall{"LLM available?"}
LLMCall --> |Yes| LLMNarrative["explain_with_llm(context)<br/>Exponential Backoff Retry"]
LLMCall --> |No| Fallback["fallback_narrative()"]
LLMNarrative --> Merge["merge_llm_into_result()"]
Fallback --> Merge
Merge --> End(["End"])
```

**Diagram sources**
- [hybrid_pipeline.py:1262-1407](file://app/backend/services/hybrid_pipeline.py#L1262-L1407)
- [hybrid_pipeline.py:1074-1256](file://app/backend/services/hybrid_pipeline.py#L1074-L1256)

**Section sources**
- [hybrid_pipeline.py:1-1498](file://app/backend/services/hybrid_pipeline.py#L1-L1498)

### LangGraph Agent Pipeline
The LangGraph-based agent pipeline defines a 3-stage workflow:
- Stage 1 (parallel): jd_parser
- Stage 2 (parallel): resume_analyser (combines skill/domain/edu/timeline)
- Stage 3 (parallel): scorer (combined scoring and interview questions)

It uses:
- Two LLM singletons (fast and reasoning) with keep-alive sessions
- JSON parsing helper with fallback extraction
- In-memory JD cache keyed by MD5 of first 2000 characters
- Streamable nodes emitting SSE events
- Fallback per node returning typed-null defaults on failures

```mermaid
sequenceDiagram
participant Client as "Client"
participant Agent as "agent_pipeline.py"
participant Fast as "get_fast_llm()"
participant Reason as "get_reasoning_llm()"
Client->>Agent : run_agent_pipeline(...)
Agent->>Fast : jd_parser_node()
Fast-->>Agent : jd_analysis
Agent->>Fast : resume_analyser_node()
Fast-->>Agent : candidate_profile/skill_analysis/edu_timeline_analysis
Agent->>Reason : scorer_node()
Reason-->>Agent : final_scores/interview_questions
Agent-->>Client : assembled result
```

**Diagram sources**
- [agent_pipeline.py:520-541](file://app/backend/services/agent_pipeline.py#L520-L541)
- [agent_pipeline.py:161-180](file://app/backend/services/agent_pipeline.py#L161-L180)
- [agent_pipeline.py:280-322](file://app/backend/services/agent_pipeline.py#L280-L322)
- [agent_pipeline.py:367-448](file://app/backend/services/agent_pipeline.py#L367-L448)

**Section sources**
- [agent_pipeline.py:1-634](file://app/backend/services/agent_pipeline.py#L1-L634)

### Enhanced Parser Service
The enhanced parser supports:
- PDF: PyMuPDF primary, pdfplumber fallback with table extraction; scanned PDF guard
- DOCX: Multi-stage extraction with headers, textboxes, tables, paragraphs, and XML fallback
- DOC/RTF/HTML/ODT/TXT: Best-effort extraction with Unicode normalization and deduplication
- Advanced contact extraction with LLM-powered merging strategy
- Resume parsing: work experience, skills, education, contact info with enrichment

```mermaid
flowchart TD
A["extract_text(file_bytes, filename)"] --> B{"PDF?"}
B --> |Yes| C["PyMuPDF -> text"]
C --> D{"Empty?"}
D --> |Yes| E["pdfplumber fallback"]
D --> |No| Z["Return text"]
B --> |No| F{"DOCX?"}
F --> |Yes| G["Multi-stage DOCX extraction:<br/>Headers → Textboxes → Tables → Paragraphs → XML Fallback"]
F --> |No| H{"Other formats?"}
H --> |Yes| I["Decode with encodings"]
H --> |No| J["Raise unsupported format"]
G --> K["Return text"]
I --> L{"Readable?"}
L --> |Yes| Z
L --> |No| J
```

**Diagram sources**
- [parser_service.py:240-313](file://app/backend/services/parser_service.py#L240-L313)
- [parser_service.py:343-492](file://app/backend/services/parser_service.py#L343-L492)
- [parser_service.py:542-737](file://app/backend/services/parser_service.py#L542-L737)

**Section sources**
- [parser_service.py:1-552](file://app/backend/services/parser_service.py#L1-L552)

### Employment Gap Detection Algorithm
The gap detector performs:
- Date normalization to YYYY-MM with flexible parsing and fallback
- Overlap-aware total experience via interval merging
- Objective gap severity classification (threshold-based)
- Structured timeline with gap metadata for downstream LLM consumption

```mermaid
flowchart TD
Start(["Start"]) --> Normalize["Normalize dates to YYYY-MM"]
Normalize --> Sort["Sort jobs by start_ym"]
Sort --> Timeline["Build timeline with gap_after_months"]
Timeline --> Gaps["Filter gaps ≥ 3 months"]
Timeline --> Overlaps["Detect overlaps > 1 month"]
Timeline --> ShortStints["Detect stints < 6 months"]
Timeline --> MergeInt["Merge overlapping intervals"]
MergeInt --> TotalYears["Compute total_years from merged intervals"]
Gaps --> End(["End"])
Overlaps --> End
ShortStints --> End
TotalYears --> End
```

**Diagram sources**
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)

**Section sources**
- [gap_detector.py:1-219](file://app/backend/services/gap_detector.py#L1-L219)

### Skills Registry System
The skills registry:
- Seeds canonical skills and aliases into the DB
- Loads active skills into an in-memory flashtext processor
- Provides hot-reload capability and fallback to hardcoded list
- Maps skills to domains for seeding and matching

```mermaid
classDiagram
class SkillsRegistry {
-_processor
-_skills : str[]
-_loaded : bool
+seed_if_empty(db)
+load(db)
+rebuild(db)
+get_processor()
+get_all_skills() str[]
}
class Skill {
+id
+name
+aliases
+domain
+status
+source
+frequency
}
SkillsRegistry --> Skill : "loads from"
```

**Diagram sources**
- [hybrid_pipeline.py:323-426](file://app/backend/services/hybrid_pipeline.py#L323-L426)
- [db_models.py:238-250](file://app/backend/models/db_models.py#L238-L250)

**Section sources**
- [hybrid_pipeline.py:70-426](file://app/backend/services/hybrid_pipeline.py#L70-L426)
- [db_models.py:227-250](file://app/backend/models/db_models.py#L227-L250)

### LLM Service Integration with Ollama
Integration points:
- ChatOllama singletons for fast and reasoning models
- Environment configuration for base URL, model, and context sizes
- JSON parsing utilities tolerant of fenced code blocks and partial JSON
- Fallback responses on errors and timeouts
- Health and diagnostics endpoints for model readiness
- **Enhanced**: Semaphore-based concurrency control with auto-detection for cloud vs local
- **Robust**: Comprehensive error handling with exponential backoff for rate limiting

```mermaid
sequenceDiagram
participant Service as "llm_service.py"
participant Ollama as "Ollama API"
Service->>Service : get_ollama_semaphore()<br/>Auto-detect cloud/local
Service->>Ollama : POST /api/generate (JSON format)
Ollama-->>Service : response JSON
Service->>Service : _parse_json_response()
Service-->>Caller : validated result or fallback
```

**Diagram sources**
- [llm_service.py:43-104](file://app/backend/services/llm_service.py#L43-L104)
- [main.py:262-327](file://app/backend/main.py#L262-L327)

**Section sources**
- [llm_service.py:1-156](file://app/backend/services/llm_service.py#L1-L156)
- [main.py:104-149](file://app/backend/main.py#L104-L149)

### Scoring Algorithms, Recommendation Logic, and Risk Assessment
Scoring and risk:
- Weighted fit score across skill, experience, architecture, education, timeline, domain, and risk
- Risk signals derived deterministically from gaps, short stints, domain mismatch, and overqualification
- Recommendation thresholds (Shortlist ≥ 72, Consider [45–71], Reject < 45)
- Timeline severity penalties and architecture signal bonuses

```mermaid
flowchart TD
Scores["Scores: skill/exp/arch/edu/timeline/domain"] --> Weights["Apply weights"]
Weights --> Risk["Compute risk_penalty from risk_signals"]
Risk --> Fit["fit_score = sum - risk_penalty"]
Fit --> Clamp["Clamp 0..100"]
Clamp --> Rec["Recommendation thresholds"]
Rec --> End(["End"])
```

**Diagram sources**
- [hybrid_pipeline.py:964-1058](file://app/backend/services/hybrid_pipeline.py#L964-L1058)

**Section sources**
- [hybrid_pipeline.py:953-1058](file://app/backend/services/hybrid_pipeline.py#L953-L1058)

### Route Orchestration and Streaming
The analyze route:
- Validates file types and sizes, resolves JD from text or file
- Parses resumes in thread pool to avoid blocking
- Runs hybrid pipeline and persists results
- Supports SSE streaming with heartbeat pings
- Implements candidate deduplication and profile storage
- **Enhanced JSON serialization**: Comprehensive datetime, date, and Decimal handling

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "analyze.py"
participant Parser as "parser_service.py"
participant Gap as "gap_detector.py"
participant Hybrid as "hybrid_pipeline.py"
participant DB as "db_models.py"
Client->>Route : POST /api/analyze
Route->>Parser : parse_resume(...)
Parser-->>Route : parsed_data
Route->>Gap : analyze_gaps(parsed_data.work_experience)
Gap-->>Route : gap_analysis
Route->>Hybrid : run_hybrid_pipeline(...)
Hybrid-->>Route : result
Route->>DB : persist ScreeningResult
Route-->>Client : AnalysisResponse
```

**Diagram sources**
- [analyze.py:268-501](file://app/backend/routes/analyze.py#L268-L501)

**Section sources**
- [analyze.py:1-813](file://app/backend/routes/analyze.py#L1-L813)

## Enhanced AI Pipeline Capabilities

**Updated** The analysis engine now features sophisticated score rationales and comprehensive risk analysis capabilities that provide detailed explanations for each score dimension and structured risk summaries.

### Score Rationale Generation

The system generates detailed explanations for each score dimension:

- **Skill Rationale**: Explains the strength of skill matches, missing critical skills, and adjacent skills
- **Experience Rationale**: Details experience calculation methodology and required vs actual years
- **Education Rationale**: Describes degree relevance and field alignment scoring
- **Timeline Rationale**: Provides employment gap analysis and timeline interpretation
- **Domain Rationale**: Explains domain fit and architecture alignment assessment
- **Overall Rationale**: Synthesizes all factors into a comprehensive recommendation explanation

```mermaid
flowchart TD
Scores["_build_score_rationales()"] --> Skill["Skill Rationale"]
Scores --> Experience["Experience Rationale"]
Scores --> Education["Education Rationale"]
Scores --> Timeline["Timeline Rationale"]
Scores --> Domain["Domain Rationale"]
Skill --> Overall["Overall Rationale"]
Experience --> Overall
Education --> Overall
Timeline --> Overall
Domain --> Overall
Overall --> Output["score_rationales"]
```

**Diagram sources**
- [hybrid_pipeline.py:1480-1525](file://app/backend/services/hybrid_pipeline.py#L1480-L1525)

**Section sources**
- [hybrid_pipeline.py:1480-1525](file://app/backend/services/hybrid_pipeline.py#L1480-L1525)

### Structured Risk Summary

The risk summary provides comprehensive risk assessment:

- **Seniority Alignment**: Compares actual experience against required seniority level with specific ranges
- **Career Trajectory**: Analyzes upward progression, early career patterns, and single-role candidates
- **Stability Assessment**: Evaluates employment stability based on gaps, short stints, and job-hopping patterns
- **Risk Flags**: Converts risk signals into user-friendly format with severity levels

```mermaid
flowchart TD
RiskSignals["Risk Signals"] --> Flags["Risk Flags"]
RiskSignals --> Seniority["Seniority Alignment"]
RiskSignals --> Trajectory["Career Trajectory"]
RiskSignals --> Stability["Stability Assessment"]
Flags --> Summary["risk_summary"]
Seniority --> Summary
Trajectory --> Summary
Stability --> Summary
Summary --> Output["risk_summary"]
```

**Diagram sources**
- [hybrid_pipeline.py:1528-1600](file://app/backend/services/hybrid_pipeline.py#L1528-L1600)

**Section sources**
- [hybrid_pipeline.py:1528-1600](file://app/backend/services/hybrid_pipeline.py#L1528-L1600)

**Section sources**
- [hybrid_pipeline.py:1528-1600](file://app/backend/services/hybrid_pipeline.py#L1528-L1600)

## Intelligent Scoring Weights System

**Updated** The analysis engine now features a comprehensive intelligent scoring weights system that supports multiple weight schemas and provides automatic conversion between legacy and new formats.

### Weight Schema Support

The system supports three distinct weight schemas:

- **Legacy Schema (4 weights)**: skills, experience, stability, education
- **Old Backend Schema (7 weights)**: skills, experience, architecture, education, timeline, domain, risk
- **New Universal Schema (7 weights)**: core_competencies, experience, domain_fit, education, career_trajectory, role_excellence, risk

### Weight Mapping and Conversion

The weight mapper provides intelligent conversion between schemas:

```mermaid
flowchart TD
Input["Input Weights"] --> Detect["detect_weight_schema()"]
Detect --> Legacy{"Legacy Schema?"}
Detect --> OldBackend{"Old Backend Schema?"}
Detect --> New{"New Schema?"}
Detect --> Unknown{"Unknown Schema?"}
Legacy --> MapLegacy["map_legacy_to_new()"]
MapLegacy --> Normalize["normalize_weights()"]
OldBackend --> MapOld["map_old_backend_to_new()"]
MapOld --> Normalize
New --> Normalize
Unknown --> Merge["merge_with_defaults()"]
Merge --> Normalize
Normalize --> Output["Converted Weights"]
```

**Diagram sources**
- [weight_mapper.py:179-246](file://app/backend/services/weight_mapper.py#L179-L246)

### Weight Suggestion System

The LLM-based weight suggestion system analyzes job descriptions to provide optimal weight recommendations:

- **Role Category Detection**: Automatically identifies role categories (technical, sales, hr, marketing, operations, leadership)
- **Seniority Level Analysis**: Determines appropriate seniority levels for weight balancing
- **Context-Aware Recommendations**: Provides role-specific weight distributions with confidence scores
- **Adaptive Labels**: Generates role-specific labels for the role_excellence factor

**Section sources**
- [weight_mapper.py:20-360](file://app/backend/services/weight_mapper.py#L20-L360)
- [weight_suggester.py:86-177](file://app/backend/services/weight_suggester.py#L86-L177)

## Advanced Contact Extraction

**Updated** The analysis engine now features an intelligent contact extraction system that combines multiple extraction strategies for maximum accuracy with enhanced LLM contact extraction capabilities.

### Multi-Strategy Contact Extraction

The contact extraction system employs a tiered approach:

1. **LLM-Powered Extraction**: Uses gemma4:31b-cloud model for complex name formats and international names
2. **Regex-Based Extraction**: Traditional pattern matching for emails, phones, and LinkedIn URLs
3. **Fallback Strategies**: NER, email-based, relaxed header scanning, and filename-based extraction

```mermaid
flowchart TD
Start["Contact Extraction"] --> LLM["LLM Extraction<br/>(Most Accurate)"]
LLM --> LLMSuccess{"LLM Success?"}
LLMSuccess --> |Yes| Merge["merge_contact_info()"]
LLMSuccess --> |No| Regex["Regex Extraction<br/>(Standard Formats)"]
Regex --> Merge
Merge --> Fallback["Fallback Strategies<br/(NER → Email → Header → Filename)"]
Fallback --> Complete["Complete Contact Info"]
```

**Diagram sources**
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)
- [parser_service.py:1080-1126](file://app/backend/services/parser_service.py#L1080-L1126)

### Enhanced LLM Contact Extraction Strategy

The LLM extraction prioritizes accuracy over speed with conservative extraction principles:

- **Header Focus**: Uses first 1000 characters containing contact information
- **Structured JSON Output**: Forces LLM to return valid JSON with name, email, phone, linkedin fields
- **Conservative Extraction Principles**: Strict validation rules to prevent false positives
- **Enhanced Logging**: Comprehensive debug information for troubleshooting
- **Improved JSON Validation**: Robust parsing with markdown code block support
- **Edge Case Handling**: Handles international names, creative layouts, and non-standard formats
- **Timeout Management**: 15-second timeout to prevent blocking

**Section sources**
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)
- [parser_service.py:1080-1126](file://app/backend/services/parser_service.py#L1080-L1126)

## Enhanced Parser Service

**Updated** The parser service now features advanced multi-tier extraction strategies specifically designed for DOCX files and improved text recovery mechanisms.

### Multi-Tier DOCX Extraction Pipeline

The enhanced DOCX extraction uses a five-stage pipeline:

1. **Stage 1: Headers** - Extracts contact info from document headers
2. **Stage 2: Textboxes/Shapes** - Uses docx2txt for complex layouts
3. **Stage 3: Tables** - Extracts structured data from tables (common for contact info)
4. **Stage 4: Paragraphs** - Standard paragraph extraction
5. **Stage 5: XML Fallback** - Direct XML parsing for corrupted files

```mermaid
flowchart TD
Start["DOCX Extraction"] --> Headers["Stage 1: Headers<br/>(Contact Info)"]
Headers --> Textboxes["Stage 2: Textboxes<br/>(Complex Layouts)"]
Textboxes --> Tables["Stage 3: Tables<br/>(Structured Data)"]
Tables --> Paragraphs["Stage 4: Paragraphs<br/>(Standard Content)"]
Paragraphs --> XML["Stage 5: XML Fallback<br/>(Corrupted Files)"]
XML --> Dedup["Deduplication & Priority Sorting"]
Dedup --> Output["Final Text Output"]
```

**Diagram sources**
- [parser_service.py:343-492](file://app/backend/services/parser_service.py#L343-L492)

### Advanced Text Recovery and Deduplication

The parser implements sophisticated text recovery mechanisms:

- **Duplicate Detection**: Uses normalized text comparison to eliminate repeated content
- **Source Priority**: Prioritizes content from headers, textboxes, tables, then paragraphs
- **Line-by-Line Processing**: Processes text in lines to maintain readability
- **Fallback Chains**: Multiple fallback strategies for different failure modes

**Section sources**
- [parser_service.py:343-492](file://app/backend/services/parser_service.py#L343-L492)
- [parser_service.py:542-737](file://app/backend/services/parser_service.py#L542-L737)

## Streaming Endpoint Integration

**Updated** The analysis engine now features enhanced SSE streaming with heartbeat pings and background LLM processing for improved user experience.

### SSE Streaming Architecture

The streaming endpoint provides real-time analysis updates:

1. **Immediate Python Results**: Yields parsing stage with Python scores within 2 seconds
2. **Background LLM Processing**: Continues LLM analysis while streaming
3. **Heartbeat Pings**: Prevents timeouts with periodic SSE comments
4. **Polling Support**: Provides analysis_id for frontend polling after initial streaming

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "analyze_stream_endpoint"
participant Hybrid as "astream_hybrid_pipeline"
participant DB as "Database"
Client->>Route : POST /api/analyze/stream
Route->>Route : Validate & Create ScreeningResult
Route->>Hybrid : Start streaming pipeline
Hybrid->>Route : Yield {"stage" : "parsing", "result" : python_scores}
Route->>Client : SSE : parsing event
Route->>DB : Early save with Python scores
Hybrid->>Hybrid : Background LLM processing
Hybrid->>Route : Yield {"stage" : "complete", "result" : with analysis_id}
Route->>Client : SSE : complete event
Route->>DB : Final save with LLM results
```

**Diagram sources**
- [analyze.py:669-868](file://app/backend/routes/analyze.py#L669-L868)
- [hybrid_pipeline.py:2190-2284](file://app/backend/services/hybrid_pipeline.py#L2190-L2284)

### Streaming Configuration

The nginx configuration ensures proper streaming behavior:

- **Buffering Disabled**: `proxy_buffering off` prevents SSE event buffering
- **Timeout Extensions**: 600-second timeout for full LLM pipeline completion
- **Connection Handling**: `add_header X-Accel-Buffering no` for immediate delivery
- **Rate Limiting**: Separate limits for streaming vs regular API endpoints

**Section sources**
- [analyze.py:669-868](file://app/backend/routes/analyze.py#L669-L868)
- [hybrid_pipeline.py:2190-2284](file://app/backend/services/hybrid_pipeline.py#L2190-L2284)
- [nginx.prod.conf:73-98](file://app/nginx/nginx.prod.conf#L73-L98)

## Structured Risk Analysis

**Updated** The enhanced risk analysis system provides comprehensive risk assessment with structured summaries and detailed explanations.

### Risk Flag System

Risk flags are systematically generated from risk signals:

- **Type Normalization**: Converts internal risk types to user-friendly formats
- **Severity Classification**: Categorizes risks as low, medium, or high severity
- **Detail Description**: Provides specific explanations for each flagged risk
- **Comprehensive Coverage**: Includes gaps, skill mismatches, domain alignment, and stability issues

### Seniority Alignment Assessment

The system evaluates seniority fit using predefined experience ranges:

- **Intern**: 0-1 years
- **Junior**: 0-2 years  
- **Mid**: 2-5 years
- **Senior**: 5-10 years
- **Lead**: 7-15 years
- **Principal**: 10-25 years
- **Staff**: 8-20 years
- **Architect**: 10-25 years
- **Director**: 12-30 years

### Career Trajectory Analysis

Career progression is assessed through role title analysis:

- **Strong Upward**: Progression from junior to senior roles
- **Upward**: Current senior role or multiple positions
- **Early Career**: Single role or limited positions
- **Data-Driven**: Heuristic analysis of title keywords

### Stability Assessment

Employment stability is evaluated based on:

- **Critical Gaps**: 12+ month gaps indicating instability
- **Job-Hopping**: 3+ short stints (<6 months) suggesting instability
- **Moderate Concerns**: Single gaps or short stints
- **Stable**: No significant gaps or short stints detected

**Section sources**
- [hybrid_pipeline.py:1528-1600](file://app/backend/services/hybrid_pipeline.py#L1528-L1600)

## Model Configuration and Performance

**Updated** The analysis engine uses optimized model configurations for enhanced performance and reliability, with intelligent migration to gemma4:31b-cloud model across all services.

### Model Specifications

The system utilizes gemma4:31b-cloud model with optimized settings:

- **Model**: gemma4:31b-cloud (31 billion parameters) for all services
- **Temperature**: 0.1 for deterministic responses
- **Format**: JSON for structured output
- **num_predict**: 4096 tokens for cloud models (optimized for verbose output)
- **num_ctx**: 16384 context window for cloud models, 2048 for local models
- **keep_alive**: -1 for model persistence in RAM (local only)
- **Request Timeout**: 150 seconds (150s + 30s buffer)

### Cloud Model Optimization

**Enhanced** The system now includes intelligent model configuration based on deployment environment:

- **Cloud Detection**: Automatically detects Ollama Cloud (ollama.com) vs local deployment
- **Token Limits**: Cloud models receive 4096 tokens for num_predict to handle verbose output from large models
- **Context Windows**: Cloud models use 16384 context window for complex reasoning tasks
- **Authentication**: Automatic API key handling for Ollama Cloud with Authorization headers
- **Performance**: Maintains 2048 token limit for local models to optimize memory usage

### Performance Characteristics

- **Cold Start**: ~2 minutes for first load on CPU
- **Subsequent Requests**: 30-60 seconds typical
- **Concurrent Limit**: 2 LLM calls per worker
- **Memory Management**: Keep-alive sessions reduce cold-start latency
- **Prompt Optimization**: Reduced num_predict (2048) for local models minimizes KV cache allocation
- **Cloud Optimization**: 4096 token limit for cloud models handles verbose output from large models efficiently

### Environment Configuration

Key environment variables:

- **OLLAMA_BASE_URL**: Default localhost:11434 or https://ollama.com for cloud
- **OLLAMA_MODEL**: gemma4:31b-cloud (narrative model) for all services
- **OLLAMA_FAST_MODEL**: gemma4:31b-cloud (fast model) for all services
- **LLM_NARRATIVE_TIMEOUT**: 150 seconds default
- **OLLAMA_API_KEY**: Required for Ollama Cloud authentication
- **OLLAMA_HOST**: docker host for containerized deployments
- **OLLAMA_MAX_CONCURRENT**: Maximum concurrent LLM requests (auto-detected)
- **LLM_MAX_RETRIES**: Maximum retry attempts for LLM calls (default: 3)

**Section sources**
- [hybrid_pipeline.py:82-107](file://app/backend/services/hybrid_pipeline.py#L82-L107)
- [main.py:266-331](file://app/backend/main.py#L266-L331)

## Enhanced JSON Serialization Capabilities

**Updated** The analysis engine now features comprehensive JSON serialization capabilities designed to handle datetime objects, dates, and Decimal values consistently across all components. This enhancement significantly improves system stability and prevents production crashes when serializing complex analysis results.

### Core JSON Serialization Utilities

The system implements a unified `_json_default` function across multiple modules to handle non-serializable types:

```python
def _json_default(obj):
    """Handle non-serializable types for json.dumps (datetime, date, Decimal)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
```

### Key Implementation Areas

#### Route-Level Serialization
The analyze route implements comprehensive JSON serialization for:
- JD caching with datetime handling
- Candidate profile storage with mixed data types
- Screening result persistence
- SSE streaming with proper serialization

#### Agent Pipeline Serialization
The LangGraph agent pipeline includes:
- Custom `_json_default` function for consistent serialization
- Support for datetime and Decimal types in pipeline states
- JSON parsing helpers with fallback extraction

#### Service-Level Serialization
Various services implement JSON serialization for:
- Parser snapshot storage
- Gap analysis persistence
- LLM response handling
- Analysis result caching

### Benefits and Stability Improvements

The enhanced JSON serialization provides several critical benefits:

- **Production Stability**: Eliminates crashes when serializing complex analysis results containing datetime, date, or Decimal objects
- **Consistent Data Handling**: Unified approach ensures all components handle non-standard JSON types uniformly
- **Database Compatibility**: Proper conversion of datetime objects to ISO format strings for database storage
- **Decimal Precision**: Safe conversion of Decimal values to float for JSON compatibility while maintaining precision
- **Error Prevention**: Comprehensive type checking prevents runtime errors during serialization operations

### Error Handling and Fallback Mechanisms

The system includes robust error handling:
- Type-specific serialization with appropriate fallbacks
- Graceful degradation when encountering unexpected object types
- Comprehensive logging for serialization failures
- Automatic recovery mechanisms for partial serialization failures

**Section sources**
- [analyze.py:48-56](file://app/backend/routes/analyze.py#L48-L56)
- [agent_pipeline.py:39-45](file://app/backend/services/agent_pipeline.py#L39-L45)
- [hybrid_pipeline.py:16](file://app/backend/services/hybrid_pipeline.py#L16)
- [llm_service.py:1](file://app/backend/services/llm_service.py#L1)

## Enhanced Error Handling and Retry Systems

**Updated** The analysis engine now features comprehensive error handling and retry mechanisms with exponential backoff support for enhanced reliability and fault tolerance.

### Exponential Backoff Retry Mechanism

The hybrid pipeline implements sophisticated retry logic for LLM calls:

- **Rate Limiting (429)**: Automatic exponential backoff with base delay of 2 seconds
- **Connection Errors**: Retry with progressive delays for network connectivity issues
- **Timeout Handling**: Graceful degradation with fallback mechanisms
- **Authentication Failures**: Clear error messaging for invalid API keys
- **Server Errors**: Retry logic for temporary server failures (5xx)

```mermaid
flowchart TD
Start["LLM Call Attempt"] --> Call["Call LLM API"]
Call --> Success{"HTTP Status 200?"}
Success --> |Yes| Parse["Parse Response"]
Success --> |No| CheckError{"Error Type?"}
CheckError --> |429 Rate Limited| Backoff["Exponential Backoff<br/>Delay = 2^attempt + random(0,1)"]
Backoff --> Retry{"Retries < Max?"}
Retry --> |Yes| Call
Retry --> |No| RaiseError["Raise RuntimeError"]
CheckError --> |401 Unauthorized| AuthError["Authentication Failed"]
CheckError --> |408/408 Timeout| TimeoutError["Request Timeout"]
CheckError --> |500+ Server Error| ServerError["Server Error"]
AuthError --> RaiseError
TimeoutError --> RaiseError
ServerError --> RaiseError
Parse --> End["Return Result"]
```

**Diagram sources**
- [hybrid_pipeline.py:1369-1400](file://app/backend/services/hybrid_pipeline.py#L1369-L1400)

### Retry Configuration

- **Maximum Retries**: Configurable via `LLM_MAX_RETRIES` environment variable (default: 3)
- **Base Delay**: 2.0 seconds for exponential backoff calculation
- **Randomization**: ±1 second jitter to prevent thundering herd effects
- **Progressive Delays**: 2s, 6s, 14s, 30s, 62s (exponential with jitter)
- **Fallback Mechanism**: Higher temperature (0.3) retry for edge cases with empty responses

### Queue System Retry Integration

The queue manager provides complementary retry mechanisms:

- **Automatic Retry**: Configurable exponential backoff delays (1min, 5min, 15min)
- **Max Retries**: Configurable retry limits per job
- **Stale Job Recovery**: Automatic recovery of abandoned jobs
- **Heartbeat Monitoring**: Worker health monitoring and recovery
- **Failure Metrics**: Comprehensive error tracking and reporting

```mermaid
flowchart TD
Job["Analysis Job"] --> Process["Process Job"]
Process --> Success{"Processing Success?"}
Success --> |Yes| Complete["Mark Complete"]
Success --> |No| CheckRetry{"Retry Count < Max?"}
CheckRetry --> |Yes| Backoff["Exponential Backoff<br/>1min → 5min → 15min"]
Backoff --> Retry["Retry Job"]
CheckRetry --> |No| Fail["Mark Failed"]
Retry --> Process
Fail --> End["Job Failed"]
Complete --> End
```

**Diagram sources**
- [queue_manager.py:456-478](file://app/backend/services/queue_manager.py#L456-L478)

**Section sources**
- [hybrid_pipeline.py:1359-1500](file://app/backend/services/hybrid_pipeline.py#L1359-L1500)
- [queue_manager.py:206-208](file://app/backend/services/queue_manager.py#L206-L208)
- [queue_manager.py:456-478](file://app/backend/services/queue_manager.py#L456-L478)

## Resource Management and Concurrency Control

**Updated** The analysis engine implements comprehensive resource management and concurrency control to ensure optimal performance and reliability under various load conditions.

### Semaphore-Based Concurrency Control

The LLM service implements intelligent semaphore-based concurrency control:

- **Auto-Detection**: Automatically detects Ollama Cloud vs local deployment
- **Cloud Configuration**: Default 4 concurrent requests to avoid rate limits
- **Local Configuration**: Single-threaded access for local Ollama instances
- **Environment Override**: `OLLAMA_MAX_CONCURRENT` allows manual configuration
- **Shared Instance**: Singleton semaphore prevents resource contention across services

```mermaid
flowchart TD
Start["LLM Request"] --> GetSem["get_ollama_semaphore()"]
GetSem --> Check{"Semaphore Available?"}
Check --> |Yes| Acquire["Acquire Semaphore"]
Check --> |No| Wait["Wait for Available Slot"]
Acquire --> Call["Call LLM API"]
Wait --> Acquire
Call --> Release["Release Semaphore"]
Release --> End["Return Result"]
```

**Diagram sources**
- [llm_service.py:41-64](file://app/backend/services/llm_service.py#L41-L64)

### Health Monitoring and Sentinel System

The Ollama health sentinel provides continuous monitoring:

- **Background Loop**: Periodic health probes every `probe_interval` seconds
- **Model State Tracking**: Tracks COLD, WARMING, HOT, ERROR states
- **Cloud Detection**: Automatic detection of Ollama Cloud vs local instances
- **Latency Measurement**: Tracks last probe latency for performance monitoring
- **Graceful Degradation**: Continues operation even if health monitoring fails

### Background Task Management

Enhanced background task handling for graceful shutdown:

- **Task Registration**: Background tasks registered for tracking
- **Graceful Shutdown**: Tasks cancelled and awaited during application shutdown
- **Timeout Handling**: 5-second timeout for background task completion
- **Exception Safety**: All background tasks awaited with exception handling

### Memory and Resource Optimization

- **Model Hot-Loading**: Keep-alive sessions reduce cold-start latency
- **Context Window Optimization**: Reduced context size (2048 tokens) for local models
- **KV Cache Management**: Memory-efficient handling of large model contexts
- **Resource Cleanup**: Proper cleanup of semaphores and background tasks

**Section sources**
- [llm_service.py:35-66](file://app/backend/services/llm_service.py#L35-L66)
- [llm_service.py:74-171](file://app/backend/services/llm_service.py#L74-L171)
- [hybrid_pipeline.py:34-50](file://app/backend/services/hybrid_pipeline.py#L34-L50)
- [main.py:260-297](file://app/backend/main.py#L260-L297)

## Dependency Analysis
Key dependencies and relationships:
- Routes depend on parser, gap detector, hybrid pipeline, and models
- Hybrid pipeline depends on skills registry and Ollama
- Agent pipeline depends on LangGraph and ChatOllama
- Models define relationships among tenants, users, candidates, and screening results
- Startup checks validate DB connectivity, skills registry, and Ollama availability
- **Enhanced JSON serialization**: Unified serialization utilities across all components
- **AI-Enhanced Narratives**: `ai_enhanced` flag distinguishes LLM vs fallback narratives
- **Enhanced Contact Extraction**: LLM-powered contact extraction with merging strategy
- **Weight Management**: Comprehensive weight mapping and suggestion system
- **Enhanced Error Handling**: Exponential backoff retry mechanisms for LLM services
- **Resource Management**: Semaphore-based concurrency control and health monitoring
- **Queue Integration**: Automatic retry mechanisms with exponential backoff

```mermaid
graph LR
Route["routes/analyze.py<br/>JSON Utils<br/>SSE Streaming"] --> Parser["services/parser_service.py"]
Route --> Gap["services/gap_detector.py"]
Route --> Hybrid["services/hybrid_pipeline.py<br/>Enhanced Error Handling"]
Route --> Agent["services/agent_pipeline.py"]
Route --> Contact["services/llm_contact_extractor.py"]
Route --> WeightMapper["services/weight_mapper.py"]
Route --> WeightSuggester["services/weight_suggester.py"]
Route --> QueueManager["services/queue_manager.py<br/>Automatic Retry"]
Hybrid --> Skills["skills registry"]
Hybrid --> Ollama["Ollama (ChatOllama)<br/>Enhanced Error Handling"]
Agent --> Ollama
Route --> Models["models/db_models.py"]
Main["main.py<br/>Background Task Management"] --> Route
Main --> Ollama
Nginx["nginx.prod.conf<br/>Streaming Config"] --> Route
```

**Diagram sources**
- [analyze.py:32-38](file://app/backend/routes/analyze.py#L32-L38)
- [hybrid_pipeline.py:49-66](file://app/backend/services/hybrid_pipeline.py#L49-L66)
- [agent_pipeline.py:33-34](file://app/backend/services/agent_pipeline.py#L33-L34)
- [db_models.py:97-147](file://app/backend/models/db_models.py#L97-L147)
- [main.py:68-149](file://app/backend/main.py#L68-L149)
- [nginx.prod.conf:73-98](file://app/nginx/nginx.prod.conf#L73-L98)

**Section sources**
- [analyze.py:32-38](file://app/backend/routes/analyze.py#L32-L38)
- [db_models.py:97-147](file://app/backend/models/db_models.py#L97-L147)
- [main.py:68-149](file://app/backend/main.py#L68-L149)

## Performance Considerations
- Concurrency control: semaphore limits concurrent LLM calls to 2 per worker
- Model hot-loading: keep-alive sessions and in-memory caches reduce cold-start latency
- Prompt sizing: reduced num_predict (2048) and num_ctx (2048) to minimize KV cache allocation for local models
- Thread pool usage: blocking PDF parsing executed in asyncio.to_thread
- Streaming: SSE heartbeat pings prevent timeouts for long-running LLM calls
- Caching: JD cache shared across workers; skills registry hot-reloadable
- Memory management: JSON parsing utilities and bounded snapshot sizes
- **Enhanced AI Pipeline**: Optimized score rationale generation with minimal overhead
- **Model Optimization**: gemma4:31b-cloud model selected for balanced performance and cost
- **KV Cache Savings**: ~800MB reduction in memory usage for local models compared to default 4096 context
- **Cloud Optimization**: Intelligent token limit scaling for cloud models handling verbose output from large models
- **Multi-Tier Extraction**: Advanced DOCX extraction reduces processing time through intelligent fallback chains
- **Streaming Optimization**: Background LLM processing allows immediate response delivery
- **Error Handling**: Exponential backoff retry mechanisms improve system reliability under stress
- **Resource Management**: Semaphore-based concurrency control prevents resource exhaustion
- **Health Monitoring**: Continuous Ollama health checks enable proactive issue detection

## Troubleshooting Guide
Common issues and resolutions:
- Ollama unreachable or model not pulled: use health and diagnostic endpoints to inspect model readiness
- Scanned PDFs: parser raises explicit error advising text-based exports
- Database locked: SQLite concurrency limitation; restart backend container
- SSL certificate renewal: manual renewal and nginx restart on production
- Deploy failures: verify Docker Hub credentials, SSH keys, and VPS firewall
- **JSON serialization errors**: Enhanced error handling now provides detailed type information for debugging serialization failures
- **Datetime conversion issues**: Unified `_json_default` function ensures consistent datetime serialization across all components
- **Model loading issues**: Use `/api/llm-status` endpoint to diagnose model readiness and hot status
- **Performance degradation**: Monitor LLM timeouts and consider increasing LLM_NARRATIVE_TIMEOUT environment variable
- **KV Cache issues**: Reduced context size (2048 tokens) helps prevent memory pressure during LLM calls for local models
- **Cloud Model Issues**: Ensure OLLAMA_API_KEY is set for Ollama Cloud deployments; verify gemma4:31b-cloud model compatibility
- **Streaming Issues**: Check nginx configuration for proper SSE streaming with `proxy_buffering off`
- **Contact Extraction Failures**: LLM extraction falls back to regex and NER strategies automatically
- **Weight Schema Conflicts**: Use weight mapper to convert between legacy and new schemas seamlessly
- **Rate Limiting Errors**: Exponential backoff retry mechanism automatically handles 429 responses
- **Connection Timeouts**: Enhanced retry logic with progressive delays for network connectivity issues
- **Authentication Failures**: Clear error messaging for invalid OLLAMA_API_KEY configuration
- **Queue Processing Issues**: Automatic retry mechanisms with exponential backoff for failed jobs
- **Background Task Cleanup**: Graceful shutdown handles background LLM processing tasks

**Section sources**
- [main.py:228-259](file://app/backend/main.py#L228-L259)
- [main.py:262-327](file://app/backend/main.py#L262-L327)
- [parser_service.py:175-181](file://app/backend/services/parser_service.py#L175-L181)
- [README.md:337-375](file://README.md#L337-L375)

## Conclusion
The analysis engine blends efficient Python-first processing with a single, well-configured LLM call to deliver fast, deterministic scoring and rich narrative insights. The LangGraph agent pipeline enables scalable, multi-step workflows with structured nodes and robust fallbacks. The enhanced resume parsing service and gap detection provide reliable inputs, while the skills registry and scoring logic offer extensible, configurable evaluation criteria suitable for customization and growth.

**Updated** The enhanced AI pipeline capabilities now provide sophisticated score rationales and comprehensive risk analysis, generating detailed explanations for each score dimension and structured risk summaries including seniority alignment, career trajectory analysis, and stability assessments. The system maintains backward compatibility while delivering significantly improved explainability and risk assessment capabilities. The AI-enhanced narrative distinction system ensures clear differentiation between LLM-generated and fallback content, improving transparency for users. The migration to gemma4:31b-cloud model across all services provides enhanced performance and reliability, with intelligent token limit scaling for both local and cloud deployments.

The integration of comprehensive error handling with exponential backoff retry mechanisms, enhanced resource management through semaphore-based concurrency control, and health monitoring systems demonstrates the evolution toward a more robust and fault-tolerant analysis platform. The streaming endpoint enhancements provide real-time user feedback while maintaining system reliability through background processing and heartbeat mechanisms. The queue system integration adds automatic retry capabilities with exponential backoff, ensuring resilient job processing even under adverse conditions.

## Appendices

### Extension Points for Custom Evaluation Criteria
- Add new scoring dimensions: extend score_* functions and compute_fit_score weights
- Introduce custom risk signals: append to risk_signals computation
- Extend skills registry: add canonical skills and aliases; hot-reload via rebuild
- Customize LLM prompts: adjust explain_with_llm and agent pipeline prompts
- Add new resume sections: extend parser_service extraction logic
- **Enhanced AI Pipeline**: Leverage score rationales and risk summary structures for new evaluation criteria
- **Model Configuration**: Adjust gemma4:31b-cloud parameters for specialized use cases
- **AI-Enhanced Narratives**: Use `ai_enhanced` flag to indicate content origin
- **Weight Management**: Utilize weight mapper for schema conversion and weight_suggester for role-specific recommendations
- **Contact Enhancement**: Implement custom contact extraction strategies using LLM contact extractor framework
- **Error Handling**: Implement exponential backoff retry mechanisms for custom LLM integrations
- **Resource Management**: Add semaphore-based concurrency control for external service integrations

**Section sources**
- [hybrid_pipeline.py:953-1058](file://app/backend/services/hybrid_pipeline.py#L953-L1058)
- [hybrid_pipeline.py:350-426](file://app/backend/services/hybrid_pipeline.py#L350-L426)
- [agent_pipeline.py:327-365](file://app/backend/services/agent_pipeline.py#L327-L365)
- [parser_service.py:319-371](file://app/backend/services/parser_service.py#L319-L371)
- [llm_contact_extractor.py:133-164](file://app/backend/services/llm_contact_extractor.py#L133-L164)
- [weight_mapper.py:212-246](file://app/backend/services/weight_mapper.py#L212-L246)
- [weight_suggester.py:86-177](file://app/backend/services/weight_suggester.py#L86-L177)

### JSON Serialization Best Practices

**Updated** When extending the analysis engine with new evaluation criteria:

1. **Use Unified Serialization**: Leverage the existing `_json_default` function for consistent datetime, date, and Decimal handling
2. **Handle Mixed Types**: Ensure all new data structures can be safely serialized using the unified approach
3. **Test Edge Cases**: Verify serialization works correctly for boundary conditions and unusual data combinations
4. **Maintain Backward Compatibility**: Ensure new serialization logic doesn't break existing stored data formats
5. **Monitor Performance**: Track serialization overhead for large datasets and optimize where necessary
6. **Risk Assessment Integration**: When adding new risk signals, follow the structured risk summary format for consistency
7. **AI-Enhanced Content**: Use `ai_enhanced` flag to distinguish between LLM-generated and fallback content
8. **Streaming Compatibility**: Ensure all streamed data can be properly serialized for SSE transmission
9. **Error Handling**: Implement comprehensive error handling for serialization failures

**Section sources**
- [analyze.py:48-56](file://app/backend/routes/analyze.py#L48-L56)
- [agent_pipeline.py:39-45](file://app/backend/services/agent_pipeline.py#L39-L45)
- [hybrid_pipeline.py:16](file://app/backend/services/hybrid_pipeline.py#L16)

### Model Configuration Guidelines

**Updated** For optimal performance with the enhanced AI pipeline:

1. **Model Selection**: gemma4:31b-cloud provides balanced performance for both fast and reasoning tasks
2. **Cloud Deployment**: Use gemma4:31b-cloud for cloud deployments requiring verbose output from large models
3. **Resource Allocation**: Ensure sufficient RAM for model hot-loading and concurrent processing
4. **Timeout Configuration**: Adjust LLM_NARRATIVE_TIMEOUT based on deployment environment and model size
5. **Concurrency Control**: Monitor semaphore limits to prevent resource exhaustion
6. **Monitoring**: Use `/api/llm-status` endpoint for continuous model health monitoring
7. **Context Optimization**: The reduced context size (2048 tokens) provides ~800MB memory savings for local models
8. **Cloud Token Limits**: Cloud models automatically receive 4096 tokens for verbose output handling
9. **Authentication**: Set OLLAMA_API_KEY for secure cloud model access
10. **KV Cache Management**: Monitor memory usage during LLM calls to prevent overflow, especially with cloud models
11. **Streaming Optimization**: Configure nginx for proper SSE streaming with heartbeat mechanisms
12. **Error Handling**: Configure LLM_MAX_RETRIES environment variable for optimal retry behavior
13. **Resource Management**: Set OLLAMA_MAX_CONCURRENT for appropriate concurrency levels

**Section sources**
- [hybrid_pipeline.py:82-107](file://app/backend/services/hybrid_pipeline.py#L82-L107)
- [main.py:266-331](file://app/backend/main.py#L266-L331)
- [nginx.prod.conf:73-98](file://app/nginx/nginx.prod.conf#L73-L98)

### Contact Extraction Integration Guidelines

**Updated** For implementing custom contact extraction strategies:

1. **Use LLM Contact Extractor Framework**: Leverage the existing `extract_contact_with_llm()` function for structured JSON output
2. **Implement Merging Strategy**: Use `merge_contact_info()` to combine LLM and regex results intelligently
3. **Handle Edge Cases**: Account for international names, creative layouts, and non-standard formats
4. **Set Appropriate Timeouts**: Balance accuracy with performance using timeout parameters
5. **Fallback Chain**: Implement tiered extraction with LLM → Regex → NER → Filename strategies
6. **Validation**: Ensure extracted contact information meets business requirements
7. **Enhanced Logging**: Implement comprehensive logging for debugging and monitoring
8. **Error Handling**: Graceful degradation when LLM extraction fails
9. **Retry Mechanisms**: Implement exponential backoff for rate-limited LLM calls

**Section sources**
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)
- [parser_service.py:1080-1126](file://app/backend/services/parser_service.py#L1080-L1126)

### Weight Management Best Practices

**Updated** For effective weight management in the analysis engine:

1. **Schema Detection**: Use `detect_weight_schema()` to automatically identify input weight format
2. **Automatic Conversion**: Leverage `convert_to_new_schema()` for seamless schema transitions
3. **Role-Specific Weights**: Utilize `suggest_weights_for_jd()` for context-aware weight recommendations
4. **Default Handling**: Implement fallback weights using `get_default_weights_for_category()`
5. **Normalization**: Always use `normalize_weights()` to ensure proper weight distribution
6. **Adaptive Labels**: Generate role-specific labels with `get_weight_labels()`
7. **Confidence Scoring**: Consider confidence levels when using LLM-suggested weights
8. **Testing**: Validate weight conversions with comprehensive test suites
9. **Error Handling**: Implement retry mechanisms for weight suggestion failures

**Section sources**
- [weight_mapper.py:179-246](file://app/backend/services/weight_mapper.py#L179-L246)
- [weight_suggester.py:86-177](file://app/backend/services/weight_suggester.py#L86-L177)
- [weight_suggester.py:180-247](file://app/backend/services/weight_suggester.py#L180-L247)

### Error Handling and Retry Integration Guidelines

**Updated** For implementing robust error handling in custom extensions:

1. **Exponential Backoff**: Implement base delay of 2 seconds with exponential growth (2^n + random jitter)
2. **Retry Configuration**: Allow configurable maximum retry attempts via environment variables
3. **Error Categorization**: Distinguish between rate limiting (429), authentication (401), and server errors (5xx)
4. **Fallback Mechanisms**: Provide graceful degradation for critical failures
5. **Logging**: Implement comprehensive logging for error tracking and debugging
6. **Timeout Handling**: Set appropriate timeouts to prevent resource exhaustion
7. **Resource Management**: Use semaphores to prevent resource contention during retries
8. **Health Monitoring**: Implement health checks for external service dependencies
9. **Queue Integration**: Leverage queue manager retry mechanisms for persistent job processing
10. **Background Task Management**: Ensure proper cleanup of background tasks during error scenarios

**Section sources**
- [hybrid_pipeline.py:1359-1500](file://app/backend/services/hybrid_pipeline.py#L1359-L1500)
- [queue_manager.py:456-478](file://app/backend/services/queue_manager.py#L456-L478)
- [llm_service.py:41-64](file://app/backend/services/llm_service.py#L41-L64)