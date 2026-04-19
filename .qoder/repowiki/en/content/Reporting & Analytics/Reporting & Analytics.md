# Reporting & Analytics

<cite>
**Referenced Files in This Document**
- [Dashboard.jsx](file://app/frontend/src/pages/Dashboard.jsx)
- [DashboardNew.jsx](file://app/frontend/src/pages/DashboardNew.jsx)
- [ComparePage.jsx](file://app/frontend/src/pages/ComparePage.jsx)
- [ReportPage.jsx](file://app/frontend/src/pages/ReportPage.jsx)
- [SkillsRadar.jsx](file://app/frontend/src/components/SkillsRadar.jsx)
- [Timeline.jsx](file://app/frontend/src/components/Timeline.jsx)
- [ScoreGauge.jsx](file://app/frontend/src/components/ScoreGauge.jsx)
- [ResultCard.jsx](file://app/frontend/src/components/ResultCard.jsx)
- [api.js](file://app/frontend/src/lib/api.js)
- [analyze.py](file://app/backend/routes/analyze.py)
- [compare.py](file://app/backend/routes/compare.py)
- [export.py](file://app/backend/routes/export.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [analysis_service.py](file://app/backend/services/analysis_service.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced PDF generation capabilities with direct PDF download functionality
- Added contact information headers to report pages with dual display modes
- Integrated narrative enhancement status indicators with polling mechanisms
- Improved dashboard components with new usage statistics and quick access features
- Added comprehensive narrative integration with AI enhancement status tracking

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
This document describes the reporting and analytics capabilities of Resume AI by ThetaLogics. It covers the dashboard components, score visualization techniques, interactive charts, comparison functionality, skills radar, timeline components, progress indicators, export capabilities, customization options, and performance considerations for large datasets and real-time updates.

**Updated** Enhanced with new PDF generation capabilities including direct PDF download, contact information headers, and narrative integration with AI enhancement status tracking.

## Project Structure
The analytics and reporting features span the frontend React application and the backend FastAPI service:
- Frontend pages and components render results, comparisons, and interactive visualizations with PDF generation support.
- Backend routes orchestrate analysis, comparison, and exports, persisting results to the database.
- Services implement the hybrid analysis pipeline and scoring logic with narrative enhancement capabilities.

```mermaid
graph TB
subgraph "Frontend"
D["Dashboard.jsx"]
DN["DashboardNew.jsx"]
R["ReportPage.jsx"]
C["ComparePage.jsx"]
RC["ResultCard.jsx"]
SR["SkillsRadar.jsx"]
TL["Timeline.jsx"]
SG["ScoreGauge.jsx"]
API["api.js"]
PDF["PDF Generation<br/>html2pdf.js"]
ENDPOINT["Narrative Endpoint<br/>/analysis/{id}/narrative"]
end
subgraph "Backend"
A["routes/analyze.py"]
CMP["routes/compare.py"]
EXP["routes/export.py"]
MODELS["models/db_models.py"]
SVC["services/analysis_service.py"]
HP["services/hybrid_pipeline.py"]
NARRATIVE["Narrative Service"]
end
D --> API
DN --> API
R --> API
R --> PDF
R --> ENDPOINT
C --> API
RC --> SR
RC --> TL
RC --> SG
API --> A
API --> CMP
API --> EXP
A --> SVC
A --> HP
A --> NARRATIVE
CMP --> MODELS
EXP --> MODELS
```

**Diagram sources**
- [Dashboard.jsx:1-330](file://app/frontend/src/pages/Dashboard.jsx#L1-330)
- [DashboardNew.jsx:1-336](file://app/frontend/src/pages/DashboardNew.jsx#L1-336)
- [ReportPage.jsx:1-514](file://app/frontend/src/pages/ReportPage.jsx#L1-514)
- [ComparePage.jsx:1-230](file://app/frontend/src/pages/ComparePage.jsx#L1-230)
- [ResultCard.jsx:1-836](file://app/frontend/src/components/ResultCard.jsx#L1-836)
- [SkillsRadar.jsx:1-261](file://app/frontend/src/components/SkillsRadar.jsx#L1-261)
- [Timeline.jsx:1-115](file://app/frontend/src/components/Timeline.jsx#L1-115)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-97)
- [api.js:1-701](file://app/frontend/src/lib/api.js#L1-701)
- [analyze.py:1-1169](file://app/backend/routes/analyze.py#L1-1169)
- [compare.py:1-78](file://app/backend/routes/compare.py#L1-78)
- [export.py:1-105](file://app/backend/routes/export.py#L1-105)
- [db_models.py:1-250](file://app/backend/models/db_models.py#L1-250)
- [analysis_service.py:1-121](file://app/backend/services/analysis_service.py#L1-121)
- [hybrid_pipeline.py:1-200](file://app/backend/services/hybrid_pipeline.py#L1-200)

**Section sources**
- [Dashboard.jsx:1-330](file://app/frontend/src/pages/Dashboard.jsx#L1-330)
- [DashboardNew.jsx:1-336](file://app/frontend/src/pages/DashboardNew.jsx#L1-336)
- [ReportPage.jsx:1-514](file://app/frontend/src/pages/ReportPage.jsx#L1-514)
- [ComparePage.jsx:1-230](file://app/frontend/src/pages/ComparePage.jsx#L1-230)
- [ResultCard.jsx:1-836](file://app/frontend/src/components/ResultCard.jsx#L1-836)
- [SkillsRadar.jsx:1-261](file://app/frontend/src/components/SkillsRadar.jsx#L1-261)
- [Timeline.jsx:1-115](file://app/frontend/src/components/Timeline.jsx#L1-115)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-97)
- [api.js:1-701](file://app/frontend/src/lib/api.js#L1-701)
- [analyze.py:1-1169](file://app/backend/routes/analyze.py#L1-1169)
- [compare.py:1-78](file://app/backend/routes/compare.py#L1-78)
- [export.py:1-105](file://app/backend/routes/export.py#L1-105)
- [db_models.py:1-250](file://app/backend/models/db_models.py#L1-250)
- [analysis_service.py:1-121](file://app/backend/services/analysis_service.py#L1-121)
- [hybrid_pipeline.py:1-200](file://app/backend/services/hybrid_pipeline.py#L1-200)

## Core Components
- Dashboard: Presents the analysis pipeline progress, usage widget, and submission controls with enhanced statistics.
- DashboardNew: New dashboard with comprehensive usage analytics, recent analyses grid, and quick access features.
- Report Page: Renders the candidate report with score visualization, explainability, skills radar, timeline, contact information headers, and PDF download functionality.
- Compare Page: Compares up to five candidates side-by-side with score breakdowns and export.
- ResultCard: Aggregates analysis results, score breakdowns, strengths/weaknesses, risk signals, explainability, education analysis, domain fit, and interview kit with narrative integration.
- SkillsRadar: Visualizes matched vs missing skills by category with coverage metrics and bar chart.
- Timeline: Displays employment history with gaps and severity.
- ScoreGauge: Circular score visualization with thresholds and status badges.
- API client: Wraps HTTP requests to backend endpoints for analysis, comparison, exports, and narrative polling.
- PDF Generation: Direct PDF download functionality using html2pdf.js with customizable options.

**Updated** Added comprehensive PDF generation capabilities, contact information headers, and narrative enhancement status tracking.

**Section sources**
- [Dashboard.jsx:161-330](file://app/frontend/src/pages/Dashboard.jsx#L161-330)
- [DashboardNew.jsx:56-336](file://app/frontend/src/pages/DashboardNew.jsx#L56-336)
- [ReportPage.jsx:82-514](file://app/frontend/src/pages/ReportPage.jsx#L82-514)
- [ComparePage.jsx:20-230](file://app/frontend/src/pages/ComparePage.jsx#L20-230)
- [ResultCard.jsx:265-836](file://app/frontend/src/components/ResultCard.jsx#L265-836)
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-261)
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-115)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-97)
- [api.js:47-701](file://app/frontend/src/lib/api.js#L47-701)

## Architecture Overview
The system streams analysis results from the backend to the frontend, persists results to the database, supports batch operations, exports, and includes advanced PDF generation capabilities with narrative integration.

```mermaid
sequenceDiagram
participant U as "User"
participant FE as "Frontend Pages<br/>Dashboard/Report/Compare"
participant API as "Frontend API<br/>api.js"
participant BE as "Backend Routes<br/>analyze.py/compare.py/export.py"
participant PDF as "PDF Engine<br/>html2pdf.js"
participant DB as "Database Models<br/>db_models.py"
U->>FE : "Submit resume + job description"
FE->>API : "analyzeResumeStream()"
API->>BE : "POST /analyze/stream"
BE->>BE : "run_hybrid_pipeline()"
BE-->>API : "SSE events (stages)"
API-->>FE : "Stage callbacks"
BE->>DB : "Persist ScreeningResult/Candidate"
FE->>API : "Navigate to /report"
API->>BE : "GET /history or fetch result"
BE-->>API : "Result payload"
API-->>FE : "Render ReportPage"
FE->>API : "Poll narrative status"
API->>BE : "GET /analysis/{id}/narrative"
BE-->>API : "Narrative status/data"
API-->>FE : "Update UI with AI enhancement"
FE->>API : "handleDownload()"
API->>PDF : "html2pdf().set(options)"
PDF-->>FE : "Generate PDF"
FE->>FE : "Trigger download"
U->>FE : "Compare candidates"
FE->>API : "compareResults()"
API->>BE : "POST /compare"
BE->>DB : "Query ScreeningResult"
BE-->>API : "Comparison payload"
API-->>FE : "Render ComparePage"
U->>FE : "Export CSV/Excel"
FE->>API : "exportCsv()/exportExcel()"
API->>BE : "GET /export/csv or /export/excel"
BE->>DB : "Fetch results"
BE-->>API : "Streaming CSV/XLSX"
API-->>FE : "Trigger download"
```

**Diagram sources**
- [api.js:75-147](file://app/frontend/src/lib/api.js#L75-147)
- [ReportPage.jsx:216-256](file://app/frontend/src/pages/ReportPage.jsx#L216-256)
- [ReportPage.jsx:127-195](file://app/frontend/src/pages/ReportPage.jsx#L127-195)
- [api.js:627-631](file://app/frontend/src/lib/api.js#L627-631)
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-646)
- [compare.py:16-78](file://app/backend/routes/compare.py#L16-78)
- [export.py:55-105](file://app/backend/routes/export.py#L55-105)
- [db_models.py:128-147](file://app/backend/models/db_models.py#L128-147)

## Detailed Component Analysis

### Dashboard: Enhanced Usage Statistics and Quick Access
- Tracks pipeline stages and derives active stages based on completion.
- Shows comprehensive usage widget with unlimited plan support and progress visualization.
- Provides quick access to recent analyses and saved job descriptions.
- Includes feature highlights with AI-powered analysis capabilities.

**Updated** Enhanced with new DashboardNew component featuring comprehensive usage analytics, recent analyses grid, and quick access to saved job descriptions.

```mermaid
flowchart TD
Start(["User accesses dashboard"]) --> Usage["Display usage stats<br/>Monthly limit + progress"]
Usage --> Recent["Show recent analyses grid<br/>5 most recent results"]
Recent --> QuickAccess["Quick access to saved JDs<br/>Top 3 templates"]
QuickAccess --> Features["Feature highlights<br/>AI weight suggestions,<br/>Batch processing,<br/>Version history"]
Features --> Actions["CTA buttons<br/>New analysis,<br/>View all candidates,<br/>JD library"]
```

**Diagram sources**
- [DashboardNew.jsx:56-336](file://app/frontend/src/pages/DashboardNew.jsx#L56-336)

**Section sources**
- [Dashboard.jsx:161-330](file://app/frontend/src/pages/Dashboard.jsx#L161-330)
- [DashboardNew.jsx:56-336](file://app/frontend/src/pages/DashboardNew.jsx#L56-336)

### Report Page: Comprehensive PDF Generation and Contact Information
- Displays a ScoreGauge with thresholds and recommendation badge.
- Renders ResultCard with score breakdown bars, strengths/weaknesses, risk signals, explainability, education analysis, domain fit, and interview kit.
- Provides share and PDF download actions with comprehensive contact information headers.
- Integrates SkillsRadar and Timeline components with narrative enhancement status tracking.

**Updated** Enhanced with direct PDF download functionality using html2pdf.js, comprehensive contact information headers visible in both screen and print modes, and narrative enhancement status indicators.

```mermaid
classDiagram
class ReportPage {
+render()
+handleShare()
+handleDownload()
+narrativePolling
}
class ScoreGauge {
+score
}
class ResultCard {
+result
+defaultExpandEducation
+narrativeData
}
class SkillsRadar
class Timeline
class PDFGenerator {
+html2pdf()
+options
+download()
}
ReportPage --> ScoreGauge : "renders"
ReportPage --> ResultCard : "renders"
ReportPage --> PDFGenerator : "uses"
ResultCard --> SkillsRadar : "uses"
ReportPage --> Timeline : "renders"
```

**Diagram sources**
- [ReportPage.jsx:82-514](file://app/frontend/src/pages/ReportPage.jsx#L82-514)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-97)
- [ResultCard.jsx:265-836](file://app/frontend/src/components/ResultCard.jsx#L265-836)
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-261)
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-115)

**Section sources**
- [ReportPage.jsx:82-514](file://app/frontend/src/pages/ReportPage.jsx#L82-514)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-97)
- [ResultCard.jsx:265-836](file://app/frontend/src/components/ResultCard.jsx#L265-836)

### Compare Page: Side-by-Side Evaluation
- Allows selection of 2–5 candidates from history.
- Calls compare endpoint to compute winners per category and renders a comparison table with scores and recommendations.

```mermaid
sequenceDiagram
participant U as "User"
participant CP as "ComparePage"
participant API as "api.js"
participant CMP as "compare.py"
participant DB as "db_models.py"
U->>CP : "Select candidate IDs"
CP->>API : "compareResults(ids)"
API->>CMP : "POST /compare"
CMP->>DB : "Query ScreeningResult by IDs"
DB-->>CMP : "Results"
CMP-->>API : "Comparison payload"
API-->>CP : "Render comparison table"
U->>CP : "Export CSV"
CP->>API : "exportCsv(selected)"
API->>EXP : "GET /export/csv"
EXP->>DB : "Fetch filtered results"
EXP-->>API : "CSV stream"
API-->>CP : "Trigger download"
```

**Diagram sources**
- [ComparePage.jsx:20-230](file://app/frontend/src/pages/ComparePage.jsx#L20-230)
- [api.js:176-204](file://app/frontend/src/lib/api.js#L176-204)
- [compare.py:16-78](file://app/backend/routes/compare.py#L16-78)
- [export.py:55-105](file://app/backend/routes/export.py#L55-105)
- [db_models.py:128-147](file://app/backend/models/db_models.py#L128-147)

**Section sources**
- [ComparePage.jsx:20-230](file://app/frontend/src/pages/ComparePage.jsx#L20-230)
- [api.js:176-204](file://app/frontend/src/lib/api.js#L176-204)
- [compare.py:16-78](file://app/backend/routes/compare.py#L16-78)
- [export.py:55-105](file://app/backend/routes/export.py#L55-105)

### Skills Radar: Category-Based Gap Analysis
- Categorizes skills and computes matched vs missing counts per category.
- Shows overall match percentage with circular progress and a vertical bar chart.
- Displays skill chips per category with distinct colors.

```mermaid
flowchart TD
Input["matchedSkills, missingSkills"] --> Categorize["Categorize skills"]
Categorize --> Tally["Tally per category"]
Tally --> Sort["Sort by total desc"]
Sort --> Metrics["Compute match percentage"]
Metrics --> Render["Render circular progress + bar chart + chips"]
```

**Diagram sources**
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-261)

**Section sources**
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-261)

### Timeline: Employment History and Gaps
- Sorts jobs by start date and renders a vertical timeline.
- Highlights short tenures and displays gaps with duration and severity.

```mermaid
flowchart TD
Jobs["workExperience"] --> Sort["Sort by start_date desc"]
Sort --> Render["Render timeline entries"]
Render --> Gaps["Render gaps with severity"]
```

**Diagram sources**
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-115)

**Section sources**
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-115)

### Score Gauge: Threshold-Based Visualization
- Visualizes fit score with color-coded arcs and labels.
- Handles pending state when score is unavailable.

```mermaid
flowchart TD
Score["fit_score"] --> Check{"isPending?"}
Check --> |Yes| Pending["Show pending UI"]
Check --> |No| Color["Map score to color/label"]
Color --> Arc["Draw arc with offset"]
```

**Diagram sources**
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-97)

**Section sources**
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-97)

### ResultCard: Comprehensive Analysis Display with Narrative Integration
- Renders score breakdown bars, strengths/weaknesses, risk signals, explainability, education analysis, domain fit, and interview kit tabs.
- Integrates SkillsRadar and Timeline for deeper insights.
- Includes narrative enhancement status indicators and error handling.
- Provides analysis source badges and quality indicators.

**Updated** Enhanced with comprehensive narrative integration, analysis source badges, quality indicators, and error handling for AI enhancement failures.

```mermaid
classDiagram
class ResultCard {
+score_breakdown
+interview_questions
+explainability
+education_analysis
+risk_signals
+narrativeData
+aiEnhanced
+narrativeError
}
ResultCard --> SkillsRadar : "renders"
ResultCard --> Timeline : "renders"
ResultCard --> AnalysisSourceBadge : "displays"
ResultCard --> PendingBanner : "shows"
ResultCard --> NarrativeErrorBanner : "handles"
```

**Diagram sources**
- [ResultCard.jsx:265-836](file://app/frontend/src/components/ResultCard.jsx#L265-836)
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-261)
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-115)

**Section sources**
- [ResultCard.jsx:265-836](file://app/frontend/src/components/ResultCard.jsx#L265-836)

### Backend Analysis Pipeline
- Hybrid pipeline: Python-first scoring and a single LLM call for narrative.
- Supports streaming SSE events and fallbacks when LLM is unavailable.
- Deduplicates candidates and stores enriched profiles for reuse.
- Provides narrative enhancement endpoint with status tracking.

**Updated** Enhanced with narrative enhancement capabilities and status tracking endpoints.

```mermaid
sequenceDiagram
participant BE as "analyze.py"
participant HP as "hybrid_pipeline.py"
participant SVC as "analysis_service.py"
participant DB as "db_models.py"
BE->>HP : "run_hybrid_pipeline()"
HP->>HP : "Phase 1 (Python) : parse + match + score"
HP->>SVC : "Phase 2 (LLM) : analyze_with_llm()"
SVC-->>HP : "Narrative + strengths/weaknesses"
HP-->>BE : "Final result"
BE->>DB : "Persist ScreeningResult + Candidate"
BE->>BE : "Store narrative data"
```

**Diagram sources**
- [analyze.py:268-318](file://app/backend/routes/analyze.py#L268-318)
- [hybrid_pipeline.py:1-200](file://app/backend/services/hybrid_pipeline.py#L1-200)
- [analysis_service.py:10-53](file://app/backend/services/analysis_service.py#L10-53)
- [db_models.py:128-147](file://app/backend/models/db_models.py#L128-147)

**Section sources**
- [analyze.py:268-318](file://app/backend/routes/analyze.py#L268-318)
- [hybrid_pipeline.py:1-200](file://app/backend/services/hybrid_pipeline.py#L1-200)
- [analysis_service.py:10-53](file://app/backend/services/analysis_service.py#L10-53)
- [db_models.py:128-147](file://app/backend/models/db_models.py#L128-147)

## Dependency Analysis
- Frontend depends on API client for all backend interactions including PDF generation and narrative polling.
- Backend routes depend on SQLAlchemy models and services including narrative enhancement.
- Analysis pipeline integrates Python scoring and LLM reasoning with PDF generation support.

**Updated** Enhanced with PDF generation dependencies and narrative enhancement dependencies.

```mermaid
graph LR
FE["Frontend Pages/Components"] --> API["api.js"]
API --> ROUTES["analyze.py / compare.py / export.py"]
ROUTES --> MODELS["db_models.py"]
ROUTES --> SERVICES["analysis_service.py / hybrid_pipeline.py"]
SERVICES --> PDF["PDF Generation<br/>html2pdf.js"]
SERVICES --> NARRATIVE["Narrative Enhancement"]
```

**Diagram sources**
- [api.js:1-701](file://app/frontend/src/lib/api.js#L1-701)
- [analyze.py:1-1169](file://app/backend/routes/analyze.py#L1-1169)
- [compare.py:1-78](file://app/backend/routes/compare.py#L1-78)
- [export.py:1-105](file://app/backend/routes/export.py#L1-105)
- [db_models.py:1-250](file://app/backend/models/db_models.py#L1-250)
- [analysis_service.py:1-121](file://app/backend/services/analysis_service.py#L1-121)
- [hybrid_pipeline.py:1-200](file://app/backend/services/hybrid_pipeline.py#L1-200)

**Section sources**
- [api.js:1-701](file://app/frontend/src/lib/api.js#L1-701)
- [analyze.py:1-1169](file://app/backend/routes/analyze.py#L1-1169)
- [compare.py:1-78](file://app/backend/routes/compare.py#L1-78)
- [export.py:1-105](file://app/backend/routes/export.py#L1-105)
- [db_models.py:1-250](file://app/backend/models/db_models.py#L1-250)
- [analysis_service.py:1-121](file://app/backend/services/analysis_service.py#L1-121)
- [hybrid_pipeline.py:1-200](file://app/backend/services/hybrid_pipeline.py#L1-200)

## Performance Considerations
- Streaming: The frontend receives incremental updates via SSE, enabling responsive UI during long-running analysis.
- Concurrency: LLM semaphore limits concurrent reasoning calls to maintain stability.
- Background processing: Long-running tasks offload parsing and scoring to threads to avoid blocking the event loop.
- Caching: Job description parsing is cached per hash to reduce repeated work across requests and workers.
- Pagination and limits: History and batch sizes are constrained by subscription plans to prevent overload.
- PDF Generation: Optimized with html2pdf.js using appropriate scaling and CORS settings for efficient rendering.
- Narrative Polling: Adaptive polling with exponential backoff for AI enhancement status tracking.

**Updated** Enhanced with PDF generation optimization and narrative polling performance considerations.

## Troubleshooting Guide
- Ollama/LangChain unavailability: The system falls back to Python-only scores and deterministic narrative; UI indicates "LLM offline".
- Usage limits: Exceeding monthly quotas triggers a 429 response; the frontend should surface actionable messages.
- Network errors: The API client retries unauthorized requests with token refresh and redirects to login when needed.
- Large files: Backend enforces size limits for resumes and job description files.
- PDF Generation Errors: html2pdf.js may fail due to complex CSS or CORS issues; provides fallback to browser print option.
- Narrative Enhancement Failures: Automatic fallback to standard analysis with error banners and status indicators.
- Contact Information Display: Dual display modes ensure contact info visibility in both screen and print contexts.

**Updated** Enhanced with PDF generation troubleshooting, narrative enhancement failure handling, and contact information display considerations.

**Section sources**
- [ReportPage.jsx:187-197](file://app/frontend/src/pages/ReportPage.jsx#L187-197)
- [ReportPage.jsx:250-256](file://app/frontend/src/pages/ReportPage.jsx#L250-256)
- [ReportPage.jsx:452-468](file://app/frontend/src/pages/ReportPage.jsx#L452-468)
- [api.js:19-43](file://app/frontend/src/lib/api.js#L19-43)
- [analyze.py:364-367](file://app/backend/routes/analyze.py#L364-367)
- [analyze.py:373-380](file://app/backend/routes/analyze.py#L373-380)

## Conclusion
Resume AI provides a robust analytics and reporting system with real-time progress, rich visualizations, export capabilities, and comprehensive PDF generation. The hybrid pipeline ensures reliable scoring even without LLM availability, while the frontend components deliver clear insights through gauges, radar charts, timelines, and explainability. The enhanced dashboard components provide better usage analytics and quick access to key features, while the PDF generation capabilities enable direct report downloads with professional formatting.

**Updated** Enhanced conclusion reflecting new PDF generation capabilities, comprehensive dashboard features, and improved narrative integration.

## Appendices

### Export Capabilities
- CSV: Endpoint returns a streamed CSV file with selected result IDs.
- Excel: Endpoint returns a streamed XLSX file with the same dataset.
- PDF: Direct PDF download functionality with html2pdf.js integration.

**Updated** Added PDF export capability with comprehensive formatting options.

**Section sources**
- [export.py:55-105](file://app/backend/routes/export.py#L55-105)
- [api.js:183-204](file://app/frontend/src/lib/api.js#L183-204)
- [ReportPage.jsx:216-256](file://app/frontend/src/pages/ReportPage.jsx#L216-256)

### Customization Options
- Scoring weights: Provided during analysis to influence score breakdown.
- Candidate name editing: Inline editor in the report page.
- Template-based emails: Email generation integrated via backend templates.
- PDF Options: Customizable margins, filename, image quality, and jsPDF settings.
- Contact Information: Dual display modes for screen and print contexts.

**Updated** Enhanced with PDF customization options and contact information display modes.

**Section sources**
- [Dashboard.jsx:212-212](file://app/frontend/src/pages/Dashboard.jsx#L212-212)
- [ReportPage.jsx:12-80](file://app/frontend/src/pages/ReportPage.jsx#L12-80)
- [ReportPage.jsx:229-246](file://app/frontend/src/pages/ReportPage.jsx#L229-246)
- [ReportPage.jsx:452-468](file://app/frontend/src/pages/ReportPage.jsx#L452-468)
- [api.js:239-242](file://app/frontend/src/lib/api.js#L239-242)

### Extending Analytics Features
- Add new visualization components by composing existing building blocks (e.g., integrate a new chart in ResultCard).
- Extend backend services to compute additional metrics and expose them via the analysis pipeline.
- Introduce new export formats by adding endpoints similar to CSV/Excel.
- Implement additional PDF generation options with custom styling and layout configurations.
- Add new dashboard widgets for enhanced analytics and usage tracking.

**Updated** Enhanced with PDF generation extension possibilities and dashboard widget additions.

### PDF Generation Configuration
- html2pdf.js options include margin, filename, image quality, scaling, and page breaks.
- Supports A4 portrait format with CSS-based page breaks.
- Integrates with report content element for seamless PDF generation.
- Provides fallback to browser print option for error scenarios.

**Section sources**
- [ReportPage.jsx:229-246](file://app/frontend/src/pages/ReportPage.jsx#L229-246)
- [ReportPage.jsx:249-256](file://app/frontend/src/pages/ReportPage.jsx#L249-256)

### Narrative Enhancement Integration
- Real-time polling for AI-enhanced narratives with adaptive delays.
- Status indicators for pending, processing, ready, and failed states.
- Fallback mechanisms for standard analysis when AI enhancement fails.
- Integration with ResultCard for comprehensive analysis presentation.

**Section sources**
- [ReportPage.jsx:127-195](file://app/frontend/src/pages/ReportPage.jsx#L127-195)
- [ResultCard.jsx:299-373](file://app/frontend/src/components/ResultCard.jsx#L299-373)
- [api.js:627-631](file://app/frontend/src/lib/api.js#L627-631)