# Candidate Profile Storage

<cite>
**Referenced Files in This Document**
- [db_models.py](file://app/backend/models/db_models.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [candidates.py](file://app/backend/routes/candidates.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [gap_detector.py](file://app/backend/services/gap_detector.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)
- [002_parser_snapshot_json.py](file://alembic/versions/002_parser_snapshot_json.py)
- [database.py](file://app/backend/db/database.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced data reconstruction capabilities documentation to reflect comprehensive fallback mechanisms using parsed_data as backup source
- Updated systematic reconstruction of key fields like contact_info, candidate_profile, and work_experience
- Added improved error logging for data quality issues with detailed warning messages
- Updated parser snapshot JSON section to emphasize full parse output storage and reconstruction capabilities
- Enhanced three-layer candidate deduplication documentation with improved error handling

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Enhanced Data Persistence](#enhanced-data-persistence)
7. [Dependency Analysis](#dependency-analysis)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)

## Introduction
This document explains the candidate profile storage system in Resume AI. It covers the Candidate model structure, the end-to-end data persistence workflow from resume uploads through parsing to database storage, enriched profile fields, the parser snapshot JSON role, examples of profile updates and contact info merging, and data integrity and optimization strategies.

**Updated** Enhanced data reconstruction capabilities ensure complete candidate profile information is available even when analysis results are incomplete, with comprehensive fallback mechanisms and improved error logging for data quality issues.

## Project Structure
The candidate profile storage spans models, routes, services, and migrations:
- Models define the Candidate table and related entities.
- Routes orchestrate parsing, deduplication, and persistence with enhanced reconstruction capabilities.
- Services implement parsing, gap analysis, and hybrid scoring with fallback mechanisms.
- Migrations evolve the schema to support enriched profiles, snapshots, and reconstruction features.

```mermaid
graph TB
subgraph "Models"
A["db_models.py<br/>Candidate, ScreeningResult, JdCache, Skill"]
end
subgraph "Routes"
B["routes/analyze.py<br/>Single/Batch/Stream analysis with reconstruction"]
C["routes/candidates.py<br/>List/Get/Update with fallback mechanisms"]
end
subgraph "Services"
D["parser_service.py<br/>ResumeParser, parse_resume"]
E["gap_detector.py<br/>GapDetector.analyze"]
F["hybrid_pipeline.py<br/>run_hybrid_pipeline with fallback"]
end
subgraph "Migrations"
G["001_enrich_candidates_add_caches.py"]
H["002_parser_snapshot_json.py"]
end
subgraph "DB"
I["database.py<br/>Engine, Session"]
end
B --> D
B --> E
B --> F
B --> A
C --> A
C --> F
A --> I
G --> A
H --> A
```

**Diagram sources**
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [candidates.py:26-302](file://app/backend/routes/candidates.py#L26-L302)
- [parser_service.py:130-552](file://app/backend/services/parser_service.py#L130-L552)
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)
- [hybrid_pipeline.py:1-120](file://app/backend/services/hybrid_pipeline.py#L1-L120)
- [001_enrich_candidates_add_caches.py:42-121](file://alembic/versions/001_enrich_candidates_add_caches.py#L42-L121)
- [002_parser_snapshot_json.py:21-34](file://alembic/versions/002_parser_snapshot_json.py#L21-L34)
- [database.py:1-33](file://app/backend/db/database.py#L1-L33)

**Section sources**
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [candidates.py:26-302](file://app/backend/routes/candidates.py#L26-L302)
- [parser_service.py:130-552](file://app/backend/services/parser_service.py#L130-L552)
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)
- [hybrid_pipeline.py:1-120](file://app/backend/services/hybrid_pipeline.py#L1-L120)
- [001_enrich_candidates_add_caches.py:42-121](file://alembic/versions/001_enrich_candidates_add_caches.py#L42-L121)
- [002_parser_snapshot_json.py:21-34](file://alembic/versions/002_parser_snapshot_json.py#L21-L34)
- [database.py:1-33](file://app/backend/db/database.py#L1-L33)

## Core Components
- Candidate model: stores enriched profile fields and parser snapshot for reuse with reconstruction capabilities.
- Parser service: extracts text and structured data from resumes with fallback mechanisms.
- Gap detector: computes employment timeline, gaps, overlaps, and total experience.
- Hybrid pipeline: orchestrates Python rules and LLM scoring with comprehensive fallback handling.
- Routes: handle upload, deduplication, storage, re-analysis, and systematic data reconstruction.

Key enriched profile fields on Candidate:
- resume_file_hash: MD5 of file bytes for deduplication.
- raw_resume_text: capped text for downstream use.
- parsed_skills, parsed_education, parsed_work_exp: JSON arrays of structured data.
- gap_analysis_json: JSON object with timeline, gaps, overlaps, short stints, total_years.
- current_role, current_company, total_years_exp: denormalized quick-access fields.
- profile_quality: quality label for the stored profile.
- profile_updated_at: timestamp of last enrichment.
- parser_snapshot_json: full JSON of parse_resume output for audit/re-analysis and reconstruction.

**Section sources**
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)
- [001_enrich_candidates_add_caches.py:42-72](file://alembic/versions/001_enrich_candidates_add_caches.py#L42-L72)
- [002_parser_snapshot_json.py:21-28](file://alembic/versions/002_parser_snapshot_json.py#L21-L28)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)

## Architecture Overview
End-to-end flow from upload to persistent candidate profile with enhanced reconstruction capabilities:

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "routes/analyze.py"
participant Parser as "parser_service.py"
participant Gap as "gap_detector.py"
participant Hybrid as "hybrid_pipeline.py"
participant DB as "db_models.py/Candidate"
participant Cache as "JdCache"
Client->>Route : POST /api/analyze (resume, job)
Route->>Parser : parse_resume(file_bytes, filename)
Parser-->>Route : parsed_data (raw_text, skills, education, work_exp, contact_info)
Route->>Gap : analyze_gaps(work_experience)
Gap-->>Route : gap_analysis (timeline, gaps, overlaps, total_years)
Route->>Cache : _get_or_cache_jd(job_description)
Cache-->>Route : jd_analysis
Route->>Hybrid : run_hybrid_pipeline(...)
Hybrid-->>Route : result (scores, narrative, etc.)
Route->>DB : _get_or_create_candidate(...)
DB-->>Route : candidate_id
Route->>DB : persist ScreeningResult with fallback reconstruction
Route-->>Client : result + candidate_id
```

**Diagram sources**
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [parser_service.py:547-552](file://app/backend/services/parser_service.py#L547-L552)
- [gap_detector.py:217-219](file://app/backend/services/gap_detector.py#L217-L219)
- [hybrid_pipeline.py:1-120](file://app/backend/services/hybrid_pipeline.py#L1-L120)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

## Detailed Component Analysis

### Candidate Model and Schema
The Candidate entity stores both denormalized and normalized fields for efficient querying and re-analysis. The schema includes:
- Identity and tenant association.
- Contact info (name, email, phone).
- Enriched profile fields for reuse.
- Parser snapshot for auditability and reconstruction.
- Timestamps for freshness.

```mermaid
classDiagram
class Candidate {
+int id
+int tenant_id
+string name
+string email
+string phone
+datetime created_at
+string resume_file_hash
+string raw_resume_text
+string parsed_skills
+string parsed_education
+string parsed_work_exp
+string gap_analysis_json
+string current_role
+string current_company
+float total_years_exp
+string profile_quality
+datetime profile_updated_at
+string parser_snapshot_json
}
class ScreeningResult {
+int id
+int tenant_id
+int candidate_id
+string resume_text
+string jd_text
+string parsed_data
+string analysis_result
+string status
+datetime timestamp
}
class JdCache {
+string hash
+string result_json
+datetime created_at
}
class Skill {
+int id
+string name
+string aliases
+string domain
+string status
+string source
+int frequency
+datetime created_at
}
Candidate "1" --> "*" ScreeningResult : "has many"
Candidate "1" --> "*" TranscriptAnalysis : "has many"
Candidate "1" --> "*" Candidate : "tenant"
JdCache "1" --> "*" ScreeningResult : "used by"
Skill "1" --> "*" ScreeningResult : "referenced by"
```

**Diagram sources**
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)
- [db_models.py:128-146](file://app/backend/models/db_models.py#L128-L146)
- [db_models.py:229-236](file://app/backend/models/db_models.py#L229-L236)
- [db_models.py:238-250](file://app/backend/models/db_models.py#L238-L250)

**Section sources**
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

### Parser Snapshot JSON
The parser snapshot captures the complete output of parse_resume, including contact_info (which may include LinkedIn), raw_text, skills, education, work_experience. It is serialized to JSON and stored in parser_snapshot_json with a maximum byte size to bound row size.

- Purpose: Auditability and re-analysis independence from parsing heuristics.
- Fallback: If snapshot is missing, reconstructed from denormalized columns.
- Reconstruction: Systematic reconstruction of contact_info, candidate_profile, and work_experience from parsed_data backup source.

**Updated** Enhanced data reconstruction capabilities ensure that when analysis results are incomplete, the system can systematically reconstruct key fields using parsed_data as the backup source, providing comprehensive fallback mechanisms.

```mermaid
flowchart TD
Start(["Store Candidate Profile"]) --> CheckSnap["Has parser_snapshot_json?"]
CheckSnap --> |Yes| UseSnap["Use snapshot JSON"]
CheckSnap --> |No| Reconstruct["Reconstruct from denormalized columns"]
UseSnap --> CapText["Cap raw text length"]
Reconstruct --> CapText
CapText --> Store["Persist to Candidate row"]
Store --> End(["Done"])
```

**Diagram sources**
- [analyze.py:109-116](file://app/backend/routes/analyze.py#L109-L116)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)
- [candidates.py:228-266](file://app/backend/routes/candidates.py#L228-L266)

**Section sources**
- [analyze.py:109-116](file://app/backend/routes/analyze.py#L109-L116)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)
- [candidates.py:228-266](file://app/backend/routes/candidates.py#L228-L266)
- [002_parser_snapshot_json.py:21-28](file://alembic/versions/002_parser_snapshot_json.py#L21-L28)

### Data Persistence Workflow
- Deduplication: Three-layer matching by email, file hash, and name+phone.
- Enrichment: Gap analysis, skills registry, and hybrid scoring.
- Storage: Candidate row updated with enriched fields and snapshot; ScreeningResult persisted with comprehensive fallback mechanisms.

**Updated** Enhanced data persistence ensures complete candidate profile information is saved during analysis pipeline, preventing data loss during parsing stage with systematic reconstruction capabilities.

```mermaid
sequenceDiagram
participant Route as "routes/analyze.py"
participant Dedup as "_get_or_create_candidate"
participant Store as "_store_candidate_profile"
participant DB as "Candidate/ScreeningResult"
Route->>Dedup : parsed_data, tenant_id, file_hash, action
Dedup-->>Route : candidate_id, is_duplicate
alt update_profile
Route->>Store : update existing candidate
Store->>DB : write enriched fields + snapshot
else create_new
Route->>DB : create Candidate
Store->>DB : write enriched fields + snapshot
end
Route->>DB : persist ScreeningResult with fallback reconstruction
```

**Diagram sources**
- [analyze.py:147-214](file://app/backend/routes/analyze.py#L147-L214)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

**Section sources**
- [analyze.py:147-214](file://app/backend/routes/analyze.py#L147-L214)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)

### Enriched Profile Fields and Their Impact
- Denormalized fields enable fast queries and reduce repeated parsing costs.
- Gap analysis informs total_years_exp and highlights risks (overlaps, short stints).
- Skills registry improves coverage and consistency across resumes.
- Quality label (profile_quality) helps prioritize higher-quality profiles.
- Parser snapshot enables systematic reconstruction of incomplete analysis results.

**Section sources**
- [db_models.py:107-121](file://app/backend/models/db_models.py#L107-L121)
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)
- [hybrid_pipeline.py:323-427](file://app/backend/services/hybrid_pipeline.py#L323-L427)

### Re-analyzing Existing Candidates
The system supports re-analyzing an existing candidate against a new job description using the stored profile, skipping full parsing and relying on the snapshot or denormalized columns with enhanced reconstruction capabilities.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "routes/candidates.py"
participant Hybrid as "hybrid_pipeline.py"
participant DB as "Candidate/ScreeningResult"
Client->>Route : POST /api/candidates/{id}/analyze-jd
Route->>DB : load candidate (snapshot or denormalized)
Route->>Hybrid : run_hybrid_pipeline(parsed_data, gap_analysis)
Hybrid-->>Route : result with reconstruction fallback
Route->>DB : persist ScreeningResult with enhanced error handling
Route-->>Client : result
```

**Diagram sources**
- [candidates.py:192-302](file://app/backend/routes/candidates.py#L192-L302)
- [hybrid_pipeline.py:1-120](file://app/backend/services/hybrid_pipeline.py#L1-L120)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

**Section sources**
- [candidates.py:192-302](file://app/backend/routes/candidates.py#L192-L302)

### Contact Info Merging and Validation
- Contact info precedence: snapshot contact_info merged with candidate's edited name/email/phone.
- Validation: minimal checks on JD length and file sizes; deduplication ensures uniqueness.
- Deduplication layers: email, file hash, name+phone.
- Reconstruction: systematic fallback using parsed_data when snapshot is missing.

**Updated** Enhanced data reconstruction ensures contact information merging occurs during the analysis pipeline with systematic fallback mechanisms using parsed_data as backup source.

```mermaid
flowchart TD
A["Contact Info Source"] --> B{"From snapshot?"}
B --> |Yes| C["Use snapshot contact_info"]
B --> |No| D["Use denormalized columns"]
C --> E{"Candidate edited fields?"}
D --> E
E --> |Yes| F["Override with candidate fields"]
E --> |No| G["Keep snapshot fields"]
F --> H["Final contact_info"]
G --> H
```

**Diagram sources**
- [candidates.py:150-171](file://app/backend/routes/candidates.py#L150-L171)
- [candidates.py:228-266](file://app/backend/routes/candidates.py#L228-L266)

**Section sources**
- [candidates.py:150-171](file://app/backend/routes/candidates.py#L150-L171)
- [candidates.py:228-266](file://app/backend/routes/candidates.py#L228-L266)
- [analyze.py:147-214](file://app/backend/routes/analyze.py#L147-L214)

### Parser Snapshot JSON Structure
The snapshot JSON mirrors the output of parse_resume:
- raw_text: extracted text.
- skills: list of identified skills.
- education: list of educational entries.
- work_experience: list of job entries.
- contact_info: dictionary with name, email, phone, and optional LinkedIn.

Constraints:
- Maximum serialized size enforced to prevent oversized rows.
- Stored as Text to accommodate large JSON.
- Reconstruction fallback enabled through systematic field restoration.

**Section sources**
- [parser_service.py:547-552](file://app/backend/services/parser_service.py#L547-L552)
- [analyze.py:109-116](file://app/backend/routes/analyze.py#L109-L116)
- [002_parser_snapshot_json.py:21-28](file://alembic/versions/002_parser_snapshot_json.py#L21-L28)

## Enhanced Data Persistence

### Three-Layer Candidate Deduplication
The system implements a robust three-layer deduplication strategy to ensure candidate profiles are not duplicated unnecessarily:

1. **Email Match**: Primary deduplication using email address
2. **File Hash Match**: Secondary deduplication using MD5 hash of resume file bytes
3. **Name + Phone Match**: Tertiary deduplication using combination of name and phone number

**Updated** Enhanced data persistence ensures that during the deduplication process, complete candidate profile information is saved immediately to prevent data loss during parsing stage with comprehensive reconstruction capabilities.

```mermaid
flowchart TD
Start(["Candidate Analysis"]) --> Action{"Action Type"}
Action --> |None/unrecognized| EmailMatch["Layer 1: Email Match"]
Action --> |use_existing| UseExisting["Load Stored Profile"]
Action --> |update_profile| UpdateProfile["Update Existing Profile"]
Action --> |create_new| CreateNew["Create New Candidate"]
EmailMatch --> EmailFound{"Email Found?"}
EmailFound --> |Yes| ReturnExisting["Return Existing Candidate"]
EmailFound --> |No| HashMatch["Layer 2: File Hash Match"]
HashMatch --> HashFound{"File Hash Found?"}
HashFound --> |Yes| ReturnExisting
HashFound --> |No| NamePhoneMatch["Layer 3: Name + Phone Match"]
NamePhoneMatch --> NamePhoneFound{"Name + Phone Found?"}
NamePhoneFound --> |Yes| ReturnExisting
NamePhoneFound --> |No| CreateNew
UseExisting --> LoadProfile["Load Stored Profile"]
UpdateProfile --> SaveProfile["Save Updated Profile"]
CreateNew --> SaveNew["Create New Candidate"]
```

**Diagram sources**
- [analyze.py:182-241](file://app/backend/routes/analyze.py#L182-L241)

### Comprehensive Fallback Mechanisms and Data Reconstruction
The enhanced data persistence includes comprehensive fallback mechanisms to ensure data integrity:

- **Parsed Data Backup**: parsed_data serves as the primary backup source for reconstruction
- **Systematic Field Restoration**: contact_info, candidate_profile, and work_experience are systematically reconstructed
- **Enhanced Error Logging**: Detailed warning messages for data quality issues with specific field identification
- **Reconstruction Logic**: When analysis_result is empty or missing critical fields, systematic fallback occurs

**Updated** Enhanced error handling ensures that even if parsing fails or database operations encounter issues, candidate profile information is still persisted to prevent data loss during the analysis pipeline through comprehensive fallback mechanisms.

```mermaid
flowchart TD
ParseStart["Resume Parse Attempt"] --> ParseSuccess{"Parse Success?"}
ParseSuccess --> |Yes| ContinueAnalysis["Continue Analysis"]
ParseSuccess --> |No| FallbackData["Create Fallback Parsed Data"]
FallbackData --> ContinueAnalysis
ContinueAnalysis --> CreateCandidate["Create/Update Candidate"]
CreateCandidate --> SaveToDB["Save to Database"]
SaveToDB --> DBSuccess{"DB Save Success?"}
DBSuccess --> |Yes| CompleteAnalysis["Complete Analysis"]
DBSuccess --> |No| RetryMechanism["Retry Mechanism"]
RetryMechanism --> SnapshotFallback["Use Snapshot Fallback"]
SnapshotFallback --> CompleteAnalysis
CompleteAnalysis --> StreamSSE["Stream SSE Results"]
StreamSSE --> EarlyDBSave["Early DB Save During Streaming"]
EarlyDBSave --> FinalDBSave["Final DB Save"]
FinalDBSave --> AnalysisComplete["Analysis Complete"]
```

**Diagram sources**
- [analyze.py:567-588](file://app/backend/routes/analyze.py#L567-L588)
- [analyze.py:832-876](file://app/backend/routes/analyze.py#L832-L876)

### Enhanced Streaming Capabilities
The system now includes improved streaming capabilities with early database saves to prevent data loss:

- **Early DB Saves**: Candidate profiles are saved immediately after parsing phase
- **Progressive Updates**: Analysis results are progressively updated in the database
- **Resilient Streaming**: Even if client disconnects, partial results are preserved
- **Reconstruction Fallback**: Systematic fallback mechanisms ensure complete data availability

**Updated** Enhanced streaming capabilities ensure that candidate profile information is persisted immediately after the parsing phase, preventing data loss during SSE streaming when clients may disconnect, with comprehensive reconstruction fallback mechanisms.

**Section sources**
- [analyze.py:567-588](file://app/backend/routes/analyze.py#L567-L588)
- [analyze.py:832-876](file://app/backend/routes/analyze.py#L832-L876)

## Dependency Analysis
- Routes depend on parser_service, gap_detector, and hybrid_pipeline with enhanced fallback capabilities.
- Candidate enrichment depends on gap_detector and skills registry.
- Persistence depends on SQLAlchemy models and Alembic migrations.
- Reconstruction logic depends on systematic fallback mechanisms and error logging.

```mermaid
graph LR
Parser["parser_service.py"] --> Routes["routes/analyze.py"]
Gap["gap_detector.py"] --> Routes
Hybrid["hybrid_pipeline.py"] --> Routes
Routes --> Models["db_models.py"]
Models --> DB["database.py"]
M1["001_enrich_candidates_add_caches.py"] --> Models
M2["002_parser_snapshot_json.py"] --> Models
```

**Diagram sources**
- [analyze.py:32-39](file://app/backend/routes/analyze.py#L32-L39)
- [parser_service.py:130-552](file://app/backend/services/parser_service.py#L130-L552)
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)
- [hybrid_pipeline.py:1-120](file://app/backend/services/hybrid_pipeline.py#L1-L120)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)
- [database.py:1-33](file://app/backend/db/database.py#L1-L33)
- [001_enrich_candidates_add_caches.py:42-121](file://alembic/versions/001_enrich_candidates_add_caches.py#L42-L121)
- [002_parser_snapshot_json.py:21-28](file://alembic/versions/002_parser_snapshot_json.py#L21-L28)

**Section sources**
- [analyze.py:32-39](file://app/backend/routes/analyze.py#L32-L39)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

## Performance Considerations
- Thread pool parsing: resume parsing offloads to threads to avoid blocking the event loop.
- JD caching: shared cache across workers reduces repeated JD parsing.
- Snapshot size cap: bounds row size and memory footprint.
- Index on resume_file_hash: accelerates deduplication by file hash.
- Asynchronous streaming: SSE endpoints stream intermediate results for responsiveness.
- **Enhanced persistence**: Immediate saving of candidate profiles prevents data loss and reduces recovery complexity.
- **Reconstruction efficiency**: Systematic fallback mechanisms minimize computational overhead for incomplete results.

**Updated** Enhanced persistence mechanisms improve system reliability by ensuring candidate profile information is saved immediately during the analysis pipeline, reducing the risk of data loss during parsing failures or system interruptions. The systematic reconstruction capabilities provide efficient fallback mechanisms that minimize computational overhead while ensuring data integrity.

## Troubleshooting Guide
Common issues and remedies:
- Scanned PDFs: Parsing raises a clear error; advise uploading text-based PDFs.
- Too-short JD: Rejected with a helpful message; require at least 80 words.
- Excessive resume size: Rejected at 10 MB; compress or optimize.
- Excessive JD file size: Rejected at 5 MB; prefer text-based files.
- Deduplication not matching: Verify email, file hash, and name+phone combinations; consider update_profile action.
- **Enhanced persistence failures**: If candidate profiles fail to save, check database connectivity and retry mechanism; system automatically falls back to snapshot reconstruction with detailed error logging.
- **Incomplete analysis results**: System automatically reconstructs missing fields using parsed_data backup source with comprehensive fallback mechanisms.

**Updated** Enhanced troubleshooting guidance now includes specific steps for handling persistence failures and data loss scenarios during the analysis pipeline, with detailed information about systematic reconstruction capabilities and enhanced error logging for data quality issues.

**Section sources**
- [analyze.py:268-290](file://app/backend/routes/analyze.py#L268-L290)
- [analyze.py:255-265](file://app/backend/routes/analyze.py#L255-L265)
- [analyze.py:369-374](file://app/backend/routes/analyze.py#L369-L374)
- [analyze.py:376-381](file://app/backend/routes/analyze.py#L376-L381)

## Conclusion
The candidate profile storage system in Resume AI combines robust parsing, gap analysis, and hybrid scoring with a durable schema that persists enriched profiles and a full parser snapshot. This enables fast re-analysis, auditability, and consistent candidate evaluation across job descriptions while maintaining data integrity and performance.

**Updated** The enhanced data reconstruction capabilities ensure complete candidate profile information is available even when analysis results are incomplete, with comprehensive fallback mechanisms using parsed_data as backup source. The systematic reconstruction of key fields like contact_info, candidate_profile, and work_experience, combined with improved error logging for data quality issues, makes the system more robust and suitable for production environments where data integrity is critical. These enhancements provide reliable fallback mechanisms that ensure candidate analysis results remain accessible and complete even under challenging circumstances.