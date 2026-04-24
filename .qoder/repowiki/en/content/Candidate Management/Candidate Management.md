# Candidate Management

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [database.py](file://app/backend/db/database.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [llm_service.py](file://app/backend/services/llm_service.py)
- [llm_contact_extractor.py](file://app/backend/services/llm_contact_extractor.py)
- [weight_mapper.py](file://app/backend/services/weight_mapper.py)
- [weight_suggester.py](file://app/backend/services/weight_suggester.py)
- [gap_detector.py](file://app/backend/services/gap_detector.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [analysis_service.py](file://app/backend/services/analysis_service.py)
- [consensus_analyzer.py](file://app/backend/services/consensus_analyzer.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [candidates.py](file://app/backend/routes/candidates.py)
- [export.py](file://app/backend/routes/export.py)
- [compare.py](file://app/backend/routes/compare.py)
- [upload.py](file://app/backend/routes/upload.py)
- [002_parser_snapshot_json.py](file://alembic/versions/002_parser_snapshot_json.py)
- [008_analysis_queue_system.py](file://alembic/versions/008_analysis_queue_system.py)
- [009_intelligent_scoring_weights.py](file://alembic/versions/009_intelligent_scoring_weights.py)
- [015_add_resume_file_storage.py](file://alembic/versions/015_add_resume_file_storage.py)
- [test_candidate_dedup.py](file://app/backend/tests/test_candidate_dedup.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced candidate management with comprehensive resume file storage and retrieval capabilities
- Added support for storing original resume files in database with resume_file_data column
- Implemented download/view functionality for original uploaded resumes
- Integrated resume access into candidate workflows with tenant isolation
- Added chunked upload system for large file handling beyond Cloudflare limits
- Enhanced candidate profile storage with resume filename tracking

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document describes the candidate management system for Resume AI by ThetaLogics. It covers how candidate profiles are stored, how resumes are parsed and analyzed, how deduplication works across resumes and analysis results, and how search, filtering, history, and analysis results are managed. It also documents integration between parsing services and candidate data storage, bulk operations, export capabilities, and data portability features. Finally, it outlines strategies for extending candidate metadata and customizing parsing workflows, along with privacy and lifecycle considerations.

**Updated** Enhanced with comprehensive resume file storage and retrieval capabilities, including original file byte storage, download/view functionality, and integration with the analysis workflow.

## Project Structure
The candidate management system spans models, services, and routes:
- Models define the persistent entities (Candidate, ScreeningResult, JdCache, Skill, etc.) and relationships.
- Services encapsulate parsing, gap detection, hybrid pipeline scoring, LLM orchestration, intelligent weight management, and field-level data merging.
- Routes expose endpoints for analysis, candidate listing/detail, history, export, comparison, and weight suggestions.

```mermaid
graph TB
subgraph "Models"
C["Candidate"]
SR["ScreeningResult"]
JC["JdCache"]
SK["Skill"]
end
subgraph "Services"
PS["parser_service.py"]
LS["llm_service.py"]
LCE["llm_contact_extractor.py"]
WM["weight_mapper.py"]
WS["weight_suggester.py"]
GD["gap_detector.py"]
HP["hybrid_pipeline.py"]
AS["analysis_service.py"]
CA["consensus_analyzer.py"]
end
subgraph "Routes"
RA["analyze.py"]
RC["candidates.py"]
RE["export.py"]
RCM["compare.py"]
RU["upload.py"]
end
RA --> PS
RA --> LS
RA --> LCE
RA --> WM
RA --> WS
RA --> GD
RA --> HP
RA --> AS
RA --> CA
RA --> C
RA --> SR
RA --> JC
RC --> C
RC --> SR
RE --> SR
RCM --> SR
RU --> C
```

**Diagram sources**
- [db_models.py:97-150](file://app/backend/models/db_models.py#L97-L150)
- [parser_service.py:130-552](file://app/backend/services/parser_service.py#L130-L552)
- [llm_service.py:163-314](file://app/backend/services/llm_service.py#L163-L314)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)
- [weight_mapper.py:20-360](file://app/backend/services/weight_mapper.py#L20-L360)
- [weight_suggester.py:86-307](file://app/backend/services/weight_suggester.py#L86-L307)
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)
- [hybrid_pipeline.py:467-800](file://app/backend/services/hybrid_pipeline.py#L467-L800)
- [analysis_service.py:6-121](file://app/backend/services/analysis_service.py#L6-L121)
- [consensus_analyzer.py:278-316](file://app/backend/services/consensus_analyzer.py#L278-L316)
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [candidates.py:26-189](file://app/backend/routes/candidates.py#L26-L189)
- [export.py:20-104](file://app/backend/routes/export.py#L20-L104)
- [compare.py:16-77](file://app/backend/routes/compare.py#L16-L77)
- [upload.py:1-361](file://app/backend/routes/upload.py#L1-L361)

**Section sources**
- [README.md:201-229](file://README.md#L201-L229)
- [database.py:1-33](file://app/backend/db/database.py#L1-L33)

## Core Components
- Candidate entity stores enriched profile fields, parser snapshot, and metadata used for deduplication and re-analysis.
- ScreeningResult persists analysis outcomes, weights metadata, narrative data, and links to candidates and role templates.
- Parser service extracts text and structured data from resumes with enhanced DOCX fallback and multi-stage extraction.
- LLM service provides reliable analysis with validated fit_score and final_recommendation fields.
- LLM contact extractor provides accurate contact information extraction using Gemini model with fallback strategies.
- Weight mapper and suggester services manage intelligent scoring weights with universal schema support and role-adaptive recommendations.
- Gap detector computes timelines, gaps, overlaps, and total experience.
- Hybrid pipeline orchestrates Python-based scoring and LLM narrative with support for new weight schemas.
- Consensus analyzer processes multiple analysis results with field-level merge strategy preserving critical fields.
- Deduplication logic identifies duplicates across email, file hash, and name+phone.
- Routes expose endpoints for single and batch analysis, candidate listing/detail, history, export, comparison, and weight suggestions.
- **Updated**: Resume file storage system with LargeBinary column for original file bytes and filename tracking.
- **Updated**: Chunked upload system for handling large files beyond Cloudflare limits.
- **Updated**: Download/view functionality for accessing original uploaded resumes.

**Updated** Enhanced with comprehensive resume file storage and retrieval capabilities, including original file byte storage, download/view functionality, and integration with the analysis workflow.

**Section sources**
- [db_models.py:97-150](file://app/backend/models/db_models.py#L97-L150)
- [parser_service.py:193-552](file://app/backend/services/parser_service.py#L193-L552)
- [llm_service.py:263-284](file://app/backend/services/llm_service.py#L263-L284)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)
- [weight_mapper.py:20-360](file://app/backend/services/weight_mapper.py#L20-L360)
- [weight_suggester.py:86-307](file://app/backend/services/weight_suggester.py#L86-L307)
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)
- [hybrid_pipeline.py:467-800](file://app/backend/services/hybrid_pipeline.py#L467-L800)
- [consensus_analyzer.py:278-316](file://app/backend/services/consensus_analyzer.py#L278-L316)
- [analyze.py:147-214](file://app/backend/routes/analyze.py#L147-L214)
- [upload.py:1-361](file://app/backend/routes/upload.py#L1-L361)

## Architecture Overview
The system integrates parsing, gap detection, hybrid scoring, intelligent weight management, and persistence. Deduplication ensures candidate identity is preserved across uploads and re-analyses. Profiles are stored for fast re-analysis and auditability with enhanced contact extraction capabilities and field-level data integrity. The unified API response approach ensures consistent data structures across all endpoints. **Updated**: The architecture now includes comprehensive resume file storage with LargeBinary column for original file bytes and filename tracking.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "analyze.py"
participant Parser as "parser_service.py"
participant LLM as "llm_service.py"
participant LLMContact as "llm_contact_extractor.py"
participant Gap as "gap_detector.py"
participant Pipe as "hybrid_pipeline.py"
participant DB as "DB (SQLAlchemy)"
participant Cand as "Candidate"
participant Res as "ScreeningResult"
Client->>Route : POST /api/analyze (resume, job_description, scoring_weights)
Route->>Parser : parse_resume()
Parser->>LLMContact : extract_contact_with_llm()
LLMContact-->>Parser : contact_info
Parser-->>Route : parsed_data + contact_info
Route->>Gap : analyze_gaps(work_experience)
Gap-->>Route : gap_analysis
Route->>Pipe : run_hybrid_pipeline(parsed_data, gap_analysis, jd, weights)
Pipe->>LLM : analyze_with_llm()
LLM-->>Pipe : validated_analysis_result
Pipe-->>Route : analysis_result + fit_score
Route->>DB : _get_or_create_candidate(file_content, filename)
DB-->>Route : candidate_id, is_dup
Route->>DB : persist ScreeningResult (with weights metadata)
DB-->>Route : result_id
Route-->>Client : analysis_result + candidate_id/result_id
```

**Diagram sources**
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [parser_service.py:547-552](file://app/backend/services/parser_service.py#L547-L552)
- [llm_service.py:297-314](file://app/backend/services/llm_service.py#L297-L314)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)
- [gap_detector.py:217-219](file://app/backend/services/gap_detector.py#L217-L219)
- [hybrid_pipeline.py:467-800](file://app/backend/services/hybrid_pipeline.py#L467-L800)
- [db_models.py:97-150](file://app/backend/models/db_models.py#L97-L150)

## Detailed Component Analysis

### Candidate Profile Storage
- Candidate stores:
  - Contact info and derived fields (current_role, current_company, total_years_exp).
  - Enriched profile fields: raw_resume_text, parsed_skills, parsed_education, parsed_work_exp, gap_analysis_json.
  - parser_snapshot_json: full parser output snapshot for auditability and re-analysis.
  - resume_file_hash: MD5 of file bytes for deduplication.
  - **Updated**: resume_filename: Original filename of uploaded resume.
  - **Updated**: resume_file_data: LargeBinary column storing original file bytes.
  - profile_updated_at and profile_quality for freshness and quality tracking.
- Stored on first analysis or when explicitly updating profile.

```mermaid
erDiagram
CANDIDATE {
int id PK
int tenant_id FK
string name
string email
string phone
string resume_file_hash
string resume_filename
largebinary resume_file_data
text raw_resume_text
text parsed_skills
text parsed_education
text parsed_work_exp
text gap_analysis_json
string current_role
string current_company
float total_years_exp
string profile_quality
timestamp profile_updated_at
text parser_snapshot_json
}
```

**Diagram sources**
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)
- [002_parser_snapshot_json.py:21-33](file://alembic/versions/002_parser_snapshot_json.py#L21-L33)
- [015_add_resume_file_storage.py:7-9](file://alembic/versions/015_add_resume_file_storage.py#L7-L9)

**Section sources**
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)
- [002_parser_snapshot_json.py:1-33](file://alembic/versions/002_parser_snapshot_json.py#L1-L33)
- [015_add_resume_file_storage.py:1-49](file://alembic/versions/015_add_resume_file_storage.py#L1-L49)

### Enhanced Resume Parsing and Extraction Workflows
- ResumeParser supports PDF, DOCX, DOC, TXT, RTF, HTML, ODT, and plain text with enhanced multi-stage extraction pipeline.
- Extracts raw text, work experience, skills, education, and contact info with improved accuracy.
- Enriches parsed output with LLM-based contact extraction as the primary method, falling back to regex/NLP methods.
- Uses PyMuPDF with pdfplumber fallback for PDFs; enhanced DOCX fallback with paragraph and table extraction.
- Normalizes Unicode and implements comprehensive error handling with graceful fallbacks.

**Updated** Enhanced with new LLM contact extraction capabilities and improved DOCX fallback processing.

```mermaid
flowchart TD
Start(["parse_resume()"]) --> ExtText["extract_text()"]
ExtText --> PDF{"PDF?"}
PDF --> |Yes| PMU["PyMuPDF get_text()"]
PMU --> Empty{"Empty?"}
Empty --> |Yes| PL["pdfplumber fallback"]
Empty --> |No| DonePDF["Text ready"]
PDF --> |No| DOCX{"DOCX?"}
DOCX --> |Yes| DOCXRead["Read paragraphs + tables + enhanced fallback"]
DOCX --> |No| TXT{"TXT?"}
TXT --> |Yes| ReturnTxt["Return decoded text"]
TXT --> |No| Error["Raise unsupported format"]
PL --> DonePDF
DOCXRead --> DonePDF
DonePDF --> Build["Build parsed_data"]
ReturnTxt --> Build
Build --> Enrich["enrich_parsed_resume()"]
Enrich --> LLMContact["extract_contact_with_llm()"]
LLMContact --> MergeContact["merge_contact_info()"]
MergeContact --> End(["Return parsed_data"])
```

**Diagram sources**
- [parser_service.py:142-193](file://app/backend/services/parser_service.py#L142-L193)
- [parser_service.py:152-191](file://app/backend/services/parser_service.py#L152-L191)
- [parser_service.py:533-552](file://app/backend/services/parser_service.py#L533-L552)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)

**Section sources**
- [parser_service.py:22-128](file://app/backend/services/parser_service.py#L22-L128)
- [parser_service.py:130-552](file://app/backend/services/parser_service.py#L130-L552)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)

### LLM Service and Field-Level Validation
- **Reliable Analysis**: Provides validated fit_score (0-100) and final_recommendation fields with strict validation.
- **Structured Output**: Returns JSON with fit_score, strengths, weaknesses, education_analysis, risk_signals, and final_recommendation.
- **Field Validation**: Ensures fit_score stays within bounds, arrays are limited to 5 items, and recommendations are valid.
- **Fallback Mechanism**: Provides default values when LLM analysis fails.

**Updated** Enhanced with field-level validation that preserves critical analysis fields during narrative integration.

**Section sources**
- [llm_service.py:263-284](file://app/backend/services/llm_service.py#L263-L284)
- [llm_service.py:286-294](file://app/backend/services/llm_service.py#L286-L294)

### LLM Contact Extraction System
- **Primary Method**: LLM-based contact extraction using Gemini model for highest accuracy.
- **Fallback Strategy**: spaCy NER, email-based extraction, relaxed header scanning, and filename-based extraction.
- **Enhanced Accuracy**: Handles international names, creative layouts, and edge cases with structured JSON output.
- **Timeout Handling**: Configurable timeouts with graceful degradation to fallback methods.
- **Validation**: Structured validation and cleaning of extracted contact information.

**New Feature** Comprehensive LLM contact extraction system with multiple fallback layers for improved accuracy.

**Section sources**
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)

### Intelligent Scoring Weights System
- **Universal Schema**: New 7-weight schema supporting core_competencies, experience, domain_fit, education, career_trajectory, role_excellence, and risk.
- **Backward Compatibility**: Automatic conversion from legacy 4-weight and old 7-weight schemas.
- **Role Adaptation**: AI-powered weight suggestions based on job description analysis.
- **Version Management**: ScreeningResult includes version tracking and active status for historical comparisons.
- **Adaptive Labels**: Dynamic weight labels based on role categories (technical, sales, hr, marketing, etc.).

**New Feature** Complete intelligent scoring weights system with universal schema support and AI-powered suggestions.

```mermaid
flowchart TD
StartWeights["Weight Input"] --> Detect{"Detect Schema Type"}
Detect --> |Legacy 4-weight| Legacy["map_legacy_to_new()"]
Detect --> |Old 7-weight| OldBackend["map_old_backend_to_new()"]
Detect --> |New 7-weight| NewSchema["normalize_weights()"]
Legacy --> Convert["convert_to_new_schema()"]
OldBackend --> Convert
NewSchema --> Convert
Convert --> WeightsOut["Normalized Weights"]
WeightsOut --> Persist["Persist to ScreeningResult"]
```

**Diagram sources**
- [weight_mapper.py:212-246](file://app/backend/services/weight_mapper.py#L212-L246)
- [weight_suggester.py:86-178](file://app/backend/services/weight_suggester.py#L86-L178)

**Section sources**
- [weight_mapper.py:20-360](file://app/backend/services/weight_mapper.py#L20-L360)
- [weight_suggester.py:86-307](file://app/backend/services/weight_suggester.py#L86-L307)
- [009_intelligent_scoring_weights.py:27-74](file://alembic/versions/009_intelligent_scoring_weights.py#L27-L74)

### Gap Detection and Timeline Analysis
- Converts dates to YYYY-MM, merges overlapping intervals, and computes total effective years.
- Produces employment timeline entries with gap metadata and severity.
- Flags overlapping jobs and short stints.

```mermaid
flowchart TD
StartGD(["analyze_gaps()"]) --> Normalize["Normalize dates to YYYY-MM"]
Normalize --> Intervals["Build intervals (start,end)"]
Intervals --> Merge["Merge overlapping intervals"]
Merge --> Sum["Sum merged intervals to total months"]
Sum --> Timeline["Build employment timeline with gaps"]
Timeline --> Flags["Detect overlaps and short stints"]
Flags --> ReturnGD(["Return gap_analysis"])
```

**Diagram sources**
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)

**Section sources**
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)

### Hybrid Pipeline and Enhanced Scoring
- Python rules parse JD, build candidate profile, match skills, score education/timeline, and compute fit score.
- LLM adds narrative, strengths/weaknesses, and explainability.
- Skills registry supports dynamic skill discovery and alias expansion.
- **Updated**: Enhanced scoring with intelligent weight system supporting new universal schema.
- **Updated**: Automatic weight conversion from legacy formats to new schema.

**Updated** Integrated intelligent scoring weights system with universal schema support and automatic conversion.

```mermaid
sequenceDiagram
participant Route as "analyze.py"
participant HP as "hybrid_pipeline.py"
participant WM as "weight_mapper.py"
participant SR as "ScreeningResult"
Route->>WM : convert_to_new_schema(scoring_weights)
WM-->>Route : normalized_weights
Route->>HP : run_hybrid_pipeline(resume_text, job_description, parsed_data, gap_analysis, jd_analysis, weights)
HP->>LLM : analyze_with_llm()
LLM-->>HP : validated_analysis_result
HP-->>Route : result (scores, matched/missing skills, breakdown)
Route->>SR : persist ScreeningResult (with weights metadata)
SR-->>Route : result_id
Route-->>Route : attach candidate_id/result_id
```

**Diagram sources**
- [analyze.py:304-318](file://app/backend/routes/analyze.py#L304-L318)
- [hybrid_pipeline.py:467-800](file://app/backend/services/hybrid_pipeline.py#L467-L800)
- [weight_mapper.py:212-246](file://app/backend/services/weight_mapper.py#L212-L246)

**Section sources**
- [hybrid_pipeline.py:467-800](file://app/backend/services/hybrid_pipeline.py#L467-L800)
- [analysis_service.py:6-121](file://app/backend/services/analysis_service.py#L6-L121)

### Enhanced Candidate Comparison Algorithm with JSON Safety Checks
**Critical Update**: Implemented comprehensive JSON parsing safety checks and redesigned comparison algorithm with priority-based data sources.

- **JSON Safety**: Implements `_safe_loads()` function with comprehensive error handling for malformed JSON data.
- **Priority-Based Data Sources**: Analysis data takes precedence over parsed data with robust fallback mechanisms.
- **Enhanced Comparison Fields**: Includes employment_gaps, interview_questions_preview, analysis_quality, and adjacent_skills.
- **Winner Determination**: Calculates winners across multiple categories (overall, skills, experience, education, stability).
- **Candidate Name Resolution**: Priority-based resolution from analysis_result, parsed_data, or Candidate table.
- **Score Breakdown Defaults**: Ensures score_breakdown has all expected keys with sensible defaults.

```mermaid
flowchart TD
StartCompare(["compare_candidates()"]) --> ValidateIDs["Validate candidate_ids (2-5)"]
ValidateIDs --> QueryDB["Query ScreeningResults with tenant filter"]
QueryDB --> CheckResults{"Enough results found?"}
CheckResults --> |No| Error["HTTP 404 Not enough results"]
CheckResults --> |Yes| Iterate["Iterate through results"]
Iterate --> SafeLoad["Safe JSON loads with error handling"]
SafeLoad --> NameResolution["Priority-based candidate name resolution"]
NameResolution --> DataSourceCheck["Check analysis data completeness"]
DataSourceCheck --> HasAnalysis{"Has essential analysis fields?"}
HasAnalysis --> |Yes| UseAnalysis["Use analysis data as primary source"]
HasAnalysis --> |No| UseParsed["Use parsed_data as fallback"]
UseAnalysis --> ProfileFallback["Resolve candidate_profile from analysis or Candidate"]
UseParsed --> ProfileFallback
ProfileFallback --> InterviewPreview["Extract interview questions preview"]
InterviewPreview --> AppendResult["Append to comparison array"]
AppendResult --> NextResult{"More results?"}
NextResult --> |Yes| Iterate
NextResult --> |No| CalculateWinners["Calculate winners across categories"]
CalculateWinners --> ReturnResults["Return comparison results"]
```

**Diagram sources**
- [compare.py:17-158](file://app/backend/routes/compare.py#L17-L158)

**Section sources**
- [compare.py:17-158](file://app/backend/routes/compare.py#L17-L158)

### Enhanced Resume File Storage and Retrieval System
**New Feature**: Comprehensive resume file storage and retrieval system with tenant isolation and security.

- **Database Storage**: Candidate model now includes resume_file_data (LargeBinary) and resume_filename (String) columns for storing original uploaded files.
- **File Hashing**: resume_file_hash column enables deduplication across identical resumes regardless of filename.
- **Tenant Isolation**: All resume operations respect tenant boundaries for security and data separation.
- **Download/View Functionality**: REST API endpoint `/api/candidates/{candidate_id}/resume` provides secure access to original files.
- **Format Support**: Supports PDF, DOCX, DOC, ODT, TXT, and RTF formats with appropriate MIME type handling.
- **Security Measures**: File access requires authentication and authorization; unauthorized access attempts are blocked.
- **Storage Optimization**: LargeBinary storage enables direct file retrieval without external file system dependencies.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "candidates.py"
participant DB as "DB"
participant Candidate as "Candidate"
Client->>Route : GET /api/candidates/{candidate_id}/resume
Route->>DB : Query Candidate with tenant filter
DB-->>Route : Candidate record
Route->>Route : Validate file exists and belongs to tenant
Route->>Client : Response with file bytes + appropriate headers
```

**Diagram sources**
- [candidates.py:504-559](file://app/backend/routes/candidates.py#L504-L559)
- [db_models.py:112-116](file://app/backend/models/db_models.py#L112-L116)

**Section sources**
- [db_models.py:112-116](file://app/backend/models/db_models.py#L112-L116)
- [candidates.py:504-559](file://app/backend/routes/candidates.py#L504-L559)
- [015_add_resume_file_storage.py:1-49](file://alembic/versions/015_add_resume_file_storage.py#L1-L49)

### Chunked Upload System for Large Files
**New Feature**: Robust chunked upload system designed to handle files exceeding Cloudflare limits.

- **Cloudflare Compliance**: Solves 100MB upload limit by splitting files into manageable chunks.
- **Temporary Storage**: Chunks are stored in `/tmp/aria_chunks/{upload_id}/` with automatic cleanup after 24 hours.
- **Integrity Verification**: MD5 hash verification ensures file integrity during assembly.
- **Parallel Processing**: Up to 3 chunks processed concurrently for optimal performance.
- **Metadata Tracking**: Upload metadata stored with user and tenant information for audit trails.
- **Cleanup Automation**: Automatic cleanup of orphaned chunks prevents storage bloat.
- **Error Recovery**: Comprehensive error handling with detailed failure messages for troubleshooting.

```mermaid
flowchart TD
StartUpload["Client initiates upload"] --> SplitChunks["Split file into chunks"]
SplitChunks --> UploadLoop["Upload chunks sequentially"]
UploadLoop --> VerifyChunks["Verify all chunks received"]
VerifyChunks --> AssembleFile["Assemble chunks into complete file"]
AssembleFile --> VerifyIntegrity["Verify MD5 hash"]
VerifyIntegrity --> Success["Return assembled file path"]
```

**Diagram sources**
- [upload.py:99-205](file://app/backend/routes/upload.py#L99-L205)
- [upload.py:207-324](file://app/backend/routes/upload.py#L207-L324)

**Section sources**
- [upload.py:1-361](file://app/backend/routes/upload.py#L1-L361)

### Deduplication Strategies
- Three-layer deduplication:
  1) Email match within tenant.
  2) File hash match (MD5 of bytes).
  3) Name + phone match within tenant.
- On duplicate detection, returns duplicate_candidate metadata and avoids re-parsing unless requested.
- Supports actions:
  - create_new: always create new candidate.
  - update_profile: update stored profile.
  - use_existing: skip re-analysis and reuse stored profile.

**Updated** Enhanced with resume file hash deduplication that identifies identical resumes across different filenames.

```mermaid
flowchart TD
StartDup(["_get_or_create_candidate"]) --> Action{"action == create_new?"}
Action --> |Yes| Create["Create new Candidate"]
Action --> |No| L1["Layer 1: email match"]
L1 --> Found1{"Found?"}
Found1 --> |Yes| ReturnDup["Return existing id, is_dup=True"]
Found1 --> |No| L2["Layer 2: file_hash match"]
L2 --> Found2{"Found?"}
Found2 --> |Yes| ReturnDup
Found2 --> |No| L3["Layer 3: name+phone match"]
L3 --> Found3{"Found?"}
Found3 --> |Yes| ReturnDup
Found3 --> |No| Create
Create --> Store["Store profile if gap_analysis provided"]
Store --> ReturnNew["Return new id, is_dup=False"]
```

**Diagram sources**
- [analyze.py:147-214](file://app/backend/routes/analyze.py#L147-L214)

**Section sources**
- [analyze.py:72-116](file://app/backend/routes/analyze.py#L72-L116)
- [test_candidate_dedup.py:158-265](file://app/backend/tests/test_candidate_dedup.py#L158-L265)

### Candidate Search and Filtering
- List candidates with pagination and optional search by name or email.
- Detail endpoint returns enriched profile, skills snapshot, and history with unified data structure.
- GET /api/history lists recent screening results for the tenant.

```mermaid
sequenceDiagram
participant Client as "Client"
participant CandRoute as "candidates.py"
participant DB as "DB"
Client->>CandRoute : GET /api/candidates?page=&page_size=&search=
CandRoute->>DB : query(Candidate).filter(tenant).search
DB-->>CandRoute : candidates
CandRoute-->>Client : enriched list with unified structure
Client->>CandRoute : GET /api/candidates/{id}
CandRoute->>DB : query(Candidate) + ScreeningResult
DB-->>CandRoute : candidate + history
CandRoute-->>Client : detail + history with unified structure
```

**Diagram sources**
- [candidates.py:26-189](file://app/backend/routes/candidates.py#L26-L189)

**Section sources**
- [candidates.py:26-189](file://app/backend/routes/candidates.py#L26-L189)

### History Tracking and Analysis Result Management
- ScreeningResult persists parsed_data and analysis_result as JSON for auditability.
- **Updated**: Enhanced with intelligent scoring weights metadata (role_category, weight_reasoning, suggested_weights_json).
- **Updated**: Version management with is_active flag and version_number for historical tracking.
- **Updated**: API response unification ensures consistent data structure across all history endpoints.
- **Updated**: Field-level merge strategy ensures critical analysis fields remain intact during narrative integration.
- History endpoint aggregates recent results with fit_score, recommendation, and risk level.
- Candidate detail endpoint augments history with analysis quality and score breakdown.

**Updated** Enhanced with API response unification that ensures consistent data structure across all history endpoints and field-level merge strategy that preserves critical analysis fields during narrative integration.

**Section sources**
- [db_models.py:128-150](file://app/backend/models/db_models.py#L128-L150)
- [analyze.py:763-786](file://app/backend/routes/analyze.py#L763-L786)
- [candidates.py:122-140](file://app/backend/routes/candidates.py#L122-L140)
- [009_intelligent_scoring_weights.py:27-74](file://alembic/versions/009_intelligent_scoring_weights.py#L27-L74)

### Integration Between Parsing Services and Candidate Data Storage
- After parsing and gap analysis, the hybrid pipeline produces a result with enhanced weight system.
- The route persists both the ScreeningResult with weights metadata and updates the Candidate profile snapshot.
- parser_snapshot_json captures the complete parser output for re-analysis and auditing.
- **Updated**: Weight metadata is stored with screening results for future comparisons and analysis.
- **Updated**: API response unification ensures consistent data structure across all integration points.
- **Updated**: Field-level merge strategy ensures data integrity during narrative integration.
- **Updated**: Resume file storage integrates seamlessly with the analysis workflow, storing original file bytes and filename.

**Updated** Integrated intelligent scoring weights system into the parsing and storage workflow with enhanced field-level data protection and API response unification.

**Section sources**
- [analyze.py:454-476](file://app/backend/routes/analyze.py#L454-L476)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)

### Bulk Operations and Export Capabilities
- Batch analysis endpoint supports multiple resumes with plan-based limits and usage enforcement.
- Export endpoints (CSV/Excel) stream screening results for selected IDs or all recent results.
- **Updated**: Export includes enhanced weight metadata and version information for comprehensive reporting.
- **Updated**: API response unification ensures consistent data structure in exported results.
- **Updated**: Field-level merge strategy ensures exported data maintains critical analysis field integrity.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "analyze.py"
participant DB as "DB"
participant Export as "export.py"
Client->>Route : POST /api/analyze/batch (resumes, job_description, scoring_weights)
Route->>DB : persist ScreeningResults (with weights metadata)
DB-->>Route : result_ids
Route-->>Client : ranked batch results
Client->>Export : GET /api/export/csv?ids=
Export->>DB : fetch results (including weights metadata)
DB-->>Export : rows
Export-->>Client : CSV stream with unified structure
```

**Diagram sources**
- [analyze.py:651-758](file://app/backend/routes/analyze.py#L651-L758)
- [export.py:55-104](file://app/backend/routes/export.py#L55-L104)

**Section sources**
- [analyze.py:651-758](file://app/backend/routes/analyze.py#L651-L758)
- [export.py:20-104](file://app/backend/routes/export.py#L20-L104)

### Data Portability Features
- parser_snapshot_json stores the complete parser output, enabling:
  - Re-analysis without re-parsing resume patterns.
  - Auditability and reproducibility of parsing decisions.
  - Export of raw parsed fields alongside analysis results.
- **Updated**: Enhanced with intelligent scoring weights metadata for comprehensive data portability.
- **Updated**: API response unification ensures consistent data structure for portable results.
- **Updated**: Field-level merge strategy ensures portable data maintains critical analysis field integrity.
- **Updated**: Resume file storage enables complete data portability with original file bytes.

**Updated** Enhanced parser snapshot with intelligent scoring weights metadata for improved portability and data integrity with API response unification.

**Section sources**
- [db_models.py:120-121](file://app/backend/models/db_models.py#L120-L121)
- [002_parser_snapshot_json.py:1-33](file://alembic/versions/002_parser_snapshot_json.py#L1-L33)

### Extending Candidate Metadata and Customizing Parsing Workflows
- Extend Candidate fields by adding columns to the Candidate model and updating storage logic.
- Customize parsing by modifying ResumeParser methods (e.g., additional sections, new date patterns).
- Adjust skills registry and matching by updating skills lists and aliases in the SkillsRegistry.
- **Updated**: Enhance contact extraction by integrating LLM contact extractor into parsing pipeline.
- **Updated**: Customize weight schemas by extending weight mapper and suggester services.
- **Updated**: Extend field-level merge strategy by adding new critical fields to preservation logic.
- **Updated**: API response unification allows for consistent extension of data structures across all endpoints.
- **Updated**: Resume file storage system provides foundation for additional file-related metadata extensions.

**Updated** Enhanced with LLM contact extraction integration, customizable weight schemas, extensible field-level merge strategy, and API response unification for consistent data structure extensions.

**Section sources**
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)
- [parser_service.py:130-552](file://app/backend/services/parser_service.py#L130-L552)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)
- [weight_mapper.py:20-360](file://app/backend/services/weight_mapper.py#L20-L360)
- [hybrid_pipeline.py:323-426](file://app/backend/services/hybrid_pipeline.py#L323-L426)

### Data Privacy Considerations and Lifecycle Management
- Candidate and ScreeningResult data are tenant-scoped; enforce tenant isolation in queries.
- parser_snapshot_json and raw_resume_text are retained; consider implementing retention policies and deletion endpoints.
- Usage logs track analysis counts per tenant; leverage for compliance and billing.
- **Updated**: Intelligent scoring weights metadata requires careful privacy consideration for sensitive role-based data.
- **Updated**: API response unification ensures consistent privacy considerations across all endpoints.
- **Updated**: Field-level merge strategy ensures critical analysis fields maintain integrity during narrative processing.
- **Updated**: Resume file storage introduces new privacy considerations for sensitive personal documents.
- Recommendations:
  - Add tenant-aware soft-delete and anonymization.
  - Implement data export/deletion APIs aligned with privacy regulations.
  - Add encryption-at-rest for sensitive fields if required.
  - Consider GDPR-compliant handling of AI-generated weight suggestions.
  - Monitor field-level merge operations for data integrity compliance.
  - Implement file access logging for audit trails.
  - Consider implementing file retention policies and automated cleanup.

**Updated** Enhanced privacy considerations for intelligent scoring weights metadata and AI-generated suggestions, with API response unification and field-level data integrity protection.

**Section sources**
- [db_models.py:79-93](file://app/backend/models/db_models.py#L79-L93)
- [candidates.py:26-80](file://app/backend/routes/candidates.py#L26-L80)

## Dependency Analysis
The following diagram shows key dependencies among modules involved in candidate management with enhanced API response unification and field-level data protection.

```mermaid
graph LR
PS["parser_service.py"] --> LCE["llm_contact_extractor.py"]
PS --> HP["hybrid_pipeline.py"]
LCE --> HP
WM["weight_mapper.py"] --> HP
WS["weight_suggester.py"] --> RA["routes/analyze.py"]
RA --> PS
RA --> GD["gap_detector.py"]
RA --> HP
RA --> DBM["models/db_models.py"]
RC["routes/candidates.py"] --> DBM
RE["routes/export.py"] --> DBM
RCM["routes/compare.py"] --> DBM
RU["routes/upload.py"] --> DBM
```

**Diagram sources**
- [analyze.py:32-39](file://app/backend/routes/analyze.py#L32-L39)
- [candidates.py:20-21](file://app/backend/routes/candidates.py#L20-L21)
- [export.py:14-15](file://app/backend/routes/export.py#L14-L15)
- [compare.py:9-11](file://app/backend/routes/compare.py#L9-L11)
- [db_models.py:97-150](file://app/backend/models/db_models.py#L97-L150)
- [llm_service.py:163-314](file://app/backend/services/llm_service.py#L163-L314)

**Section sources**
- [analyze.py:32-39](file://app/backend/routes/analyze.py#L32-L39)
- [candidates.py:20-21](file://app/backend/routes/candidates.py#L20-L21)
- [export.py:14-15](file://app/backend/routes/export.py#L14-L15)
- [compare.py:9-11](file://app/backend/routes/compare.py#L9-L11)

## Performance Considerations
- Deduplication reduces redundant parsing and analysis.
- JD caching (JdCache) avoids repeated JD parsing across workers.
- Asynchronous processing and thread pools prevent blocking during parsing.
- Snapshot storage enables fast re-analysis without re-parsing.
- Batch analysis enforces plan-based limits and parallel processing.
- **Updated**: LLM contact extraction uses optimized timeouts and fallback strategies for performance.
- **Updated**: Intelligent scoring weights system includes caching and normalization for efficient computation.
- **Updated**: API response unification optimizes data processing by ensuring consistent structures across all endpoints.
- **Updated**: Field-level merge strategy optimizes data processing by avoiding unnecessary field overwrites.
- **Updated**: JSON safety checks prevent performance degradation from malformed data.
- **Updated**: Resume file storage requires careful consideration of memory usage for large files.
- **Updated**: Chunked upload system optimizes network performance for large file transfers.

## Troubleshooting Guide
Common issues and resolutions:
- Scanned PDFs: Parsing raises a readable error; advise uploading text-based PDFs.
- Database locked: SQLite concurrency limitation; restart backend container.
- Ollama not responding: Check container logs and pull the model if needed.
- Exceeding usage limits: Monthly analysis or batch size limits enforced; upgrade plan.
- **Updated**: LLM contact extraction failures: Automatic fallback to regex/NLP methods; check model availability.
- **Updated**: Intelligent scoring weights conversion errors: Automatic fallback to default weights; verify input format.
- **Updated**: API response unification issues: Ensure analysis_result structure consistency across all endpoints.
- **Updated**: Field-level merge failures: Core analysis fields remain intact; check narrative data format; verify critical field preservation.
- **Updated**: JSON parsing errors: Malformed JSON automatically handled with safe fallbacks; check data integrity in analysis_result and parsed_data fields.
- **Updated**: Resume file storage issues: LargeBinary column may cause memory pressure; consider file size limits and cleanup policies.
- **Updated**: Chunked upload failures: Check chunk storage directory permissions and cleanup processes; verify MD5 hash integrity.
- **Updated**: Resume download errors: Ensure candidate has associated file data; verify tenant isolation and authentication.

**Section sources**
- [parser_service.py:175-181](file://app/backend/services/parser_service.py#L175-L181)
- [README.md:339-355](file://README.md#L339-L355)
- [analyze.py:364-370](file://app/backend/routes/analyze.py#L364-L370)
- [llm_contact_extractor.py:120-130](file://app/backend/services/llm_contact_extractor.py#L120-L130)
- [weight_mapper.py:212-246](file://app/backend/services/weight_mapper.py#L212-L246)
- [compare.py:42-47](file://app/backend/routes/compare.py#L42-L47)
- [upload.py:85-97](file://app/backend/routes/upload.py#L85-L97)

## Conclusion
The candidate management system integrates robust parsing, deduplication, intelligent scoring weights, and analysis workflows with durable storage and auditability. It supports efficient re-analysis, bulk operations, and export for downstream ATS use. The enhanced LLM contact extraction and intelligent scoring system provide superior accuracy and adaptability. The newly implemented API response unification ensures consistent data structures across all endpoints, using analysis_result as the authoritative data source. The enhanced field-level merge strategy ensures critical analysis fields like fit_score and final_recommendation maintain integrity while allowing selective narrative enhancements. The redesigned candidate comparison algorithm with comprehensive JSON safety checks provides robust comparison operations with priority-based data sources and multiple fallback mechanisms. Extensibility is provided through model additions, parser customization, skills registry updates, intelligent weight management, configurable field-level merge logic, and consistent API response structures. Privacy and lifecycle management should be considered for production deployments with enhanced attention to AI-generated metadata, data integrity protection, and unified API response structures. **Updated**: The system now includes comprehensive resume file storage and retrieval capabilities, enabling complete data portability and secure access to original uploaded files with tenant isolation and security measures.

## Appendices

### Endpoint Reference
- POST /api/analyze: Single resume analysis with dedup and profile storage.
- POST /api/analyze/stream: Streaming analysis with stage events.
- POST /api/analyze/batch: Batch analysis with plan limits.
- POST /api/analyze/suggest-weights: AI-powered weight suggestions for job descriptions.
- GET /api/history: Recent screening results.
- GET /api/candidates: Paginated and searchable candidate list.
- GET /api/candidates/{id}: Candidate detail with history and skills snapshot.
- POST /api/candidates/{id}/analyze-jd: Re-analyze existing candidate against a new JD.
- GET /api/export/csv: Export screening results to CSV.
- GET /api/export/excel: Export screening results to Excel.
- POST /api/compare: Compare up to 5 screening results with enhanced safety checks.
- **Updated**: GET /api/candidates/{candidate_id}/resume: Download or view original uploaded resume file.
- **Updated**: POST /api/upload/chunk: Upload resume file in chunks for large file handling.
- **Updated**: POST /api/upload/finalize: Finalize chunked upload and assemble complete file.

**Section sources**
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:651-758](file://app/backend/routes/analyze.py#L651-L758)
- [analyze.py:669-697](file://app/backend/routes/analyze.py#L669-L697)
- [candidates.py:26-189](file://app/backend/routes/candidates.py#L26-L189)
- [export.py:55-104](file://app/backend/routes/export.py#L55-L104)
- [compare.py:16-77](file://app/backend/routes/compare.py#L16-L77)
- [candidates.py:504-559](file://app/backend/routes/candidates.py#L504-L559)
- [upload.py:99-205](file://app/backend/routes/upload.py#L99-L205)
- [upload.py:207-324](file://app/backend/routes/upload.py#L207-L324)

### Intelligent Scoring Weights Schema
- **Legacy 4-weight**: skills, experience, stability, education
- **Old 7-weight**: skills, experience, architecture, education, timeline, domain, risk
- **New Universal 7-weight**: core_competencies, experience, domain_fit, education, career_trajectory, role_excellence, risk
- **Automatic Conversion**: Seamless conversion between all schema types
- **AI Suggestions**: Role-adaptive weight recommendations with confidence scores

**Section sources**
- [weight_mapper.py:20-360](file://app/backend/services/weight_mapper.py#L20-L360)
- [weight_suggester.py:86-307](file://app/backend/services/weight_suggester.py#L86-L307)
- [009_intelligent_scoring_weights.py:27-74](file://alembic/versions/009_intelligent_scoring_weights.py#L27-L74)

### Enhanced Candidate Comparison Algorithm Details
**JSON Safety and Reliability**:
- `_safe_loads()` function with comprehensive error handling for malformed JSON data
- Logging warnings for malformed JSON with result ID context
- Graceful fallback to empty dictionaries for corrupted JSON data
- Tenant-scoped filtering prevents unauthorized data access

**Priority-Based Data Sources**:
- Analysis data takes precedence over parsed data for accuracy
- Essential fields check determines data source priority
- Candidate table serves as final fallback for missing information
- Score breakdown defaults ensure consistent comparison metrics

**Enhanced Comparison Fields**:
- `employment_gaps`: Count of employment gaps from analysis
- `interview_questions_preview`: Technical questions preview (first 2 items)
- `analysis_quality`: Quality assessment of analysis (high/medium/low)
- `adjacent_skills`: Adjacent skills for role fit analysis
- `winners`: Category winners for overall, skills, experience, education, stability

**Winner Determination Logic**:
- Calculates maximum scores across all categories
- Marks candidates as winners when achieving maximum values
- Provides clear visual indicators in comparison interface
- Handles edge cases where multiple candidates tie for winners

**Updated** Enhanced with comprehensive JSON parsing safety checks, priority-based data source selection, and improved fallback mechanisms for robust candidate comparison operations with tenant isolation and error handling.

**Section sources**
- [compare.py:17-158](file://app/backend/routes/compare.py#L17-L158)
- [schemas.py:284-286](file://app/backend/models/schemas.py#L284-L286)

### Resume File Storage Implementation Details
**Database Schema**:
- resume_filename: String column (255 characters) storing original filename
- resume_file_data: LargeBinary column storing complete file bytes
- resume_file_hash: String column (64 characters) for MD5 file hash

**Storage Architecture**:
- Direct LargeBinary storage eliminates external file system dependencies
- Tenant isolation ensures data privacy and security
- Automatic deduplication via file hash comparison
- Efficient retrieval through dedicated API endpoint

**Security Measures**:
- Tenant-scoped queries prevent unauthorized access
- Authentication required for all file access operations
- MIME type validation prevents malicious file execution
- Content-Disposition headers control file download behavior

**API Integration**:
- Seamless integration with existing analysis workflow
- Optional file storage based on analysis requirements
- Backward compatibility with existing candidate records
- Efficient chunked upload system for large file handling

**Section sources**
- [db_models.py:112-116](file://app/backend/models/db_models.py#L112-L116)
- [candidates.py:504-559](file://app/backend/routes/candidates.py#L504-L559)
- [015_add_resume_file_storage.py:1-49](file://alembic/versions/015_add_resume_file_storage.py#L1-L49)