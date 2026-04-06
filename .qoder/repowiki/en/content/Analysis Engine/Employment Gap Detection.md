# Employment Gap Detection

<cite>
**Referenced Files in This Document**
- [gap_detector.py](file://app/backend/services/gap_detector.py)
- [test_gap_detector.py](file://app/backend/tests/test_gap_detector.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [analysis_service.py](file://app/backend/services/analysis_service.py)
- [llm_service.py](file://app/backend/services/llm_service.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [README.md](file://README.md)
</cite>

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
This document explains the employment gap detection algorithm that analyzes work history patterns to identify potential gaps and career transitions. It covers the gap calculation methodology, temporal analysis algorithms, and pattern recognition techniques. It documents the scoring system for gap severity, transition likelihood, and career stability assessment, along with integration points to resume parsing, validation against employment records, and correlation with skill development patterns. The document also includes examples of gap detection scenarios, false positive reduction techniques, confidence scoring, and how gap analysis contributes to overall candidate evaluation and risk assessment.

## Project Structure
The employment gap detection lives in a dedicated service module and integrates with the resume parsing pipeline and the hybrid analysis pipeline. The key files are:
- Gap detection service: [gap_detector.py](file://app/backend/services/gap_detector.py)
- Gap detection tests: [test_gap_detector.py](file://app/backend/tests/test_gap_detector.py)
- Resume parsing: [parser_service.py](file://app/backend/services/parser_service.py)
- Route orchestration: [analyze.py](file://app/backend/routes/analyze.py)
- Analysis service (risk signals and LLM integration): [analysis_service.py](file://app/backend/services/analysis_service.py)
- LLM service: [llm_service.py](file://app/backend/services/llm_service.py)
- Hybrid pipeline (skills, education, scoring): [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- Data models (storage of gap analysis): [db_models.py](file://app/backend/models/db_models.py)

```mermaid
graph TB
A["Resume Parser<br/>parse_resume()"] --> B["Gap Detector<br/>analyze_gaps()"]
B --> C["Hybrid Pipeline<br/>run_hybrid_pipeline()"]
C --> D["Analysis Service<br/>AnalysisService.analyze()"]
D --> E["LLM Service<br/>analyze_with_llm()"]
E --> F["Final Result"]
B --> G["DB Models<br/>Candidate.gap_analysis_json"]
```

**Diagram sources**
- [gap_detector.py:103-218](file://app/backend/services/gap_detector.py#L103-L218)
- [parser_service.py:547-552](file://app/backend/services/parser_service.py#L547-L552)
- [analyze.py:268-318](file://app/backend/routes/analyze.py#L268-L318)
- [analysis_service.py:6-53](file://app/backend/services/analysis_service.py#L6-L53)
- [llm_service.py:139-156](file://app/backend/services/llm_service.py#L139-L156)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

**Section sources**
- [README.md:9-20](file://README.md#L9-L20)
- [gap_detector.py:1-219](file://app/backend/services/gap_detector.py#L1-L219)
- [parser_service.py:193-202](file://app/backend/services/parser_service.py#L193-L202)
- [analyze.py:268-318](file://app/backend/routes/analyze.py#L268-L318)

## Core Components
- GapDetector: Implements date normalization, interval merging, gap classification, and timeline construction.
- analyze_gaps(): Top-level function to run gap detection on parsed work experience.
- ResumeParser: Extracts work experience from resume text, including start/end dates and company/title.
- Routes: Orchestrates parsing, gap analysis, hybrid pipeline, and persistence.
- AnalysisService: Aggregates risk signals (overlaps, short stints) and coordinates LLM analysis.
- LLM Service: Generates narrative and risk signals using a local LLM.
- Hybrid Pipeline: Provides skills, education, and scoring context for gap analysis.

**Section sources**
- [gap_detector.py:103-218](file://app/backend/services/gap_detector.py#L103-L218)
- [parser_service.py:193-202](file://app/backend/services/parser_service.py#L193-L202)
- [analyze.py:268-318](file://app/backend/routes/analyze.py#L268-L318)
- [analysis_service.py:6-53](file://app/backend/services/analysis_service.py#L6-L53)
- [llm_service.py:139-156](file://app/backend/services/llm_service.py#L139-L156)
- [hybrid_pipeline.py:604-637](file://app/backend/services/hybrid_pipeline.py#L604-L637)

## Architecture Overview
The gap detection pipeline follows a clear separation of concerns:
- Parsing: ResumeParser extracts work experience entries with start/end dates.
- Gap Detection: GapDetector normalizes dates, merges overlapping intervals, computes gaps, and builds a timeline.
- Hybrid Pipeline: Skills and education scoring inform the broader analysis.
- LLM Integration: AnalysisService prepares risk signals and passes metrics to LLM for narrative synthesis.
- Persistence: Gap analysis results are stored in Candidate.gap_analysis_json for reuse.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Route as "Routes.analyze_endpoint"
participant Parser as "ResumeParser.parse_resume"
participant Gap as "GapDetector.analyze"
participant Hybrid as "run_hybrid_pipeline"
participant Analysis as "AnalysisService.analyze"
participant LLM as "LLMService.analyze_resume"
participant DB as "DB Models"
Client->>Route : POST /api/analyze
Route->>Parser : parse_resume(file)
Parser-->>Route : parsed_data
Route->>Gap : analyze_gaps(parsed_data.work_experience)
Gap-->>Route : gap_analysis
Route->>Hybrid : run_hybrid_pipeline(...)
Hybrid-->>Route : hybrid_result
Route->>Analysis : AnalysisService.analyze(...)
Analysis->>LLM : analyze_with_llm(...)
LLM-->>Analysis : llm_result
Analysis-->>Route : final_result
Route->>DB : persist Candidate + ScreeningResult
Route-->>Client : final_result
```

**Diagram sources**
- [analyze.py:268-318](file://app/backend/routes/analyze.py#L268-L318)
- [parser_service.py:547-552](file://app/backend/services/parser_service.py#L547-L552)
- [gap_detector.py:217-218](file://app/backend/services/gap_detector.py#L217-L218)
- [analysis_service.py:10-53](file://app/backend/services/analysis_service.py#L10-L53)
- [llm_service.py:139-156](file://app/backend/services/llm_service.py#L139-L156)
- [db_models.py:97-146](file://app/backend/models/db_models.py#L97-L146)

## Detailed Component Analysis

### Gap Detection Algorithm
The GapDetector performs:
- Date normalization to YYYY-MM format with robust parsing for fuzzy inputs.
- Gap calculation between consecutive jobs.
- Severity classification thresholds for gaps.
- Overlap-aware total experience via interval merging to prevent double counting.
- Timeline construction with gap metadata for downstream analysis.

```mermaid
classDiagram
class GapDetector {
+analyze(work_experience) Dict
-_to_ym(date_str) Optional~str~
-_months_between(start_ym, end_ym) int
-_classify_gap(months) str
-_merge_intervals(intervals) Tuple[]str,str~~
}
class GapUtils {
+analyze_gaps(work_experience) Dict
}
GapUtils --> GapDetector : "delegates"
```

**Diagram sources**
- [gap_detector.py:103-218](file://app/backend/services/gap_detector.py#L103-L218)

Key behaviors validated by tests:
- Date normalization supports multiple formats and fuzzy inputs.
- Gap severity thresholds: negligible (<3), minor (<6), moderate (<12), critical (≥12).
- Overlapping jobs are detected and excluded from gaps list.
- Short stints (<6 months) are identified.
- Total experience excludes double-counted overlaps.

**Section sources**
- [gap_detector.py:27-51](file://app/backend/services/gap_detector.py#L27-L51)
- [gap_detector.py:62-67](file://app/backend/services/gap_detector.py#L62-L67)
- [gap_detector.py:70-78](file://app/backend/services/gap_detector.py#L70-L78)
- [gap_detector.py:83-98](file://app/backend/services/gap_detector.py#L83-L98)
- [gap_detector.py:103-214](file://app/backend/services/gap_detector.py#L103-L214)
- [test_gap_detector.py:27-58](file://app/backend/tests/test_gap_detector.py#L27-L58)
- [test_gap_detector.py:66-81](file://app/backend/tests/test_gap_detector.py#L66-L81)
- [test_gap_detector.py:85-108](file://app/backend/tests/test_gap_detector.py#L85-L108)
- [test_gap_detector.py:113-141](file://app/backend/tests/test_gap_detector.py#L113-L141)
- [test_gap_detector.py:166-204](file://app/backend/tests/test_gap_detector.py#L166-L204)
- [test_gap_detector.py:226-241](file://app/backend/tests/test_gap_detector.py#L226-L241)
- [test_gap_detector.py:244-266](file://app/backend/tests/test_gap_detector.py#L244-L266)

### Temporal Analysis and Pattern Recognition
Temporal analysis focuses on:
- Converting ambiguous date strings to normalized YYYY-MM.
- Computing months between dates with relativity-aware arithmetic.
- Detecting gaps between jobs and classifying severity.
- Identifying overlapping jobs and short stints.
- Building a chronological timeline enriched with gap metadata.

```mermaid
flowchart TD
Start(["Start analyze()"]) --> Normalize["Normalize all job dates to YYYY-MM"]
Normalize --> SortJobs["Sort jobs chronologically"]
SortJobs --> ComputeGaps["Compute gaps between consecutive jobs"]
ComputeGaps --> Classify["Classify gap severity"]
Classify --> BuildTimeline["Build employment timeline with gap metadata"]
BuildTimeline --> DetectOverlaps["Detect overlapping jobs"]
DetectOverlaps --> DetectShortStints["Detect short stints (<6 months)"]
DetectShortStints --> MergeIntervals["Merge overlapping intervals for total experience"]
MergeIntervals --> Summarize["Summarize gaps, overlaps, short stints, total years"]
Summarize --> End(["Return gap analysis"])
```

**Diagram sources**
- [gap_detector.py:104-214](file://app/backend/services/gap_detector.py#L104-L214)

**Section sources**
- [gap_detector.py:116-162](file://app/backend/services/gap_detector.py#L116-L162)
- [gap_detector.py:176-200](file://app/backend/services/gap_detector.py#L176-L200)
- [gap_detector.py:202-206](file://app/backend/services/gap_detector.py#L202-L206)

### Scoring System and Risk Signals
The gap analysis produces:
- employment_gaps: gaps ≥3 months with duration and severity.
- overlapping_jobs: pairs of jobs with meaningful overlap (>1 month).
- short_stints: roles with tenure <6 months.
- total_years: overlap-aware total experience in years.

Risk signals derived from gap analysis:
- Overlapping employment risk signal.
- Job hopping risk signal (short stints).

These signals are combined with LLM-generated risk signals in AnalysisService.

**Section sources**
- [gap_detector.py:164-200](file://app/backend/services/gap_detector.py#L164-L200)
- [analysis_service.py:93-110](file://app/backend/services/analysis_service.py#L93-L110)

### Integration with Resume Parsing and Validation
Resume parsing extracts work experience entries with start/end dates and company/title. Gap analysis runs immediately after parsing and before the hybrid pipeline. The parsed work experience is passed to GapDetector, and the resulting gap_analysis is persisted in Candidate.gap_analysis_json for reuse.

```mermaid
sequenceDiagram
participant Parser as "ResumeParser"
participant Gap as "GapDetector"
participant Route as "Routes"
participant DB as "DB Models"
Parser->>Route : parsed_data
Route->>Gap : analyze_gaps(parsed_data.work_experience)
Gap-->>Route : gap_analysis
Route->>DB : Candidate.gap_analysis_json = json.dumps(gap_analysis)
```

**Diagram sources**
- [parser_service.py:193-202](file://app/backend/services/parser_service.py#L193-L202)
- [gap_detector.py:217-218](file://app/backend/services/gap_detector.py#L217-L218)
- [analyze.py:292-293](file://app/backend/routes/analyze.py#L292-L293)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)
- [db_models.py:113](file://app/backend/models/db_models.py#L113)

**Section sources**
- [parser_service.py:204-282](file://app/backend/services/parser_service.py#L204-L282)
- [analyze.py:292-293](file://app/backend/routes/analyze.py#L292-L293)
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)
- [db_models.py:113](file://app/backend/models/db_models.py#L113)

### Correlation with Skill Development Patterns
While gap detection is date-centric, the hybrid pipeline correlates gaps with:
- Skills identified from resume text and job description.
- Education scoring and domain alignment.
- Total effective years computed from gap analysis and fallback inference.

This contextualization helps interpret gaps (e.g., short gaps during skill transitions) versus red flags (prolonged gaps without development).

**Section sources**
- [hybrid_pipeline.py:604-637](file://app/backend/services/hybrid_pipeline.py#L604-L637)
- [hybrid_pipeline.py:562-586](file://app/backend/services/hybrid_pipeline.py#L562-L586)

### Examples of Gap Detection Scenarios
- Moderate gap between jobs: detected and included in employment_gaps with severity label.
- Negligible gap (<3 months): classified as negligible and excluded from employment_gaps.
- Overlapping jobs: detected and reported as overlapping_jobs.
- Short stints: detected and reported as short_stints.
- Overlap-aware total experience: computed by merging overlapping intervals to avoid double counting.

Validation references:
- [test_gap_detector.py:166-175](file://app/backend/tests/test_gap_detector.py#L166-L175)
- [test_gap_detector.py:186-193](file://app/backend/tests/test_gap_detector.py#L186-L193)
- [test_gap_detector.py:226-232](file://app/backend/tests/test_gap_detector.py#L226-L232)
- [test_gap_detector.py:244-256](file://app/backend/tests/test_gap_detector.py#L244-L256)

**Section sources**
- [test_gap_detector.py:166-204](file://app/backend/tests/test_gap_detector.py#L166-L204)
- [test_gap_detector.py:226-266](file://app/backend/tests/test_gap_detector.py#L226-L266)

### False Positive Reduction Techniques
- Threshold-based exclusion: gaps <3 months are negligible and excluded from employment_gaps.
- Overlap-aware total experience: prevents double-counting when jobs overlap.
- Robust date normalization: handles fuzzy formats and international variants.
- Timeline sorting: ensures chronological correctness before gap computation.

**Section sources**
- [gap_detector.py:70-78](file://app/backend/services/gap_detector.py#L70-L78)
- [gap_detector.py:83-98](file://app/backend/services/gap_detector.py#L83-L98)
- [gap_detector.py:27-51](file://app/backend/services/gap_detector.py#L27-L51)

### Confidence Scoring and Narrative Interpretation
Gap analysis feeds metrics to the LLM:
- skill_match_percent
- total_years (from gap analysis)
- gaps (list of gaps)
- risks (risk signals from gap analysis + LLM)

The LLM generates a narrative with fit_score, strengths, weaknesses, and risk_signals. Gap analysis contributes to risk assessment by flagging overlaps, short stints, and long gaps.

**Section sources**
- [analysis_service.py:10-53](file://app/backend/services/analysis_service.py#L10-L53)
- [llm_service.py:139-156](file://app/backend/services/llm_service.py#L139-L156)

## Dependency Analysis
The gap detection module is designed to be standalone and date-focused. It depends on:
- Standard libraries for date/time manipulation and string parsing.
- No external LLM dependencies, keeping gap detection deterministic and fast.

Integration points:
- Routes call GapDetector after parsing.
- AnalysisService composes risk signals from gap analysis.
- Hybrid pipeline uses gap-derived total_years for scoring.

```mermaid
graph TB
GD["GapDetector"] --> |date parsing| DT["datetime/dateutil"]
GD --> |relativedelta| RD["relativedelta"]
GD --> |tests| T["pytest"]
Route["Routes"] --> GD
Analysis["AnalysisService"] --> GD
Hybrid["Hybrid Pipeline"] --> GD
```

**Diagram sources**
- [gap_detector.py:12-15](file://app/backend/services/gap_detector.py#L12-L15)
- [analyze.py:33](file://app/backend/routes/analyze.py#L33)
- [analysis_service.py:3](file://app/backend/services/analysis_service.py#L3)
- [hybrid_pipeline.py:616](file://app/backend/services/hybrid_pipeline.py#L616)

**Section sources**
- [gap_detector.py:12-22](file://app/backend/services/gap_detector.py#L12-L22)
- [analyze.py:33](file://app/backend/routes/analyze.py#L33)
- [analysis_service.py:3](file://app/backend/services/analysis_service.py#L3)
- [hybrid_pipeline.py:616](file://app/backend/services/hybrid_pipeline.py#L616)

## Performance Considerations
- Gap detection is O(n log n) due to sorting jobs and O(n) for gap computation and interval merging.
- Date normalization uses efficient regex and parsing libraries; fallbacks minimize overhead.
- Overlap-aware total experience avoids expensive double-counting by merging intervals once.
- Integration with resume parsing and hybrid pipeline is streamlined to reduce redundant computations.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Unparseable dates: Ensure date strings conform to recognized patterns or include “present” variants.
- Overlapping jobs misreported: Verify job intervals and confirm normalization to YYYY-MM.
- Short stints not detected: Confirm job durations are below 6 months and start dates are present.
- Total years incorrect: Check for overlapping jobs; interval merging should prevent double counting.
- LLM errors: Review fallback responses and ensure gap analysis keys are present.

**Section sources**
- [test_gap_detector.py:27-58](file://app/backend/tests/test_gap_detector.py#L27-L58)
- [test_gap_detector.py:244-256](file://app/backend/tests/test_gap_detector.py#L244-L256)
- [llm_service.py:128-136](file://app/backend/services/llm_service.py#L128-L136)

## Conclusion
The employment gap detection algorithm provides a robust, deterministic foundation for identifying gaps and transitions in candidate work histories. By combining date normalization, interval merging, and severity classification, it enables precise risk signals that complement LLM-driven narratives. The integration with resume parsing, hybrid scoring, and persistent storage ensures consistent, reusable insights for candidate evaluation and risk assessment.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Gap Detection Output Schema
- employment_timeline: list of jobs with from/to, duration_months, gap_after_months, gap_severity.
- employment_gaps: list of gaps ≥3 months with start_date, end_date, duration_months, severity.
- overlapping_jobs: list of overlapping job pairs with type and descriptions.
- short_stints: list of roles with tenure <6 months.
- total_years: overlap-aware total experience in years.

**Section sources**
- [gap_detector.py:104-214](file://app/backend/services/gap_detector.py#L104-L214)

### Storage of Gap Analysis
Gap analysis results are persisted in Candidate.gap_analysis_json for reuse across analyses and profile updates.

**Section sources**
- [analyze.py:118-145](file://app/backend/routes/analyze.py#L118-L145)
- [db_models.py:113](file://app/backend/models/db_models.py#L113)