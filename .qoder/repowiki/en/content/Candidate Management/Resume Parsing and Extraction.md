# Resume Parsing and Extraction

<cite>
**Referenced Files in This Document**
- [parser_service.py](file://app/backend/services/parser_service.py)
- [llm_contact_extractor.py](file://app/backend/services/llm_contact_extractor.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [candidates.py](file://app/backend/routes/candidates.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [test_parser_service.py](file://app/backend/tests/test_parser_service.py)
- [002_parser_snapshot_json.py](file://alembic/versions/002_parser_snapshot_json.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced name extraction algorithms with comprehensive skip_phrases validation for job titles and professional roles
- Improved phone number detection logic with multi-pattern approach and year validation to prevent false positives
- Expanded SKIP_WORDS collection for better resume section header recognition and filtering
- Refined contact information extraction with stricter validation rules and enhanced pattern matching
- Strengthened name validation logic with comprehensive skip_phrases collection covering 40+ professional domains

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
This document explains the resume parsing and extraction workflows powering the system. It covers the parser service architecture supporting PDF and DOCX formats, text extraction algorithms, and structured data parsing for contact information, work experience, education, and skills. The system now features enhanced contact extraction accuracy through integrated LLM-based extraction using the Gemma model, providing superior accuracy for international names, creative layouts, and edge cases. It also documents the parsing pipeline stages, error handling for malformed documents and scanned PDFs, fallback mechanisms, parser snapshot generation, and JSON serialization format. Practical examples, edge-case handling, and performance optimization strategies are included, along with configuration and customization possibilities.

**Updated** Enhanced with integrated LLM-based contact extraction using Gemma model for superior accuracy and refined extraction strategies with improved validation logic.

## Project Structure
The resume parsing pipeline spans several modules:
- Parser service: extracts raw text from resumes and parses structured fields with enhanced LLM integration.
- LLM contact extractor: specialized module for LLM-based contact information extraction.
- Hybrid pipeline: augments parsed profiles with skills discovery and scoring.
- Routes: orchestrate parsing, caching, deduplication, and persistence.
- Models: define database schema and Pydantic output models.
- Tests: validate parsing behavior and edge cases including LLM integration.

```mermaid
graph TB
subgraph "Routes"
A["analyze.py<br/>POST /api/analyze"]
B["candidates.py<br/>GET /api/candidates/{id}"]
end
subgraph "Services"
C["parser_service.py<br/>parse_resume, ResumeParser<br/>enrich_parsed_resume_async"]
D["llm_contact_extractor.py<br/>extract_contact_with_llm<br/>merge_contact_info"]
E["hybrid_pipeline.py<br/>run_hybrid_pipeline, skills registry"]
end
subgraph "Models"
F["db_models.py<br/>Candidate, ScreeningResult"]
G["schemas.py<br/>AnalysisResponse, models"]
end
A --> C
A --> D
A --> E
B --> F
C --> D
C --> F
D --> F
E --> F
A --> G
B --> G
```

**Diagram sources**
- [analyze.py:1-40](file://app/backend/routes/analyze.py#L1-L40)
- [candidates.py:1-30](file://app/backend/routes/candidates.py#L1-L30)
- [parser_service.py:1-50](file://app/backend/services/parser_service.py#L1-L50)
- [llm_contact_extractor.py:1-25](file://app/backend/services/llm_contact_extractor.py#L1-L25)
- [hybrid_pipeline.py:1-40](file://app/backend/services/hybrid_pipeline.py#L1-L40)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)
- [schemas.py:89-125](file://app/backend/models/schemas.py#L89-L125)

**Section sources**
- [analyze.py:1-80](file://app/backend/routes/analyze.py#L1-L80)
- [parser_service.py:1-50](file://app/backend/services/parser_service.py#L1-L50)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

## Core Components
- ResumeParser: central class extracting raw text from PDF/DOCX/TXT and structuring contact info, work experience, education, and skills.
- parse_resume: convenience function instantiating ResumeParser and returning structured output with enhanced name enrichment.
- enrich_parsed_resume: fills missing name using a four-tier fallback system (NER detection, email-based extraction, relaxed header scanning, filename-based extraction).
- enrich_parsed_resume_async: async version that integrates LLM-based contact extraction as the primary enhancement strategy.
- LLM contact extractor: specialized module using Gemma model for accurate contact information extraction from resume headers.
- merge_contact_info: intelligent merging strategy that leverages LLM strengths while preserving regex accuracy for standard formats.
- Hybrid pipeline: enhances parsed data with skills discovery and scoring.
- Routes: orchestrate parsing, deduplication, caching, and persistence.

Key responsibilities:
- Text extraction: PDF via PyMuPDF with pdfplumber fallback; DOCX via python-docx; TXT via decoding.
- Structured parsing: work experience, skills, education, contact info.
- Enhanced contact extraction: LLM-based extraction with JSON parsing, validation, and intelligent merging strategy.
- Enhanced name extraction: robust four-tier fallback system for maximum accuracy with comprehensive validation.
- Snapshot storage: full parser output serialized to JSON for auditing and re-analysis.
- Error handling: scanned PDF detection, unsupported formats, and graceful fallbacks.

**Updated** Enhanced contact extraction with integrated LLM-based extraction using Gemma model for superior accuracy and refined extraction strategies with improved validation logic.

**Section sources**
- [parser_service.py:130-202](file://app/backend/services/parser_service.py#L130-L202)
- [parser_service.py:583-610](file://app/backend/services/parser_service.py#L583-L610)
- [parser_service.py:612-653](file://app/backend/services/parser_service.py#L612-L653)
- [parser_service.py:1080-1126](file://app/backend/services/parser_service.py#L1080-L1126)
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)
- [hybrid_pipeline.py:604-637](file://app/backend/services/hybrid_pipeline.py#L604-L637)
- [analyze.py:109-145](file://app/backend/routes/analyze.py#L109-L145)

## Architecture Overview
End-to-end flow from upload to analysis and persistence with enhanced LLM integration:

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "analyze.py"
participant Parser as "parser_service.py"
participant LLM as "llm_contact_extractor.py"
participant Gap as "gap_detector.py"
participant Hybrid as "hybrid_pipeline.py"
participant DB as "db_models.py"
Client->>Route : "Upload resume + optional JD"
Route->>Route : "Validate file size/type"
Route->>Parser : "parse_resume(file_bytes, filename)"
Parser-->>Route : "parsed_data"
Route->>LLM : "extract_contact_with_llm(raw_text, timeout=8.0)"
LLM-->>Route : "llm_contact (if available)"
Route->>Parser : "merge_contact_info(contact, llm_contact)"
Parser-->>Route : "enriched parsed_data"
Route->>Gap : "analyze_gaps(parsed_data.work_experience)"
Gap-->>Route : "gap_analysis"
Route->>Hybrid : "run_hybrid_pipeline(resume_text, job_description, parsed_data, gap_analysis)"
Hybrid-->>Route : "analysis_result"
Route->>DB : "_store_candidate_profile(...), persist ScreeningResult"
Route-->>Client : "AnalysisResponse"
```

**Diagram sources**
- [analyze.py:354-400](file://app/backend/routes/analyze.py#L354-L400)
- [parser_service.py:656-662](file://app/backend/services/parser_service.py#L656-L662)
- [parser_service.py:1080-1126](file://app/backend/services/parser_service.py#L1080-L1126)
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)
- [hybrid_pipeline.py:604-637](file://app/backend/services/hybrid_pipeline.py#L604-L637)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)
- [db_models.py:128-146](file://app/backend/models/db_models.py#L128-L146)

## Detailed Component Analysis

### Enhanced Contact Extraction Pipeline
The system now features a sophisticated contact extraction pipeline that combines multiple strategies for maximum accuracy:

**Primary LLM-Based Extraction (Enhanced Accuracy)**
- Uses Gemma model via Ollama for superior accuracy with international names, creative layouts, and edge cases.
- Extracts contact information from the first 1000 characters of resume header to optimize token usage.
- Implements JSON parsing with validation and cleanup of null values.
- Handles markdown code block wrapping and provides graceful fallbacks.

**Intelligent Merging Strategy**
- Prefers LLM results for names (more accurate with edge cases).
- Prefers regex results for emails/phones (faster, equally accurate for standard formats).
- Uses LLM as fallback when regex misses fields.
- Ensures complete contact information even when individual extraction methods fail.

**Enhanced Phone Number Detection Logic**
- Multi-pattern approach with three distinct phone number patterns:
  - International format: +1-555-123-4567, +91 98765 43210
  - Parentheses format: (555) 123-4567, (555)123-4567
  - Standard format: 555-123-4567, 555.123.4567, 555 123 4567
- Strict validation to prevent year matching: must have at least 7 digits and not be a year (1900-2099)
- Comprehensive digit extraction and validation before accepting phone numbers

**Fallback Tier System**
- Tier 0: LLM-based extraction (most accurate, handles all edge cases).
- Tier 1: spaCy NER detection (most accurate for diverse formats).
- Tier 2: Email-based extraction (handles cases where header parsing fails).
- Tier 3: Relaxed header scanning (accommodates varied resume layouts).
- Tier 4: Filename-based extraction (final fallback for edge cases).

```mermaid
flowchart TD
Start(["Contact Extraction Request"]) --> CheckComplete{"Complete contact info?"}
CheckComplete --> |Yes| Return["Return existing data"]
CheckComplete --> |No| LLM["LLM-based Extraction (Gemma)"]
LLM --> LLMResult{"LLM result?"}
LLMResult --> |Yes| Merge["Merge with regex results"]
LLMResult --> |No| Tier0["Tier 0: spaCy NER Detection"]
Tier0 --> HasNER{"NER result?"}
HasNER --> |Yes| UseNER["Use NER result"]
HasNER --> |No| Tier1["Tier 1: Email-Based Extraction"]
Tier1 --> HasEmail{"Email available?"}
HasEmail --> |Yes| UseEmail["Extract from email"]
HasEmail --> |No| Tier2["Tier 2: Relaxed Header Scan"]
Tier2 --> HasRelaxed{"Relaxed result?"}
HasRelaxed --> |Yes| UseRelaxed["Use relaxed result"]
HasRelaxed --> |No| Tier3["Tier 3: Filename-Based Extraction"]
Tier3 --> HasFilename{"Filename available?"}
HasFilename --> |Yes| UseFilename["Extract from filename"]
HasFilename --> |No| Fail["No contact info found"]
UseNER --> Success["Set contact info"]
UseEmail --> Success
UseRelaxed --> Success
UseFilename --> Success
Merge --> Success
Fail --> Success
Success --> End(["Contact enrichment complete"])
```

**Diagram sources**
- [parser_service.py:1080-1126](file://app/backend/services/parser_service.py#L1080-L1126)
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)

**Section sources**
- [parser_service.py:1014-1037](file://app/backend/services/parser_service.py#L1014-L1037)
- [parser_service.py:1080-1126](file://app/backend/services/parser_service.py#L1080-L1126)
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)

### ResumeParser: Text Extraction and Structured Parsing
- Supported formats: PDF, DOCX, DOC, TXT, RTF, HTML/HTM, ODT, and plain text fallback.
- PDF extraction:
  - Primary: PyMuPDF for robust text extraction and correct reading order.
  - Fallback: pdfplumber if PyMuPDF is unavailable or yields empty text.
  - Guard: raises a clear error for scanned PDFs (text length < 100 characters).
  - Normalization: optional Unicode normalization for accented characters.
- DOCX extraction: reads paragraph text and table cells.
- Structured parsing:
  - Work experience: detects date patterns and infers company/title from surrounding lines; accumulates descriptions.
  - Skills: section-based extraction with broad fallback using a skills registry and regex scanning.
  - Education: identifies degree-related lines and extracts university/year.
  - Contact info: name, email, phone, LinkedIn; enhanced extraction with LLM integration and improved validation.

```mermaid
classDiagram
class ResumeParser {
+extract_text(file_bytes, filename) str
+parse_resume(file_bytes, filename) dict
+_extract_pdf(file_bytes) str
+_extract_docx(file_bytes) str
+_extract_work_experience(text) list
+_extract_skills(text) list
+_extract_education(text) list
+_extract_name(text) str
+_extract_contact_info(text) dict
+enrich_parsed_resume_async(data, filename) None
+enrich_parsed_resume(data, filename) None
}
class LLMContactExtractor {
+extract_contact_with_llm(resume_text, timeout) Dict[str, str]
+merge_contact_info(regex_result, llm_result) Dict[str, str]
}
class ParserUtils {
+_extract_name_ner(raw_text) str
+_extract_name_relaxed(text) str
+_name_from_email(email) str
+_name_from_filename(filename) str
}
ResumeParser --> LLMContactExtractor : "uses"
ResumeParser --> ParserUtils : "uses"
```

**Diagram sources**
- [parser_service.py:176-662](file://app/backend/services/parser_service.py#L176-L662)
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)

**Section sources**
- [parser_service.py:188-196](file://app/backend/services/parser_service.py#L188-L196)
- [parser_service.py:198-236](file://app/backend/services/parser_service.py#L198-L236)
- [parser_service.py:238-241](file://app/backend/services/parser_service.py#L238-L241)
- [parser_service.py:242-251](file://app/backend/services/parser_service.py#L242-L251)
- [parser_service.py:253-331](file://app/backend/services/parser_service.py#L253-L331)
- [parser_service.py:368-421](file://app/backend/services/parser_service.py#L368-L421)
- [parser_service.py:423-467](file://app/backend/services/parser_service.py#L423-L467)
- [parser_service.py:469-540](file://app/backend/services/parser_service.py#L469-L540)

### Enhanced Name Extraction and Enrichment System
The system now implements a robust four-tier fallback mechanism for name extraction with LLM integration and comprehensive validation:

**Tier 0: LLM-Based Extraction (New - Most Accurate)**
- Uses Gemma model via Ollama for superior accuracy with international names, creative layouts, and edge cases.
- Extracts names from the first 1000 characters of resume header.
- Provides JSON parsing with validation and cleanup of null values.
- Handles markdown code block wrapping and graceful fallbacks.

**Tier 1: spaCy NER Detection (Most Accurate)**
- Uses spaCy's Named Entity Recognition to identify PERSON entities in the first 50 lines of resume text.
- Validates results to ensure 1-5 words, no digits, and reasonable length (< 60 characters).
- Gracefully handles spaCy unavailability by falling back to next tier.

**Tier 2: Email-Based Extraction**
- Extracts name from email local part (before @) when available.
- Splits on common separators (., _, +, -) and capitalizes tokens.
- Requires at least 2 alphabetic tokens for validation.

**Tier 3: Relaxed Header Scanning**
- Searches first 35 lines for title-case name patterns.
- Skips common section headers and contact information lines.
- Validates against skip lists and contact indicators.

**Tier 4: Filename-Based Extraction (New)**
- Extracts name from filename when all other tiers fail.
- Handles various naming conventions: "john_doe_resume_2024.pdf", "Suhas Mullangi.pdf".
- Removes common prefixes (resume, cv, curriculum, vitae), dates, and non-name patterns.
- Validates resulting name has 2-5 words and no digits.

**Enhanced Name Validation Logic**
- Comprehensive SKIP_WORDS collection expanded to 20+ section headers and common resume elements
- Advanced skip_phrases validation covering 40+ professional domains and job titles
- Multi-segment validation for pipe-separated header lines (Name | phone | city)
- Job title pattern detection to prevent matching professional roles as names
- Title case validation with flexible word counting for international names

```mermaid
flowchart TD
Start(["Name Extraction Request"]) --> CheckContact{"Contact name exists?"}
CheckContact --> |Yes| Return["Return existing name"]
CheckContact --> |No| LLM["Tier 0: LLM-Based Extraction"]
LLM --> HasLLM{"LLM result?"}
HasLLM --> |Yes| UseLLM["Use LLM result"]
HasLLM --> |No| Tier1["Tier 1: spaCy NER Detection"]
Tier1 --> HasNER{"NER result?"}
HasNER --> |Yes| UseNER["Use NER result"]
HasNER --> |No| Tier2["Tier 2: Email-Based Extraction"]
Tier2 --> HasEmail{"Email available?"}
HasEmail --> |Yes| UseEmail["Extract from email"]
HasEmail --> |No| Tier3["Tier 3: Relaxed Header Scan"]
Tier3 --> HasRelaxed{"Relaxed result?"}
HasRelaxed --> |Yes| UseRelaxed["Use relaxed result"]
HasRelaxed --> |No| Tier4["Tier 4: Filename-Based Extraction"]
Tier4 --> HasFilename{"Filename available?"}
HasFilename --> |Yes| UseFilename["Extract from filename"]
HasFilename --> |No| Fail["No name found"]
UseLLM --> Success["Set contact name"]
UseNER --> Success
UseEmail --> Success
UseRelaxed --> Success
UseFilename --> Success
Fail --> Success
Success --> End(["Name enrichment complete"])
```

**Diagram sources**
- [parser_service.py:1080-1126](file://app/backend/services/parser_service.py#L1080-L1126)
- [parser_service.py:583-610](file://app/backend/services/parser_service.py#L583-L610)
- [parser_service.py:612-653](file://app/backend/services/parser_service.py#L612-L653)

**Section sources**
- [parser_service.py:42-63](file://app/backend/services/parser_service.py#L42-L63)
- [parser_service.py:543-553](file://app/backend/services/parser_service.py#L543-L553)
- [parser_service.py:556-580](file://app/backend/services/parser_service.py#L556-L580)
- [parser_service.py:583-610](file://app/backend/services/parser_service.py#L583-L610)
- [parser_service.py:612-653](file://app/backend/services/parser_service.py#L612-L653)

### Enhanced Name Extraction Algorithm Details
The name extraction algorithm now features comprehensive validation logic:

**Skip Words Collection Expansion**
- Extended from basic section headers to 20+ comprehensive terms
- Covers resume sections: experience, education, skills, employment, projects, references
- Includes professional terms: profile, summary, objective, certifications, awards
- Adds personal information: address, contact, details, information, interests

**Advanced Skip Phrases Validation**
- Comprehensive collection of 40+ professional domains and job titles
- Covers software development: software engineer, software engineering, full stack
- Includes data science: data scientist, machine learning, deep learning
- Professional roles: project manager, product manager, scrum master, agile coach
- Technical positions: devops engineer, systems engineer, cloud architect
- Management levels: vice president, director of, head of, lead of
- Engineering management: engineering manager, technical lead, team lead

**Multi-Segment Header Processing**
- Split on pipe (|), bullet (•), and space separators
- Process each segment independently with validation
- Handle mixed content: Name | phone | city | email
- Skip email addresses, LinkedIn URLs, and excessive digits
- Apply job title pattern detection to professional roles

**Enhanced Validation Rules**
- Individual word validation against SKIP_WORDS collection
- Complete phrase validation against skip_phrases collection
- Job title pattern detection preventing role names as candidates
- Title case validation with flexible word counting
- Digit count validation (maximum 2 digits per segment)
- Length constraints (minimum 2, maximum 5 words per segment)

**Section sources**
- [parser_service.py:966-1037](file://app/backend/services/parser_service.py#L966-L1037)
- [parser_service.py:996-1008](file://app/backend/services/parser_service.py#L996-L1008)
- [parser_service.py:1023-1032](file://app/backend/services/parser_service.py#L1023-L1032)

### LLM Contact Extraction Module
The LLM contact extractor provides sophisticated contact information extraction using the Gemma model:

**LLM Extraction Features**
- Model: Gemma 4:31b-cloud via Ollama
- Prompt Engineering: System prompt and user prompt with strict JSON output requirements
- Timeout Handling: Configurable timeout (default 8.0 seconds) with graceful fallbacks
- JSON Parsing: Robust parsing with markdown code block handling
- Validation: Structure validation and null value cleanup
- Authentication: Uses Ollama Cloud authentication helper

**Extraction Strategy**
- Focuses on resume header (first 1000 characters) to optimize token usage
- Extracts name, email, phone, and LinkedIn in a single JSON response
- Handles international names, creative layouts, and edge cases
- Provides fallback to regex extraction when LLM fails

```mermaid
flowchart TD
Start(["LLM Contact Extraction"]) --> Header["Extract first 1000 chars"]
Header --> Prompt["Generate system + user prompts"]
Prompt --> Call["Call Ollama API"]
Call --> Response{"Valid JSON response?"}
Response --> |Yes| Parse["Parse JSON response"]
Response --> |No| Fallback["Fallback to regex extraction"]
Parse --> Validate["Validate structure & clean nulls"]
Validate --> Success["Return contact info"]
Fallback --> Success
Success --> End(["Extraction Complete"])
```

**Diagram sources**
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)

**Section sources**
- [llm_contact_extractor.py:23-164](file://app/backend/services/llm_contact_extractor.py#L23-L164)

### Skills Discovery and Registry
Skills extraction combines:
- Section-based extraction from a skills header region.
- Full-text scanning using a skills registry and optional keyword extraction processor.
- Fallback to a broad skills list when processors are unavailable.

```mermaid
flowchart TD
Start(["Start skills extraction"]) --> FindSection["Find skills section"]
FindSection --> Found{"Section found?"}
Found --> |Yes| Split["Split by delimiters"]
Found --> |No| ScanText["Scan full text with skills registry"]
Split --> Merge["Merge and deduplicate"]
ScanText --> Merge
Merge --> End(["Return skills list"])
```

**Diagram sources**
- [parser_service.py:368-421](file://app/backend/services/parser_service.py#L368-L421)
- [hybrid_pipeline.py:589-637](file://app/backend/services/hybrid_pipeline.py#L589-L637)

**Section sources**
- [parser_service.py:368-421](file://app/backend/services/parser_service.py#L368-L421)
- [hybrid_pipeline.py:69-182](file://app/backend/services/hybrid_pipeline.py#L69-L182)
- [hybrid_pipeline.py:589-637](file://app/backend/services/hybrid_pipeline.py#L589-L637)

### Parser Snapshot Generation and JSON Serialization
- Full parser output is serialized to JSON and stored in the Candidate row for auditing and re-analysis.
- Limits: maximum serialized size enforced to keep rows bounded.
- Restoration: routes reconstruct parsed data from snapshot or denormalized columns.

```mermaid
flowchart TD
Parsed["parsed_data from ResumeParser"] --> Serialize["JSON serialize with _parser_snapshot_json()"]
Serialize --> Cap["Cap at _SNAPSHOT_JSON_MAX"]
Cap --> Store["Store in Candidate.parser_snapshot_json"]
Store --> Restore["Restore in routes when needed"]
```

**Diagram sources**
- [analyze.py:136-143](file://app/backend/routes/analyze.py#L136-L143)
- [analyze.py:145-172](file://app/backend/routes/analyze.py#L145-L172)
- [candidates.py:228-267](file://app/backend/routes/candidates.py#L228-L267)
- [002_parser_snapshot_json.py:21-33](file://alembic/versions/002_parser_snapshot_json.py#L21-L33)

**Section sources**
- [analyze.py:136-172](file://app/backend/routes/analyze.py#L136-L172)
- [candidates.py:228-267](file://app/backend/routes/candidates.py#L228-L267)
- [db_models.py:120-121](file://app/backend/models/db_models.py#L120-L121)
- [002_parser_snapshot_json.py:21-33](file://alembic/versions/002_parser_snapshot_json.py#L21-L33)

### Deduplication and Profile Storage
- Three-layer deduplication: email, file hash, and name+phone.
- On new or updated analysis, the system stores:
  - Raw text (capped)
  - Skills, education, work experience (JSON arrays)
  - Gap analysis (JSON object)
  - Current role/company and total years experience
  - Profile quality and timestamps
  - Full parser snapshot (JSON)

```mermaid
flowchart TD
Start(["Start analysis"]) --> Dedup["3-layer dedup (email/hash/name+phone)"]
Dedup --> Exists{"Existing candidate?"}
Exists --> |Yes| Update["Update stored profile"]
Exists --> |No| Create["Create new candidate"]
Update --> Store["Store denormalized + snapshot"]
Create --> Store
Store --> End(["Done"])
```

**Diagram sources**
- [analyze.py:174-242](file://app/backend/routes/analyze.py#L174-L242)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

**Section sources**
- [analyze.py:174-242](file://app/backend/routes/analyze.py#L174-L242)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

### Example Parsing Workflows
- PDF resume with skills, work experience, and education:
  - Extract text via PyMuPDF with pdfplumber fallback.
  - Detect skills section and scan full text for additional skills.
  - Parse work experience entries with inferred company/title and descriptions.
  - Extract education degrees and years.
  - Populate contact info using LLM-based extraction with regex fallbacks and enhanced validation.
- DOCX resume:
  - Read paragraphs and table cells to build raw text.
  - Apply the same structured parsing logic as PDF with enhanced contact extraction and improved name validation.
- TXT/other formats:
  - Decode with multiple encodings and return raw text for downstream parsing.

**Updated** Enhanced contact extraction workflow now uses LLM-based extraction as the primary strategy with comprehensive fallback mechanisms and improved validation logic.

**Section sources**
- [parser_service.py:188-196](file://app/backend/services/parser_service.py#L188-L196)
- [parser_service.py:198-236](file://app/backend/services/parser_service.py#L198-L236)
- [test_parser_service.py:17-128](file://app/backend/tests/test_parser_service.py#L17-L128)

### Edge Cases and Fallback Mechanisms
- Scanned PDFs:
  - Early detection with a length threshold triggers a user-friendly error advising text-based PDFs.
- Unsupported or unreadable formats:
  - Graceful ValueError raised with supported formats list.
- Skills extraction fallback:
  - If skills registry processor is unavailable, falls back to a broad skills list.
- Enhanced contact extraction:
  - LLM-based extraction handles international names, creative layouts, and edge cases.
  - Regex extraction provides fallback for standard formats with improved validation.
  - Four-tier fallback system ensures contact extraction success across diverse scenarios.
  - spaCy NER provides highest accuracy when available.
  - Email-based extraction handles cases where header parsing fails.
  - Relaxed header scanning accommodates varied resume layouts.
  - Filename-based extraction serves as final fallback for edge cases.
- Enhanced name validation:
  - Comprehensive skip_phrases collection prevents matching professional roles as names.
  - Multi-pattern phone number detection prevents year matching false positives.
  - Expanded SKIP_WORDS collection improves section header recognition accuracy.

**Updated** Enhanced contact extraction with comprehensive LLM integration covering international names, creative layouts, and edge cases with robust fallback mechanisms and improved validation logic.

**Section sources**
- [parser_service.py:224-230](file://app/backend/services/parser_service.py#L224-L230)
- [parser_service.py:170-173](file://app/backend/services/parser_service.py#L170-L173)
- [parser_service.py:414-421](file://app/backend/services/parser_service.py#L414-L421)
- [parser_service.py:583-610](file://app/backend/services/parser_service.py#L583-L610)

## Dependency Analysis
- Parser service depends on:
  - pdfplumber for PDF text extraction.
  - python-docx for DOCX text extraction.
  - Optional PyMuPDF for improved PDF extraction.
  - Optional unidecode for Unicode normalization.
  - Optional spaCy for advanced name extraction (NER detection).
  - LLM contact extractor for enhanced contact information extraction.
- LLM contact extractor depends on:
  - Ollama API for Gemma model access.
  - httpx for asynchronous HTTP requests.
  - JSON parsing for structured output.
  - LLM service for authentication headers.
- Hybrid pipeline depends on:
  - Skills registry and optional keyword extraction processor.
  - LLM (Ollama) for narrative generation with concurrency control.
- Routes depend on:
  - Parser service for raw text and structured parsing.
  - Gap detector for employment gaps.
  - Hybrid pipeline for scoring and matching.
  - Database models for persistence and retrieval.

```mermaid
graph LR
Parser["parser_service.py"] --> PDF["pdfplumber"]
Parser --> DOCX["python-docx"]
Parser --> PyMu["PyMuPDF (optional)"]
Parser --> Uni["unidecode (optional)"]
Parser --> Spacy["spaCy (optional)"]
Parser --> LLMExt["llm_contact_extractor.py"]
LLMExt --> Ollama["Ollama API"]
LLMExt --> Httpx["httpx (async)"]
LLMExt --> LLMService["llm_service.py"]
Hybrid["hybrid_pipeline.py"] --> Skills["skills registry"]
Hybrid --> LLM["ChatOllama (optional)"]
Routes["routes/analyze.py"] --> Parser
Routes --> Hybrid
Routes --> DB["db_models.py"]
```

**Diagram sources**
- [parser_service.py:1-24](file://app/backend/services/parser_service.py#L1-L24)
- [llm_contact_extractor.py:16-21](file://app/backend/services/llm_contact_extractor.py#L16-L21)
- [hybrid_pipeline.py:45-66](file://app/backend/services/hybrid_pipeline.py#L45-L66)
- [analyze.py:32-39](file://app/backend/routes/analyze.py#L32-L39)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

**Section sources**
- [parser_service.py:1-24](file://app/backend/services/parser_service.py#L1-L24)
- [llm_contact_extractor.py:16-21](file://app/backend/services/llm_contact_extractor.py#L16-L21)
- [hybrid_pipeline.py:45-66](file://app/backend/services/hybrid_pipeline.py#L45-L66)
- [analyze.py:32-39](file://app/backend/routes/analyze.py#L32-L39)

## Performance Considerations
- PDF parsing:
  - Prefer PyMuPDF for speed and accuracy; use pdfplumber as fallback.
  - Scanned PDF guard avoids wasted computation on unreadable content.
- Concurrency:
  - Resume parsing executed in a thread pool to avoid blocking the event loop for large files.
  - LLM contact extraction uses async HTTP client with configurable timeouts.
- Caching:
  - JD parsing cached in DB for reuse across workers.
  - Snapshot JSON stored to avoid re-parsing on re-analysis.
- Memory and size limits:
  - Raw text capped at 100k characters.
  - Snapshot JSON capped at 500KB.
  - LLM extraction limited to first 1000 characters to optimize token usage.
- Skills discovery:
  - Uses a skills registry and optional processor to balance accuracy and performance.
- Enhanced contact extraction:
  - LLM extraction prioritized for accuracy with regex fallbacks for performance.
  - spaCy NER is lazy-loaded and cached for optimal performance.
  - Fallback tiers are ordered by computational cost and accuracy.
  - Async LLM calls prevent blocking the main thread.
  - Multi-pattern phone detection optimized with early exit on match.
  - Comprehensive validation reduces false positives and improves accuracy.

**Updated** Enhanced performance considerations with LLM integration including async HTTP clients, token optimization, and strategic fallback ordering with improved validation logic.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Scanned PDF detected:
  - Symptom: ValueError indicating scanned image.
  - Resolution: Export PDF from a word processor or OCR tool first.
- Unsupported file format:
  - Symptom: ValueError mentioning supported formats.
  - Resolution: Convert to PDF, DOCX, DOC, TXT, RTF, HTML, ODT, or plain text.
- Very short extracted text:
  - Symptom: Error suggesting scanned PDF.
  - Resolution: Ensure the PDF contains selectable text.
- Skills list empty:
  - Symptom: No skills extracted.
  - Resolution: Verify skills section presence or rely on full-text scanning; ensure skills registry is available.
- Contact info incomplete:
  - Symptom: Missing name/email/phone/linkedin.
  - Resolution: LLM-based extraction handles international names and creative layouts; regex fallbacks handle standard formats.
- LLM extraction failures:
  - Symptom: LLM contact extraction failed, using fallbacks.
  - Resolution: Check Ollama service availability, network connectivity, and model installation.
- Name missing:
  - Symptom: Contact info lacks name.
  - Resolution: Enhanced four-tier fallback system should resolve most cases; verify email presence and filename validity.
- spaCy not available:
  - Symptom: NER extraction disabled.
  - Resolution: Install spaCy model (en_core_web_sm) for improved accuracy; system will fall back to other tiers.
- LLM timeout errors:
  - Symptom: Timed out after X.Xs.
  - Resolution: Increase timeout value or check Ollama service performance.
- Phone number false positives:
  - Symptom: Years incorrectly matched as phone numbers.
  - Resolution: Enhanced validation prevents matching years 1900-2099; check phone number patterns.
- Professional role misidentified:
  - Symptom: Job titles matched as candidate names.
  - Resolution: Comprehensive skip_phrases validation prevents role names from being extracted.

**Updated** Enhanced troubleshooting guidance for the new LLM integration including timeout handling, Ollama service requirements, and improved validation logic for phone numbers and name extraction.

**Section sources**
- [parser_service.py:224-230](file://app/backend/services/parser_service.py#L224-L230)
- [parser_service.py:170-173](file://app/backend/services/parser_service.py#L170-L173)
- [parser_service.py:414-421](file://app/backend/services/parser_service.py#L414-L421)
- [parser_service.py:583-610](file://app/backend/services/parser_service.py#L583-L610)
- [llm_contact_extractor.py:120-130](file://app/backend/services/llm_contact_extractor.py#L120-L130)

## Conclusion
The resume parsing pipeline integrates robust text extraction, structured parsing, and a comprehensive skills discovery layer to deliver a complete candidate profile. It includes strong error handling, deduplication, caching, and snapshot storage for auditing and re-analysis. The enhanced contact extraction system provides maximum accuracy through integrated LLM-based extraction using the Gemma model, combined with a four-tier fallback mechanism covering spaCy NER, email-based extraction, relaxed header scanning, and filename-based parsing. The system now features comprehensive validation logic with expanded SKIP_WORDS collections, advanced skip_phrases validation for professional roles, and improved phone number detection with year validation. The modular design allows customization of skills discovery and LLM integration while maintaining performance and reliability.

**Updated** Enhanced conclusion reflecting the robust LLM integration with Gemma model, improved accuracy guarantees through sophisticated extraction strategies, and comprehensive validation logic for enhanced parsing reliability.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Parser Snapshot JSON Schema
- Fields:
  - raw_text: string
  - work_experience: array of objects with company, title, start_date, end_date, description
  - skills: array of strings
  - education: array of objects with degree, field, university, year
  - contact_info: object with name, email, phone, linkedin

Storage and retrieval:
- Stored in Candidate.parser_snapshot_json as a JSON string.
- Restored in routes when present; otherwise reconstructed from denormalized columns.

**Section sources**
- [analyze.py:136-172](file://app/backend/routes/analyze.py#L136-L172)
- [candidates.py:228-267](file://app/backend/routes/candidates.py#L228-L267)
- [db_models.py:120-121](file://app/backend/models/db_models.py#L120-L121)

### Configuration Options and Customization
- Skills registry:
  - Extend MASTER_SKILLS and SKILL_ALIASES in the hybrid pipeline to customize recognized technologies.
- LLM settings:
  - Adjust model, base URL, temperature, num_predict, and num_ctx in the LLM singleton.
  - Configure OLLAMA_BASE_URL and OLLAMA_MODEL environment variables for LLM contact extraction.
- Deduplication behavior:
  - Modify deduplication thresholds and actions in the routes logic.
- Parser behavior:
  - Add or refine date patterns and section headers in ResumeParser for varied resume layouts.
- Enhanced contact extraction:
  - LLM model availability affects extraction accuracy; configure Ollama service for optimal results.
  - Email-based extraction can be customized by modifying the email parsing regex.
  - Filename-based extraction validation rules can be adjusted for specific naming conventions.
  - LLM extraction timeout can be tuned for different network conditions.
  - Phone number detection patterns can be customized for regional variations.
- Storage limits:
  - Tune raw text cap and snapshot JSON cap to balance fidelity and performance.
- Validation customization:
  - Expand SKIP_WORDS collection for additional section headers.
  - Add professional roles to skip_phrases collection for improved name validation.
  - Customize phone number patterns for specific regional formats.

**Updated** Added configuration options for the enhanced LLM integration including Ollama service settings, extraction timeout tuning, and validation customization for improved parsing accuracy.

**Section sources**
- [hybrid_pipeline.py:69-182](file://app/backend/services/hybrid_pipeline.py#L69-L182)
- [hybrid_pipeline.py:45-66](file://app/backend/services/hybrid_pipeline.py#L45-L66)
- [analyze.py:174-242](file://app/backend/routes/analyze.py#L174-L242)
- [parser_service.py:42-63](file://app/backend/services/parser_service.py#L42-L63)
- [llm_contact_extractor.py:16-17](file://app/backend/services/llm_contact_extractor.py#L16-L17)