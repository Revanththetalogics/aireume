# Parser Service

<cite>
**Referenced Files in This Document**
- [parser_service.py](file://app/backend/services/parser_service.py)
- [llm_contact_extractor.py](file://app/backend/services/llm_contact_extractor.py)
- [llm_service.py](file://app/backend/services/llm_service.py)
- [test_parser_service.py](file://app/backend/tests/test_parser_service.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [candidates.py](file://app/backend/routes/candidates.py)
- [gap_detector.py](file://app/backend/services/gap_detector.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [requirements.txt](file://requirements.txt)
- [main.py](file://app/backend/main.py)
- [metrics.py](file://app/backend/services/metrics.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced DOCX parsing with comprehensive multi-stage extraction pipeline including headers, textboxes, tables, paragraphs, and XML fallback for corrupted files
- Integrated new LLM contact extraction service with async processing and intelligent merging strategy
- Implemented sophisticated fallback mechanisms for all resume formats (PDF, DOCX, DOC, RTF, ODT)
- Enhanced error handling with comprehensive logging and structured error reporting
- Added retry mechanisms for PDF extraction failures
- Implemented performance monitoring with Prometheus metrics
- Enhanced observability with structured logging and request correlation IDs
- Added comprehensive fallback strategies for all extraction methods
- Enhanced spaCy NER integration with tiered name extraction approach
- **Updated**: Enhanced name extraction with expanded skip_phrases dictionary containing 30+ professional titles and job-related phrases
- **Updated**: Improved phone number detection with multi-pattern regex approach and year validation to prevent false positives
- **Updated**: Expanded SKIP_WORDS collection with additional words for better contact information distinction
- **Updated**: Enhanced skip_phrases dictionary in _name_from_header_line function with commonly misinterpreted section headers

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Enhanced Error Handling and Observability](#enhanced-error-handling-and-observability)
7. [Performance Monitoring and Metrics](#performance-monitoring-and-metrics)
8. [Dependency Analysis](#dependency-analysis)
9. [Performance Considerations](#performance-considerations)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [Conclusion](#conclusion)
12. [Appendices](#appendices)

## Introduction
This document describes the resume parsing service that extracts structured data from PDF and DOCX formats. It explains the text processing pipeline, including OCR capabilities, formatting preservation, and data normalization. It also covers supported file formats, parsing accuracy characteristics, fallback strategies for malformed documents, examples of extracted data schemas, parsing configuration options, integration patterns with the analysis engine, and enhanced error handling with comprehensive logging and observability features.

**Updated**: The service now features enhanced DOCX parsing capabilities with a comprehensive multi-stage extraction pipeline and a robust zipfile fallback system for corrupted files, along with integration of a new LLM contact extraction service for improved accuracy in contact information extraction. Sophisticated fallback mechanisms have been implemented for all resume formats including PDF (PyMuPDF, pdfplumber), DOCX (headers, textboxes, tables, paragraphs, XML fallback), DOC (antiword, LibreOffice conversion, ASCII extraction), RTF (striprtf), and ODT (odfpy). **Enhanced**: Name extraction now includes an expanded skip_phrases dictionary with 30+ professional titles and improved phone number detection with multi-pattern regex and year validation.

## Project Structure
The parser service is implemented as a dedicated module and integrated into the broader analysis pipeline. Key integration points include:
- Routes that accept uploads and orchestrate parsing and analysis
- Services that implement parsing, gap detection, and hybrid scoring
- Models that define persisted schemas and database entities
- Tests that validate parsing behavior and edge cases
- Metrics collection for performance monitoring
- Structured logging for observability

```mermaid
graph TB
subgraph "Routes"
A["/analyze (POST)"]
B["/analyze/stream (SSE)"]
C["/api/candidates/{id}/analyze-jd (POST)"]
end
subgraph "Services"
S1["parser_service.parse_resume"]
S2["gap_detector.analyze_gaps"]
S3["hybrid_pipeline.run_hybrid_pipeline"]
S4["llm_contact_extractor.extract_contact_with_llm"]
end
subgraph "Models"
M1["Candidate (parsed fields)"]
M2["ScreeningResult (analysis_result)"]
M3["JdCache (JD parse cache)"]
end
subgraph "Monitoring"
METRICS["Metrics Collection"]
LOGGING["Structured Logging"]
END
A --> S1
A --> S2
A --> S3
B --> S1
B --> S2
B --> S3
C --> S3
S1 --> M1
S2 --> M1
S3 --> M2
S3 --> M3
S1 --> METRICS
S1 --> LOGGING
S2 --> LOGGING
S3 --> LOGGING
S4 --> LOGGING
```

**Diagram sources**
- [analyze.py:449-649](file://app/backend/routes/analyze.py#L449-L649)
- [candidates.py:192-303](file://app/backend/routes/candidates.py#L192-L303)
- [parser_service.py:193-202](file://app/backend/services/parser_service.py#L193-L202)
- [gap_detector.py:217-219](file://app/backend/services/gap_detector.py#L217-L219)
- [hybrid_pipeline.py:1-12](file://app/backend/services/hybrid_pipeline.py#L1-L12)
- [db_models.py:97-147](file://app/backend/models/db_models.py#L97-L147)
- [metrics.py:22-27](file://app/backend/services/metrics.py#L22-L27)

**Section sources**
- [analyze.py:1-200](file://app/backend/routes/analyze.py#L1-L200)
- [parser_service.py:1-1255](file://app/backend/services/parser_service.py#L1-L1255)
- [gap_detector.py:1-219](file://app/backend/services/gap_detector.py#L1-L219)
- [hybrid_pipeline.py:1-200](file://app/backend/services/hybrid_pipeline.py#L1-L200)
- [db_models.py:1-250](file://app/backend/models/db_models.py#L1-L250)

## Core Components
- **ResumeParser**: Implements extraction and parsing for PDF, DOCX, DOC, RTF, ODT, and TXT; extracts contact info, skills, education, and work experience; normalizes text and enforces scanned-PDF guardrails.
- **Enhanced DOCX Parser**: Comprehensive multi-stage extraction pipeline with headers, textboxes, tables, paragraphs, and XML fallback for corrupted files.
- **Sophisticated Fallback Mechanisms**: Multi-stage extraction pipelines for all supported formats with comprehensive error handling and logging.
- **LLM Contact Extractor**: Async service that uses Ollama/Gemma for accurate contact information extraction with intelligent merging strategy.
- **GapDetector**: Computes employment timeline, total effective years, gaps, overlaps, and short stints from parsed work experience.
- **Hybrid pipeline**: Orchestrates JD parsing, candidate profile assembly, skill matching, education scoring, and LLM narrative generation.
- **Routes**: Expose endpoints for single and streaming analysis, and for re-analysis using stored profiles.
- **Enhanced Error Handling**: Comprehensive logging, structured error reporting, and retry mechanisms for improved reliability.
- **Observability Layer**: Structured logging with request correlation IDs and performance metrics collection.

Key capabilities:
- Text extraction from PDF using PyMuPDF with pdfplumber fallback; DOCX via python-docx; TXT via UTF-8 decoding.
- Heuristic-based parsing for skills, education, and work experience with robust fallbacks.
- Name enrichment from email and relaxed heuristics when header parsing fails.
- Stored parser snapshots and deduplication to accelerate re-analysis.
- **Enhanced**: Tiered name extraction using spaCy NER for improved accuracy.
- **Enhanced**: Comprehensive logging with structured error reporting for better observability.
- **Enhanced**: Performance monitoring with Prometheus metrics collection.
- **Enhanced**: Multi-stage DOCX extraction with zipfile fallback system for corrupted files.
- **Enhanced**: Async LLM contact extraction with intelligent merging strategy.
- **Enhanced**: Sophisticated fallback mechanisms for all resume formats with comprehensive error handling.
- **Enhanced**: **Expanded skip_phrases dictionary**: 30+ professional titles and job-related phrases excluded from name extraction.
- **Enhanced**: **Multi-pattern phone detection**: Enhanced regex patterns with year validation to prevent false positives.
- **Enhanced**: **Expanded skip words**: Additional words for better contact information distinction.

**Section sources**
- [parser_service.py:130-1255](file://app/backend/services/parser_service.py#L130-L1255)
- [llm_contact_extractor.py:1-165](file://app/backend/services/llm_contact_extractor.py#L1-L165)
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)
- [hybrid_pipeline.py:467-751](file://app/backend/services/hybrid_pipeline.py#L467-L751)
- [analyze.py:449-649](file://app/backend/routes/analyze.py#L449-L649)

## Architecture Overview
The parser service integrates with the analysis pipeline as follows:
- Upload handlers call parse_resume to produce raw text and structured fields.
- Gap analysis computes objective employment metrics.
- Hybrid pipeline composes structured candidate profile, skill matching, and scoring.
- Results are persisted and exposed via endpoints.
- **Enhanced**: All operations are instrumented with logging and metrics collection.
- **Enhanced**: LLM contact extraction provides enhanced accuracy for contact information.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "analyze.py"
participant Parser as "parser_service.parse_resume"
participant LLM as "llm_contact_extractor.extract_contact_with_llm"
participant Gap as "gap_detector.analyze_gaps"
participant Hybrid as "hybrid_pipeline.run_hybrid_pipeline"
participant Metrics as "Metrics Collection"
participant DB as "Database"
Client->>Route : POST /analyze (multipart/form-data)
Route->>Parser : parse_resume(file_bytes, filename)
Parser->>Metrics : Record RESUME_PARSE_DURATION
Parser-->>Route : parsed_data (raw_text, contact_info, skills, education, work_experience)
Route->>LLM : extract_contact_with_llm(raw_text)
LLM-->>Route : enhanced contact_info
Route->>Gap : analyze_gaps(parsed_data.work_experience)
Gap-->>Route : gap_analysis (timeline, total_years, gaps, overlaps, short_stints)
Route->>Hybrid : run_hybrid_pipeline(resume_text, job_description, parsed_data, gap_analysis)
Hybrid-->>Route : analysis_result (scores, matched/missing skills, narrative)
Route->>DB : persist ScreeningResult + Candidate profile snapshot
Route-->>Client : analysis_result
```

**Diagram sources**
- [analyze.py:449-649](file://app/backend/routes/analyze.py#L449-L649)
- [parser_service.py:1201-1255](file://app/backend/services/parser_service.py#L1201-L1255)
- [llm_contact_extractor.py:23-131](file://app/backend/services/llm_contact_extractor.py#L23-L131)
- [gap_detector.py:217-219](file://app/backend/services/gap_detector.py#L217-L219)
- [hybrid_pipeline.py:1-12](file://app/backend/services/hybrid_pipeline.py#L1-L12)
- [metrics.py:22-27](file://app/backend/services/metrics.py#L22-L27)

## Detailed Component Analysis

### Enhanced ResumeParser
The ResumeParser class performs:
- File-type routing to appropriate extractor
- PDF extraction using PyMuPDF with pdfplumber fallback; scanned-PDF guard
- **Enhanced**: DOCX extraction via comprehensive multi-stage pipeline with headers, textboxes, tables, paragraphs, and XML fallback
- **Enhanced**: DOC extraction via antiword, LibreOffice conversion, and ASCII fallback
- **Enhanced**: RTF extraction via striprtf and regex fallback
- **Enhanced**: ODT extraction via odfpy and XML fallback
- Text normalization using unidecode
- Structured extraction of:
  - Contact info: name, email, phone, LinkedIn
  - Work experience: company, title, start/end dates, description
  - Education: degrees, institutions, years
  - Skills: section-based extraction, full-text scanning, and fallback lists

**Enhanced**: Implements comprehensive error handling with structured logging and retry mechanisms.

```mermaid
classDiagram
class ResumeParser {
+extract_text(file_bytes, filename) str
+parse_resume(file_bytes, filename) Dict
+_extract_pdf_multistage(file_bytes) str
+_extract_docx_multistage(file_bytes) str
+_extract_doc_multistage(file_bytes) str
+_extract_rtf(file_bytes) str
+_extract_odt(file_bytes) str
+_extract_contact_info(text) Dict
+_extract_work_experience(text) List
+_extract_education(text) List
+_extract_skills(text) List
+_extract_name(text) str
}
```

**Diagram sources**
- [parser_service.py:198-1255](file://app/backend/services/parser_service.py#L198-L1255)

**Section sources**
- [parser_service.py:220-238](file://app/backend/services/parser_service.py#L220-L238)
- [parser_service.py:239-492](file://app/backend/services/parser_service.py#L239-L492)
- [parser_service.py:498-737](file://app/backend/services/parser_service.py#L498-L737)
- [parser_service.py:1014-1037](file://app/backend/services/parser_service.py#L1014-L1037)
- [parser_service.py:750-828](file://app/backend/services/parser_service.py#L750-L828)

### Enhanced DOCX Extraction Pipeline
**New Section**: The DOCX extraction now features a comprehensive multi-stage pipeline designed to maximize content recovery from various DOCX file formats:

- **Stage 1: Headers** - Extracts contact information from document headers (often contains name, email, phone)
- **Stage 2: Textboxes and Shapes** - Uses docx2txt for complex layouts with textboxes and custom shapes
- **Stage 3: Tables** - Extracts structured data from tables (commonly contains contact information)
- **Stage 4: Paragraphs** - Standard paragraph extraction for main content
- **Stage 5: XML Fallback** - Direct XML parsing for corrupted or unusual DOCX files

**Enhanced**: Implements comprehensive fallback strategies with structured logging for all extraction methods.

```mermaid
flowchart TD
Start(["_extract_docx_multistage(file_bytes)"]) --> TryDocx["Try python-docx"]
TryDocx --> Headers["Extract headers (Stage 1)"]
Headers --> Textboxes["Extract textboxes (Stage 2)"]
Textboxes --> Tables["Extract tables (Stage 3)"]
Tables --> Paragraphs["Extract paragraphs (Stage 4)"]
Paragraphs --> Success{"Any text extracted?"}
Success --> |Yes| Combine["Combine with source priority"]
Success --> |No| XMLFallback["XML Fallback (Stage 5)"]
XMLFallback --> XMLExtract["Parse word/document.xml"]
XMLExtract --> XMLSuccess{"XML extraction success?"}
XMLSuccess --> |Yes| Combine
XMLSuccess --> |No| Error["Raise ValueError"]
Combine --> Deduplicate["Final deduplication pass"]
Deduplicate --> Return(["Return extracted text"])
```

**Diagram sources**
- [parser_service.py:343-492](file://app/backend/services/parser_service.py#L343-L492)

**Section sources**
- [parser_service.py:343-492](file://app/backend/services/parser_service.py#L343-L492)

### Enhanced DOC Extraction Pipeline
**New Section**: The DOC extraction features a sophisticated multi-stage pipeline for legacy Word documents:

- **Stage 1: Antiword** - Attempts extraction using antiword if available
- **Stage 2: LibreOffice Conversion** - Converts DOC to DOCX using LibreOffice headless conversion
- **Stage 3: ASCII Fallback** - Best-effort ASCII extraction with character cleaning

**Enhanced**: Implements comprehensive fallback strategies with structured logging for all extraction methods.

```mermaid
flowchart TD
Start(["_extract_doc_multistage(file_bytes)"]) --> Antiword["Try antiword"]
Antiword --> Success1{"Text extracted?"}
Success1 --> |Yes| Combine["Combine with source priority"]
Success1 --> |No| LibreOffice["Try LibreOffice conversion"]
LibreOffice --> Success2{"Text extracted?"}
Success2 --> |Yes| Combine
Success2 --> |No| ASCIIFallback["ASCII fallback extraction"]
ASCIIFallback --> Success3{"Text extracted?"}
Success3 --> |Yes| Combine
Success3 --> |No| Error["Raise ValueError"]
Combine --> Deduplicate["Final deduplication pass"]
Deduplicate --> Return(["Return extracted text"])
```

**Diagram sources**
- [parser_service.py:498-594](file://app/backend/services/parser_service.py#L498-L594)

**Section sources**
- [parser_service.py:498-594](file://app/backend/services/parser_service.py#L498-L594)

### Enhanced RTF Extraction Pipeline
**New Section**: The RTF extraction features a two-stage pipeline:

- **Stage 1: striprtf Library** - Uses specialized library for RTF parsing
- **Stage 2: Regex Fallback** - Regex-based RTF stripping for basic RTF files

**Enhanced**: Implements comprehensive fallback strategies with structured logging for all extraction methods.

```mermaid
flowchart TD
Start(["_extract_rtf(file_bytes)"]) --> StripRTF["Try striprtf library"]
StripRTF --> Success1{"Text extracted?"}
Success1 --> |Yes| Combine["Combine with source priority"]
Success1 --> |No| RegexFallback["Regex-based fallback"]
RegexFallback --> Success2{"Text extracted?"}
Success2 --> |Yes| Combine
Success2 --> |No| Error["Raise ValueError"]
Combine --> Deduplicate["Final deduplication pass"]
Deduplicate --> Return(["Return extracted text"])
```

**Diagram sources**
- [parser_service.py:611-664](file://app/backend/services/parser_service.py#L611-L664)

**Section sources**
- [parser_service.py:611-664](file://app/backend/services/parser_service.py#L611-L664)

### Enhanced ODT Extraction Pipeline
**New Section**: The ODT extraction features a two-stage pipeline for OpenDocument Text files:

- **Stage 1: odfpy Library** - Uses specialized library for ODT parsing
- **Stage 2: ZIP/XML Fallback** - Direct XML extraction from ZIP container

**Enhanced**: Implements comprehensive fallback strategies with structured logging for all extraction methods.

```mermaid
flowchart TD
Start(["_extract_odt(file_bytes)"]) --> ODFPY["Try odfpy library"]
ODFPY --> Success1{"Text extracted?"}
Success1 --> |Yes| Combine["Combine with source priority"]
Success1 --> |No| XMLFallback["ZIP/XML fallback"]
XMLFallback --> Success2{"Text extracted?"}
Success2 --> |Yes| Combine
Success2 --> |No| Error["Raise ValueError"]
Combine --> Deduplicate["Final deduplication pass"]
Deduplicate --> Return(["Return extracted text"])
```

**Diagram sources**
- [parser_service.py:666-737](file://app/backend/services/parser_service.py#L666-L737)

**Section sources**
- [parser_service.py:666-737](file://app/backend/services/parser_service.py#L666-L737)

### LLM Contact Extraction Integration
**New Section**: The parser now integrates with a dedicated LLM contact extraction service for enhanced accuracy:

- **Async Processing**: Uses async HTTP client for non-blocking LLM calls
- **Intelligent Merging**: Combines LLM results with regex extraction using strategic precedence
- **Robust Error Handling**: Graceful degradation when LLM is unavailable
- **Authentication**: Supports both local Ollama and Ollama Cloud with API key authentication

**Enhanced**: Implements comprehensive fallback strategies with structured logging for all extraction failures.

```mermaid
flowchart TD
Start(["enrich_parsed_resume_async(data, filename)"]) --> CheckComplete{"Contact info complete?"}
CheckComplete --> |Yes| Return["Skip enrichment"]
CheckComplete --> |No| TryLLM["Try LLM extraction"]
TryLLM --> LLMTimeout{"LLM call success?"}
LLMTimeout --> |Yes| MergeResults["Merge LLM + regex results"]
LLMTimeout --> |No| Fallbacks["Use traditional fallbacks"]
MergeResults --> NameCheck{"Name extracted?"}
NameCheck --> |Yes| Return
NameCheck --> |No| Traditional["Traditional fallbacks"]
Traditional --> NERTier["spaCy NER extraction"]
NERTier --> EmailTier["Email-based extraction"]
EmailTier --> RelaxedTier["Relaxed header scan"]
RelaxedTier --> FilenameTier["Filename-based extraction"]
FilenameTier --> Return["Return enriched data"]
```

**Diagram sources**
- [parser_service.py:1080-1155](file://app/backend/services/parser_service.py#L1080-L1155)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)

**Section sources**
- [parser_service.py:1080-1155](file://app/backend/services/parser_service.py#L1080-L1155)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)

### Enhanced Name Extraction with Expanded Skip Phrases Dictionary
**Updated Section**: The name extraction algorithm now includes sophisticated filtering mechanisms to prevent false positive name detection:

- **SKIP_WORDS Collection**: Comprehensive set of 25+ words that indicate non-name content (resume, curriculum, vitae, cv, profile, summary, objective, contact, address, details, information, page, updated, date, experience, education, skills, employment, work, projects, references, certifications, awards, publications, languages, interests, hobbies, activities, achievements)
- **skip_phrases Dictionary**: Contains 30+ professional titles and job-related phrases that are definitively not names, including newly added section headers like 'key expertise', 'key skills', 'core competencies', 'top skills', 'technical experience', 'embedded experience', 'professional experience', 'work experience', 'career highlights', 'summary', 'objective', 'personal details', 'contact information', and 'contact details'
- **Multi-stage Filtering**: Applies skip_words, skip_phrases, and job title pattern checks before accepting potential names

**Enhanced**: Implements comprehensive filtering to distinguish between actual names and contact information or job titles.

```mermaid
flowchart TD
Start(["_name_from_header_line(line, skip_words)"]) --> Split["Split by separators (|, •)"]
Split --> Loop["For each segment"]
Loop --> CheckEmpty{"Valid segment?"}
CheckEmpty --> |No| NextSeg["Next segment"]
CheckEmpty --> |Yes| CheckEmail{"Contains @ or LinkedIn?"}
CheckEmail --> |Yes| NextSeg
CheckEmail --> |No| CheckDigits{"Too many digits?"}
CheckDigits --> |Yes| NextSeg
CheckDigits --> |No| CheckPhone{"Looks like phone?"}
CheckPhone --> |Yes| NextSeg
CheckPhone --> |No| CheckLength{"1-5 words?"}
CheckLength --> |No| NextSeg
CheckLength --> |Yes| CheckSkipWords{"Matches skip_words?"}
CheckSkipWords --> |Yes| NextSeg
CheckSkipWords --> |No| CheckSkipPhrases{"Matches skip_phrases?"}
CheckSkipPhrases --> |Yes| NextSeg
CheckSkipPhrases --> |No| CheckJobTitle{"Ends with job title?"}
CheckJobTitle --> |Yes| NextSeg
CheckJobTitle --> |No| CheckTitleCase{"Title case pattern?"}
CheckTitleCase --> |No| NextSeg
CheckTitleCase --> |Yes| Accept["Accept as name"]
NextSeg --> Loop
Loop --> End(["Return empty if none found"])
```

**Diagram sources**
- [parser_service.py:994-1042](file://app/backend/services/parser_service.py#L994-L1042)

**Section sources**
- [parser_service.py:975-1042](file://app/backend/services/parser_service.py#L975-L1042)

### Enhanced Phone Number Detection
**Updated Section**: The phone number extraction algorithm now uses a sophisticated multi-pattern approach with validation to prevent false positives:

- **Multi-pattern Regex**: Three distinct patterns for different phone number formats:
  - International format: +1-555-123-4567, +91 98765 43210
  - Parentheses format: (555) 123-4567, (555)123-4567
  - Standard format: 555-123-4567, 555.123.4567, 555 123 4567
- **Digit Validation**: Ensures phone numbers contain at least 7 digits
- **Year Validation**: Prevents matching 4-digit years (1900-2099) as phone numbers
- **Pattern Matching**: Uses specific regex patterns to avoid matching dates or other numeric sequences

**Enhanced**: Implements comprehensive validation to distinguish between actual phone numbers and other numeric content.

```mermaid
flowchart TD
Start(["_extract_contact_info(text)"]) --> LoopPatterns["For each phone pattern"]
LoopPatterns --> PatternMatch{"Pattern match found?"}
PatternMatch --> |No| NextPattern["Next pattern"]
PatternMatch --> |Yes| ExtractPhone["Extract phone number"]
ExtractPhone --> DigitCheck{"Has 7+ digits?"}
DigitCheck --> |No| NextPattern
DigitCheck --> |Yes| YearCheck{"Looks like year (1900-2099)?"}
YearCheck --> |Yes| NextPattern
YearCheck --> |No| AcceptPhone["Accept as phone number"]
NextPattern --> LoopPatterns
LoopPatterns --> End(["Return contact info"])
```

**Diagram sources**
- [parser_service.py:1052-1072](file://app/backend/services/parser_service.py#L1052-L1072)

**Section sources**
- [parser_service.py:1052-1072](file://app/backend/services/parser_service.py#L1052-L1072)

### Text Extraction and Normalization
- PDF: PyMuPDF primary; pdfplumber fallback; scanned-PDF guard raises actionable error if text length below threshold.
- **Enhanced**: DOCX: Comprehensive multi-stage extraction pipeline with headers, textboxes, tables, paragraphs, and XML fallback for corrupted files.
- **Enhanced**: DOC: Multi-stage extraction with antiword, LibreOffice conversion, and ASCII fallback.
- **Enhanced**: RTF: Two-stage extraction with striprtf and regex fallback.
- **Enhanced**: ODT: Two-stage extraction with odfpy and ZIP/XML fallback.
- TXT: UTF-8 decoding with fallback encodings.
- Normalization: Unidecode applied to remove accents and diacritics.

**Enhanced**: Implements comprehensive fallback strategies with structured logging for all extraction methods.

```mermaid
flowchart TD
Start(["extract_text(file_bytes, filename)"]) --> CheckExt{"Extension?"}
CheckExt --> |pdf| PDF["_extract_pdf_multistage(file_bytes)"]
PDF --> Retry{"Retry needed?"}
Retry --> |Yes| LogWarn["Log warning with filename and error"]
Retry --> |No| ScanGuard{"Text length < 100?"}
CheckExt --> |docx| DOCX["_extract_docx_multistage(file_bytes)"]
CheckExt --> |doc| DOC["_extract_doc_multistage(file_bytes)"]
CheckExt --> |rtf| RTF["_extract_rtf(file_bytes)"]
CheckExt --> |odt| ODT["_extract_odt(file_bytes)"]
CheckExt --> |txt| TXT["Decode UTF-8"]
DOCX --> Stage1["Headers extraction"]
DOCX --> Stage2["Textboxes extraction"]
DOCX --> Stage3["Tables extraction"]
DOCX --> Stage4["Paragraphs extraction"]
DOCX --> Stage5["XML fallback"]
DOC --> Stage1["Antiword extraction"]
DOC --> Stage2["LibreOffice conversion"]
DOC --> Stage3["ASCII fallback"]
RTF --> Stage1["striprtf extraction"]
RTF --> Stage2["Regex fallback"]
ODT --> Stage1["odfpy extraction"]
ODT --> Stage2["ZIP/XML fallback"]
Stage1 --> ScanGuard
Stage2 --> ScanGuard
Stage3 --> ScanGuard
Stage4 --> ScanGuard
Stage5 --> ScanGuard
TXT --> ScanGuard
ScanGuard --> |Yes| Raise["Raise readable error"]
ScanGuard --> |No| Normalize["Apply unidecode if available"]
Normalize --> Return(["Return normalized text"])
```

**Diagram sources**
- [parser_service.py:220-238](file://app/backend/services/parser_service.py#L220-L238)
- [parser_service.py:239-492](file://app/backend/services/parser_service.py#L239-L492)
- [parser_service.py:498-737](file://app/backend/services/parser_service.py#L498-L737)
- [parser_service.py:238-240](file://app/backend/services/parser_service.py#L238-L240)

**Section sources**
- [parser_service.py:220-238](file://app/backend/services/parser_service.py#L220-L238)
- [parser_service.py:239-492](file://app/backend/services/parser_service.py#L239-L492)
- [parser_service.py:498-737](file://app/backend/services/parser_service.py#L498-L737)
- [parser_service.py:238-240](file://app/backend/services/parser_service.py#L238-L240)

### Contact Information Extraction
- Name: Header-based heuristic with pipe/separator splitting; relaxed fallback scans first lines for title-case names.
- Email/Phone/LinkedIn: Regex-based extraction; LinkedIn pattern supports common URL forms.
- **Enhanced**: LLM-based extraction using Ollama/Gemma for international names, creative layouts, and edge cases.
- **Enhanced**: **Expanded skip phrases filtering**: Professional titles and job-related phrases excluded from name extraction.
- **Enhanced**: **Multi-pattern phone validation**: Enhanced phone number detection with digit and year validation.

**Enhanced**: Implements tiered name extraction with spaCy NER for improved accuracy.

```mermaid
flowchart TD
StartCI(["_extract_contact_info(text)"]) --> Name["_extract_name(text)"]
Name --> LLMContact["extract_contact_with_llm(raw_text)"]
LLMContact --> Merge["merge_contact_info(regex_result, llm_result)"]
Merge --> NERTier["Tier 0: spaCy NER extraction"]
NERTier --> EmailTier["Tier 1: Email-based extraction"]
EmailTier --> RelaxedTier["Tier 2: Relaxed header scan"]
RelaxedTier --> Email["Regex email"]
Email --> Phone["Regex phone (multi-pattern)"]
Phone --> LinkedIn["Regex LinkedIn"]
LinkedIn --> Out(["Return {name?, email?, phone?, linkedin?}"])
```

**Diagram sources**
- [parser_service.py:1014-1037](file://app/backend/services/parser_service.py#L1014-L1037)
- [parser_service.py:1080-1155](file://app/backend/services/parser_service.py#L1080-L1155)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)

**Section sources**
- [parser_service.py:1014-1037](file://app/backend/services/parser_service.py#L1014-L1037)
- [parser_service.py:1080-1155](file://app/backend/services/parser_service.py#L1080-L1155)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)

### Work Experience Extraction
- Date pattern matching supports various formats and "present/current" indicators.
- Company/title parsing via separators ("|", ",", " at ") or preceding lines.
- Description accumulation for multi-line entries.

```mermaid
flowchart TD
StartExp(["_extract_work_experience(text)"]) --> Lines["Split into lines"]
Lines --> Iterate{"For each line"}
Iterate --> DateMatch{"Date pattern match?"}
DateMatch --> |Yes| NewJob["Start new job entry"]
DateMatch --> |No| Accumulate{"In job block?"}
Accumulate --> |Yes| AppendDesc["Append description"]
Accumulate --> |No| Remember["Remember as potential role line"]
NewJob --> Iterate
AppendDesc --> Iterate
Remember --> Iterate
Iterate --> EndExp(["Return jobs list"])
```

**Diagram sources**
- [parser_service.py:750-828](file://app/backend/services/parser_service.py#L750-L828)

**Section sources**
- [parser_service.py:750-828](file://app/backend/services/parser_service.py#L750-L828)

### Skills Extraction
- Section-based extraction using multiple skill headers.
- Full-text scanning using a keyword processor backed by a dynamic skills registry.
- Fallback to broad skill list when registry unavailable.

**Enhanced**: Implements comprehensive fallback strategy with structured logging for all extraction failures.

```mermaid
flowchart TD
StartSkills(["_extract_skills(text)"]) --> Section["Find skills section"]
Section --> Split["Split by delimiters"]
Split --> Registry["Scan with skills registry (flashtext)"]
Registry --> Merge["Merge section + scanned, dedupe"]
Merge --> Fallback{"Empty and registry failed?"}
Fallback --> |Yes| LogWarn["Log warning about registry unavailability"]
LogWarn --> Broad["Scan with KNOWN_SKILLS_BROAD"]
Fallback --> |No| Done["Return skills"]
Broad --> Done
```

**Diagram sources**
- [parser_service.py:865-918](file://app/backend/services/parser_service.py#L865-L918)
- [hybrid_pipeline.py:139-200](file://app/backend/services/hybrid_pipeline.py#L139-L200)

**Section sources**
- [parser_service.py:865-918](file://app/backend/services/parser_service.py#L865-L918)
- [hybrid_pipeline.py:139-200](file://app/backend/services/hybrid_pipeline.py#L139-L200)

### Education Extraction
- Section-based extraction using education headers.
- Degree pattern matching and optional university/year extraction.

```mermaid
flowchart TD
StartEdu(["_extract_education(text)"]) --> Section["Find education section"]
Section --> Lines["Split into lines"]
Lines --> ForEach{"For each line"}
ForEach --> Degree{"Degree pattern match?"}
Degree --> |Yes| Fields["Extract year/university"]
Fields --> Add["Append to education list"]
Degree --> |No| Next["Next line"]
Add --> ForEach
Next --> ForEach
ForEach --> EndEdu(["Return education list"])
```

**Diagram sources**
- [parser_service.py:920-964](file://app/backend/services/parser_service.py#L920-L964)

**Section sources**
- [parser_service.py:920-964](file://app/backend/services/parser_service.py#L920-L964)

### Gap Detection
- Converts dates to YYYY-MM, merges overlapping intervals, computes total effective years.
- Builds employment timeline with gap metadata and severity thresholds.

```mermaid
flowchart TD
StartGap(["analyze_gaps(work_experience)"]) --> Normalize["Normalize dates to YYYY-MM"]
Normalize --> Sort["Sort by start date"]
Sort --> Merge["Merge overlapping intervals"]
Merge --> Sum["Sum durations to total_years"]
Sum --> Timeline["Build timeline with gaps/severity"]
Timeline --> Out(["Return {timeline, gaps, overlaps, short_stints, total_years}"])
```

**Diagram sources**
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)

**Section sources**
- [gap_detector.py:103-219](file://app/backend/services/gap_detector.py#L103-L219)

### Integration Patterns
- Single-shot analysis: POST /analyze parses resume, computes gaps, runs hybrid pipeline, persists results.
- Streaming analysis: POST /analyze/stream returns events as they complete.
- Re-analysis: POST /api/candidates/{id}/analyze-jd uses stored parser snapshot and denormalized fields.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "candidates.py"
participant DB as "Database"
participant Hybrid as "hybrid_pipeline.run_hybrid_pipeline"
Client->>Route : POST /api/candidates/{id}/analyze-jd
Route->>DB : Load parser_snapshot_json and denormalized fields
Route->>Hybrid : run_hybrid_pipeline(resume_text, job_description, parsed_data, gap_analysis)
Hybrid-->>Route : analysis_result
Route->>DB : persist ScreeningResult
Route-->>Client : analysis_result
```

**Diagram sources**
- [candidates.py:192-303](file://app/backend/routes/candidates.py#L192-L303)
- [hybrid_pipeline.py:1-12](file://app/backend/services/hybrid_pipeline.py#L1-L12)

**Section sources**
- [analyze.py:449-649](file://app/backend/routes/analyze.py#L449-L649)
- [candidates.py:192-303](file://app/backend/routes/candidates.py#L192-L303)

## Enhanced Error Handling and Observability

### Structured Logging Implementation
The parser service implements comprehensive logging with structured error reporting:

- **Production JSON Logging**: Structured JSON format for production environments
- **Development Console Logging**: Human-readable format with timestamps and function names
- **Request Correlation**: Unique correlation IDs propagated through request lifecycle
- **Comprehensive Error Logging**: Detailed warnings for all fallback scenarios

### Tiered Name Extraction Strategy
**Enhanced**: Implements a four-tier name extraction approach for improved accuracy:

1. **Tier 0 (spaCy NER)**: Uses Named Entity Recognition for highest accuracy
2. **Tier 1 (LLM Contact Extraction)**: Async LLM processing for international names and edge cases
3. **Tier 2 (Email-based)**: Extracts name from email address when NER unavailable
4. **Tier 3 (Relaxed header scan)**: Fallback heuristic-based extraction

### Retry Mechanisms and Fallback Strategies
**Enhanced**: Comprehensive fallback strategies for all extraction methods:

- **PDF Extraction**: PyMuPDF primary with pdfplumber fallback
- **DOCX Extraction**: Multi-stage pipeline with XML fallback for corrupted files
- **DOC Extraction**: antiword, LibreOffice conversion, and ASCII fallback
- **RTF Extraction**: striprtf library with regex fallback
- **ODT Extraction**: odfpy with ZIP/XML fallback
- **Text Extraction**: Multiple encoding attempts with structured error logging
- **Skills Registry**: Dynamic skills registry with broad fallback list
- **NER Model Loading**: Graceful degradation when spaCy unavailable
- **LLM Contact Extraction**: Async processing with timeout handling

### Request Correlation and Context Management
**Enhanced**: Implements request correlation for better observability:

- **Correlation ID Middleware**: Generates unique request IDs per request
- **Context Variables**: Propagates correlation IDs through async operations
- **Structured Log Messages**: Includes correlation IDs and function names

### Enhanced Name Extraction Filtering
**Updated Section**: Implements sophisticated filtering mechanisms to prevent false positive name detection:

- **SKIP_WORDS Collection**: Comprehensive set of 25+ words indicating non-name content
- **Expanded skip_phrases Dictionary**: 30+ professional titles and job-related phrases excluded from name extraction, including newly added section headers like 'key expertise', 'key skills', 'core competencies', 'top skills', 'technical experience', 'embedded experience', 'professional experience', 'work experience', 'career highlights', 'summary', 'objective', 'personal details', 'contact information', and 'contact details'
- **Multi-stage Validation**: Applies filters in sequence to ensure accurate name detection
- **Job Title Pattern Recognition**: Prevents matching job titles as names

**Section sources**
- [parser_service.py:1-14](file://app/backend/services/parser_service.py#L1-L14)
- [parser_service.py:1080-1155](file://app/backend/services/parser_service.py#L1080-L1155)
- [main.py:17-55](file://app/backend/main.py#L17-L55)

## Performance Monitoring and Metrics

### Prometheus Metrics Collection
**Enhanced**: Implements comprehensive performance monitoring:

- **RESUME_PARSE_DURATION**: Histogram metric for resume parsing duration
- **LLM_CALL_DURATION**: Duration tracking for LLM operations
- **LLM_FALLBACK_TOTAL**: Counter for LLM fallback events
- **BATCH_SIZE**: Histogram for batch operation sizes

### Performance Optimization Features
**Enhanced**: Several performance improvements:

- **Early Guard Rails**: Scanned PDF detection prevents wasted processing
- **Lazy Loading**: spaCy model loaded only when needed
- **Graceful Degradation**: Falls back to simpler methods when advanced features unavailable
- **Memory Efficient Processing**: Stream-based PDF processing reduces memory usage
- **Async Processing**: LLM contact extraction uses async HTTP client for non-blocking operations

### Metrics Bucket Configuration
**Enhanced**: Optimized bucket configurations for better granularity:

- **Resume Parse Duration**: Fine-grained buckets for sub-second to multi-second processing
- **Batch Size**: Configured for typical batch operation ranges
- **LLM Call Duration**: Extended buckets for long-running LLM operations

**Section sources**
- [metrics.py:1-35](file://app/backend/services/metrics.py#L1-L35)
- [parser_service.py:1201-1255](file://app/backend/services/parser_service.py#L1201-L1255)

## Dependency Analysis
External libraries and their roles:
- pdfplumber, PyMuPDF: PDF text extraction
- python-docx: DOCX text extraction
- unidecode: Unicode normalization
- flashtext: Fast keyword extraction for skills
- dateparser/dateutil: Flexible date parsing
- langchain-ollama/ChatOllama: LLM reasoning (integrated in hybrid pipeline)
- **Enhanced**: spaCy: Named Entity Recognition for improved name extraction
- **Enhanced**: prometheus_client: Performance metrics collection
- **Enhanced**: prometheus_fastapi_instrumentator: FastAPI metrics instrumentation
- **Enhanced**: httpx: Async HTTP client for LLM communication
- **Enhanced**: docx2txt: Text extraction from complex DOCX layouts
- **Enhanced**: striprtf: RTF text extraction
- **Enhanced**: odfpy: ODT text extraction

```mermaid
graph TB
P["parser_service.py"] --> PM["PyMuPDF"]
P --> PP["pdfplumber"]
P --> WD["python-docx"]
P --> UD["unidecode"]
P --> SPACY["spaCy (optional)"]
P --> DOCX2TXT["docx2txt (optional)"]
P --> STRIPRTF["striprtf (optional)"]
P --> ODFPY["odfpy (optional)"]
LE["llm_contact_extractor.py"] --> HTTPX["httpx (async)"]
LE --> OLLAMA["Ollama API"]
HP["hybrid_pipeline.py"] --> FT["flashtext"]
HP --> DP["dateparser"]
HP --> LC["langchain-ollama"]
GD["gap_detector.py"] --> DU["dateutil.relativedelta"]
METRICS["metrics.py"] --> PC["prometheus_client"]
MAIN["main.py"] --> JF["JsonFormatter"]
```

**Diagram sources**
- [parser_service.py:13-46](file://app/backend/services/parser_service.py#L13-L46)
- [llm_contact_extractor.py:8-21](file://app/backend/services/llm_contact_extractor.py#L8-L21)
- [hybrid_pipeline.py:1-28](file://app/backend/services/hybrid_pipeline.py#L1-L28)
- [gap_detector.py:12-23](file://app/backend/services/gap_detector.py#L12-L23)
- [metrics.py:8](file://app/backend/services/metrics.py#L8)
- [main.py:27-38](file://app/backend/main.py#L27-L38)

**Section sources**
- [requirements.txt:1-54](file://requirements.txt#L1-L54)

## Performance Considerations
- **PDF extraction**: Prefer PyMuPDF for speed and accuracy; fallback to pdfplumber when needed.
- **Skills extraction**: In-memory flashtext processor for O(n) keyword search; falls back to regex scanning if unavailable.
- **Date parsing**: dateparser for flexible formats; dateutil fallback ensures minimal dependency footprint.
- **Streaming**: SSE endpoints reduce latency and improve UX for long-running analyses.
- **Deduplication**: Reduces repeated parsing and speeds up re-analysis using stored profiles.
- **Enhanced**: **Early termination**: Scanned PDF detection prevents unnecessary processing.
- **Enhanced**: **Lazy loading**: Optional dependencies (spaCy, docx2txt, striprtf, odfpy) loaded only when needed.
- **Enhanced**: **Graceful degradation**: System continues operating with reduced functionality when dependencies unavailable.
- **Enhanced**: **Async processing**: LLM contact extraction uses async HTTP client for non-blocking operations.
- **Enhanced**: **Expanded skip phrase filtering**: Reduces false positives in name extraction by excluding professional titles, job-related phrases, and commonly misinterpreted section headers.

## Troubleshooting Guide
Common issues and resolutions:
- **Unsupported file format**: parse_resume raises a clear error for non-PDF/DOCX/DOC/RTF/ODT/TXT files.
- **Scanned PDF**: Early guard raises a user-friendly error advising text-based exports.
- **Encoding issues**: extract_jd_text attempts multiple encodings; if none succeed, raises a readable error.
- **Empty or malformed resumes**: GapDetector returns conservative estimates; hybrid pipeline still produces narrative.
- **LLM unavailability**: Hybrid pipeline diagnostics expose model readiness; fallback narrative remains deterministic.
- **Enhanced**: **NER model unavailable**: spaCy model loading handles ImportError gracefully; falls back to email-based extraction.
- **Enhanced**: **DOCX corrupted files**: Multi-stage extraction with XML fallback recovers content from corrupted files.
- **Enhanced**: **DOC extraction failures**: antiword, LibreOffice conversion, and ASCII fallback provide multiple recovery options.
- **Enhanced**: **RTF extraction failures**: striprtf library and regex fallback ensure content recovery.
- **Enhanced**: **ODT extraction failures**: odfpy and ZIP/XML fallback provide comprehensive recovery.
- **Enhanced**: **LLM contact extraction failures**: Graceful fallback to regex and traditional methods.
- **Enhanced**: **Name extraction issues**: Expanded skip phrases dictionary prevents matching professional titles and section headers as names.
- **Enhanced**: **Phone number false positives**: Multi-pattern validation with year checking prevents matching dates as phone numbers.
- **Enhanced**: **Logging issues**: Structured logging provides consistent error reporting across environments.
- **Enhanced**: **Performance problems**: Prometheus metrics help identify bottlenecks in parsing operations.

**Section sources**
- [parser_service.py:237](file://app/backend/services/parser_service.py#L237)
- [parser_service.py:324-330](file://app/backend/services/parser_service.py#L324-L330)
- [parser_service.py:456-460](file://app/backend/services/parser_service.py#L456-L460)
- [main.py:262-327](file://app/backend/main.py#L262-L327)

## Conclusion
The parser service provides a robust, deterministic foundation for extracting structured resume data from PDF and DOCX formats. It integrates tightly with gap detection and a hybrid scoring pipeline, enabling accurate and efficient candidate analysis. Its enhanced error handling, comprehensive logging, retry mechanisms, and performance monitoring deliver resilience, observability, and scalability for production use. The tiered name extraction approach, comprehensive multi-stage extraction pipelines with sophisticated fallback mechanisms, and integration with LLM contact extraction ensure reliable operation even with corrupted files and complex resume layouts. **Enhanced**: The expansion of the skip_phrases dictionary, improved phone number detection, and expanded SKIP_WORDS collection significantly improves the accuracy of contact information extraction by preventing false positives and better distinguishing between names, professional titles, and contact details. The newly added section headers like 'key expertise', 'key skills', 'core competencies', 'top skills', 'technical experience', 'embedded experience', 'professional experience', 'work experience', 'career highlights', 'summary', 'objective', 'personal details', 'contact information', and 'contact details' in the skip_phrases dictionary prevent these commonly misinterpreted section headers from being mistakenly identified as candidate names.

## Appendices

### Supported File Formats and Extraction Behavior
- **PDF**: PyMuPDF primary; pdfplumber fallback; scanned-PDF guard.
- **DOCX**: Enhanced multi-stage extraction with headers, textboxes, tables, paragraphs, and XML fallback.
- **DOC**: Enhanced multi-stage extraction with antiword, LibreOffice conversion, and ASCII fallback.
- **RTF**: Enhanced extraction with striprtf library and regex fallback.
- **ODT**: Enhanced extraction with odfpy and ZIP/XML fallback.
- **TXT/MD/CSV/Plain**: Multi-encoding decode attempts.

**Section sources**
- [parser_service.py:210-238](file://app/backend/services/parser_service.py#L210-L238)

### Parsing Configuration Options
- **Scoring weights**: Provided via request form; forwarded to hybrid pipeline.
- **Streaming**: SSE endpoint for progressive results.
- **Dedup action**: Controls whether to reuse existing profile, update it, or create a new candidate.
- **Enhanced**: **NER Configuration**: Optional spaCy model loading with graceful fallback.
- **Enhanced**: **Logging Configuration**: Structured logging with environment-specific formatting.
- **Enhanced**: **LLM Contact Extraction**: Configurable timeout and model selection.
- **Enhanced**: **Name Extraction Filters**: Expanded skip phrases dictionary and expanded SKIP_WORDS collection.

**Section sources**
- [analyze.py:506-649](file://app/backend/routes/analyze.py#L506-L649)
- [candidates.py:192-303](file://app/backend/routes/candidates.py#L192-L303)

### Data Schemas and Storage
- **Candidate fields**: Stores raw text, skills, education, work experience, gap analysis, and parser snapshot JSON.
- **ScreeningResult**: Persists analysis results and parsed data.
- **AnalysisResponse**: Standardized response schema for clients.

**Section sources**
- [db_models.py:97-147](file://app/backend/models/db_models.py#L97-L147)
- [schemas.py:89-125](file://app/backend/models/schemas.py#L89-L125)

### Enhanced Error Handling Features
**New Section**: Comprehensive error handling and observability enhancements:

#### Logging Architecture
- **Structured JSON Logging**: Production-ready JSON format with timestamp, level, logger, message, and function
- **Console Logging**: Development-friendly format with human-readable timestamps
- **Request Correlation**: Unique correlation IDs propagated through request lifecycle
- **Context Variables**: Thread-safe correlation ID storage using contextvars

#### Error Recovery Strategies
- **PDF Extraction Failures**: Automatic fallback from PyMuPDF to pdfplumber with detailed logging
- **DOCX Extraction Failures**: Multi-stage pipeline with XML fallback for corrupted files
- **DOC Extraction Failures**: antiword, LibreOffice conversion, and ASCII fallback provide multiple recovery options
- **RTF Extraction Failures**: striprtf library and regex fallback ensure content recovery
- **ODT Extraction Failures**: odfpy and ZIP/XML fallback provide comprehensive recovery
- **NER Model Failures**: Graceful degradation when spaCy not available
- **Skills Registry Failures**: Fallback to broad skill list when dynamic registry unavailable
- **LLM Contact Extraction Failures**: Async processing with timeout handling and fallbacks
- **Encoding Failures**: Multiple encoding attempts with structured error reporting

#### Performance Monitoring
- **RESUME_PARSE_DURATION**: Histogram for parsing operation timing
- **Request Metrics**: Automatic FastAPI instrumentation for request/response metrics
- **Custom Metrics**: Application-specific metrics for business operations

#### LLM Integration Features
- **Async HTTP Client**: Non-blocking LLM calls using httpx
- **Authentication**: Support for both local Ollama and Ollama Cloud
- **Timeout Handling**: Configurable timeouts for LLM operations
- **Error Recovery**: Graceful fallback when LLM is unavailable
- **Intelligent Merging**: Strategic combination of LLM and regex results

#### Enhanced Name Extraction Features
- **Expanded Skip Phrases Dictionary**: 30+ professional titles and section headers excluded from name extraction
- **Expanded SKIP_WORDS Collection**: 25+ words indicating non-name content
- **Multi-stage Filtering**: Applies skip_words, skip_phrases, and job title pattern checks
- **Phone Number Validation**: Multi-pattern regex with digit and year validation
- **False Positive Prevention**: Sophisticated filtering prevents matching job titles and section headers as names

**Section sources**
- [parser_service.py:1-14](file://app/backend/services/parser_service.py#L1-L14)
- [parser_service.py:1080-1155](file://app/backend/services/parser_service.py#L1080-L1155)
- [llm_contact_extractor.py:23-165](file://app/backend/services/llm_contact_extractor.py#L23-L165)
- [metrics.py:1-35](file://app/backend/services/metrics.py#L1-L35)
- [main.py:17-55](file://app/backend/main.py#L17-L55)