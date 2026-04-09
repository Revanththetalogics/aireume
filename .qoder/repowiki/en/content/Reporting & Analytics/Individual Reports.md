# Individual Reports

<cite>
**Referenced Files in This Document**
- [ReportPage.jsx](file://app/frontend/src/pages/ReportPage.jsx)
- [ResultCard.jsx](file://app/frontend/src/components/ResultCard.jsx)
- [ScoreGauge.jsx](file://app/frontend/src/components/ScoreGauge.jsx)
- [SkillsRadar.jsx](file://app/frontend/src/components/SkillsRadar.jsx)
- [Timeline.jsx](file://app/frontend/src/components/Timeline.jsx)
- [api.js](file://app/frontend/src/lib/api.js)
- [index.css](file://app/frontend/src/index.css)
- [CandidatesPage.jsx](file://app/frontend/src/pages/CandidatesPage.jsx)
- [export.py](file://app/backend/routes/export.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [email_gen.py](file://app/backend/routes/email_gen.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [llm_service.py](file://app/backend/services/llm_service.py)
- [analysis_service.py](file://app/backend/services/analysis_service.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced Analysis Source Badge system with AI Enhanced Report vs Analysis complete distinction
- Added AI enhancement flag propagation through the entire analysis pipeline
- Updated frontend badge rendering to differentiate between AI-generated and fallback narratives
- Integrated backend flagging system for consistent identification across frontend and backend

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
This document explains the end-to-end individual report generation and display system in Resume AI by ThetaLogics. It focuses on:
- The ReportPage component for comprehensive candidate analysis reports
- Inline name editor functionality
- Sharing mechanisms and PDF download capabilities
- The ResultCard component for detailed analysis presentation with expandable sections
- The ScoreGauge component for visual fit score representation and recommendation display
- **Enhanced narrative distinction system** with AI Enhanced Report vs Analysis complete badges
- Customization options for report layouts, branding integration, print optimization, and export formats (CSV and Excel)

## Project Structure
The reporting system spans frontend React components and backend FastAPI routes:
- Frontend pages and components render the report UI, manage user interactions, and trigger exports
- Backend routes handle analysis, email generation, and export generation
- Styling and print optimization are centralized in Tailwind CSS and media queries
- **Enhanced backend services now propagate AI enhancement flags** through the entire analysis pipeline

```mermaid
graph TB
subgraph "Frontend"
RP["ReportPage.jsx"]
RC["ResultCard.jsx"]
SG["ScoreGauge.jsx"]
SR["SkillsRadar.jsx"]
TL["Timeline.jsx"]
API["api.js"]
CSS["index.css"]
end
subgraph "Backend"
AN["analyze.py"]
HP["hybrid_pipeline.py"]
LS["llm_service.py"]
AS["analysis_service.py"]
EX["export.py"]
EG["email_gen.py"]
end
RP --> RC
RP --> SG
RC --> SR
RC --> TL
RP --> API
RC --> API
API --> AN
AN --> HP
HP --> LS
AS --> LS
API --> EX
API --> EG
CSS --> RP
CSS --> RC
```

**Diagram sources**
- [ReportPage.jsx:82-296](file://app/frontend/src/pages/ReportPage.jsx#L82-L296)
- [ResultCard.jsx:265-626](file://app/frontend/src/components/ResultCard.jsx#L265-L626)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-L261)
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-L115)
- [api.js:1-395](file://app/frontend/src/lib/api.js#L1-L395)
- [index.css:136-160](file://app/frontend/src/index.css#L136-L160)
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [export.py:55-104](file://app/backend/routes/export.py#L55-L104)
- [email_gen.py:39-104](file://app/backend/routes/email_gen.py#L39-L104)
- [hybrid_pipeline.py:1322-1335](file://app/backend/services/hybrid_pipeline.py#L1322-L1335)
- [llm_service.py:256-273](file://app/backend/services/llm_service.py#L256-L273)

**Section sources**
- [ReportPage.jsx:82-296](file://app/frontend/src/pages/ReportPage.jsx#L82-L296)
- [ResultCard.jsx:265-626](file://app/frontend/src/components/ResultCard.jsx#L265-L626)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-L261)
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-L115)
- [api.js:1-395](file://app/frontend/src/lib/api.js#L1-L395)
- [index.css:136-160](file://app/frontend/src/index.css#L136-L160)
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [export.py:55-104](file://app/backend/routes/export.py#L55-L104)
- [email_gen.py:39-104](file://app/backend/routes/email_gen.py#L39-L104)

## Core Components
- ReportPage: Orchestrates the report UI, inline name editing, sharing, and PDF printing
- ResultCard: Presents analysis results with collapsible sections, email generation, and interview kit
- ScoreGauge: Visualizes fit score thresholds and recommendation
- SkillsRadar: Displays skills coverage and category breakdown
- Timeline: Renders employment history and gaps
- api.js: Provides functions for analysis, exports, and email generation
- index.css: Defines print and branding styles
- **Enhanced Analysis Source Badge System**: Distinguishes between AI Enhanced Report and Analysis complete narratives

**Section sources**
- [ReportPage.jsx:82-296](file://app/frontend/src/pages/ReportPage.jsx#L82-L296)
- [ResultCard.jsx:265-626](file://app/frontend/src/components/ResultCard.jsx#L265-L626)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-L261)
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-L115)
- [api.js:183-204](file://app/frontend/src/lib/api.js#L183-L204)
- [index.css:136-160](file://app/frontend/src/index.css#L136-L160)

## Architecture Overview
The report rendering pipeline integrates frontend and backend with enhanced AI distinction:
- Frontend loads a result (via route state or session storage) and renders ReportPage
- ReportPage delegates analysis display to ResultCard and ScoreGauge
- Timeline visualizes work experience and gaps
- **Enhanced Analysis Source Badge System** differentiates AI-generated vs fallback narratives
- Sharing uses client-side session storage to generate a shareable URL
- PDF download triggers the browser's print dialog
- Exports (CSV/Excel) are generated server-side and downloaded client-side

```mermaid
sequenceDiagram
participant User as "User"
participant RP as "ReportPage"
participant RC as "ResultCard"
participant SG as "ScoreGauge"
participant TL as "Timeline"
participant API as "api.js"
participant BE as "Backend Routes"
User->>RP : Open report page
RP->>RP : Load result from state/session
RP->>SG : Render fit score
RP->>RC : Render analysis sections
RC->>TL : Render timeline
RC->>RC : Check ai_enhanced flag
alt AI Enhanced Report
RC->>RC : Show "AI Enhanced Report" badge
else Analysis Complete
RC->>RC : Show "Analysis complete" badge
end
User->>RP : Click "Share"
RP->>RP : Store result in session<br/>Generate share URL
User->>RP : Click "Download PDF"
RP->>RP : window.print()
User->>API : Export CSV/Excel
API->>BE : GET /export/csv or /export/excel
BE-->>API : Streamed file
API-->>User : Trigger download
```

**Diagram sources**
- [ReportPage.jsx:82-296](file://app/frontend/src/pages/ReportPage.jsx#L82-L296)
- [ResultCard.jsx:265-626](file://app/frontend/src/components/ResultCard.jsx#L265-L626)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-L115)
- [api.js:183-204](file://app/frontend/src/lib/api.js#L183-L204)
- [export.py:55-104](file://app/backend/routes/export.py#L55-L104)

## Detailed Component Analysis

### ReportPage: Individual Report Container
Responsibilities:
- Resolve and persist the selected result
- Inline candidate name editor with persistence
- Share report via client-side session storage
- Trigger PDF printing
- Provide training labeling for outcomes
- **Display AI Enhancement Status Badge** based on ai_enhanced flag

Key behaviors:
- Loads result from route state or session storage keyed by a random ID
- Renders sidebar with score, recommendation, and labeling controls
- Renders sticky action bar with Share and Download PDF buttons
- **Shows AI Enhanced Report badge for ai_enhanced === true**
- **Shows Analysis complete badge for ai_enhanced === false**
- Prints a print-friendly header and delegates content to ResultCard and Timeline

```mermaid
flowchart TD
Start(["ReportPage mount"]) --> LoadResult["Load result from state or session"]
LoadResult --> HasResult{"Result present?"}
HasResult -- No --> Redirect["Redirect to home"]
HasResult -- Yes --> Render["Render sidebar + action bar + content"]
Render --> NameEditor["InlineNameEditor"]
Render --> Share["handleShare()"]
Render --> Download["handleDownload()"]
Render --> CheckAIEnhanced{"Check ai_enhanced flag"}
CheckAIEnhanced --> |true| AIEnhancedBadge["Show 'AI Enhanced Report' badge"]
CheckAIEnhanced --> |false| AnalysisCompleteBadge["Show 'Analysis complete' badge"]
Share --> SessionStore["sessionStorage.set(report_id, result)"]
Share --> Copy["navigator.clipboard.writeText(url)"]
Download --> Print["window.print()"]
```

**Diagram sources**
- [ReportPage.jsx:82-151](file://app/frontend/src/pages/ReportPage.jsx#L82-L151)
- [ReportPage.jsx:153-296](file://app/frontend/src/pages/ReportPage.jsx#L153-L296)
- [ReportPage.jsx:193-207](file://app/frontend/src/pages/ReportPage.jsx#L193-L207)

**Section sources**
- [ReportPage.jsx:82-151](file://app/frontend/src/pages/ReportPage.jsx#L82-L151)
- [ReportPage.jsx:153-296](file://app/frontend/src/pages/ReportPage.jsx#L153-L296)
- [ReportPage.jsx:193-207](file://app/frontend/src/pages/ReportPage.jsx#L193-L207)

### Inline Name Editor
- Toggles between display and edit modes
- Persists edits via PATCH to update candidate name
- Supports Enter to save and Escape to cancel
- Triggers parent callback to update local state

```mermaid
sequenceDiagram
participant User as "User"
participant Editor as "InlineNameEditor"
participant API as "api.js.updateCandidateName"
User->>Editor : Click pencil or Enter
Editor->>Editor : Focus input and show save/cancel
User->>Editor : Press Enter or click Save
Editor->>API : PATCH /candidates/{id}
API-->>Editor : Success
Editor-->>Parent : onSaved(trimmedName)
```

**Diagram sources**
- [ReportPage.jsx:12-80](file://app/frontend/src/pages/ReportPage.jsx#L12-L80)
- [api.js:239-242](file://app/frontend/src/lib/api.js#L239-L242)

**Section sources**
- [ReportPage.jsx:12-80](file://app/frontend/src/pages/ReportPage.jsx#L12-L80)
- [api.js:239-242](file://app/frontend/src/lib/api.js#L239-L242)

### ResultCard: Detailed Analysis Presentation
Highlights:
- Recommendation badge and risk indicator
- **Enhanced Analysis Source Badge** indicating AI Enhanced Report vs Analysis complete
- Score breakdown bars
- Skills matched/missing and adjacent skills
- Skills radar visualization
- Strengths, weaknesses, risk signals
- Explainability rationale
- Education and domain-fit sections
- Interview kit tabs (Technical, Behavioral, Culture Fit)
- Email generation modal

Expandable sections:
- Education Analysis
- Domain Fit & Architecture Assessment
- Explainability
- Interview Kit

```mermaid
classDiagram
class ResultCard {
+props.result
+props.defaultExpandEducation
+render()
}
class AnalysisSourceBadge {
+props.narrativeReady
+props.isPolling
+props.analysisQuality
+props.aiEnhanced
+render()
}
class SkillsRadar {
+props.matchedSkills
+props.missingSkills
+render()
}
class EmailModal {
+props.candidateId
+props.resultId
+props.onClose
+render()
}
ResultCard --> AnalysisSourceBadge : "renders"
ResultCard --> SkillsRadar : "renders"
ResultCard --> EmailModal : "opens"
```

**Diagram sources**
- [ResultCard.jsx:265-626](file://app/frontend/src/components/ResultCard.jsx#L265-L626)
- [ResultCard.jsx:198-244](file://app/frontend/src/components/ResultCard.jsx#L198-L244)
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-L261)

**Section sources**
- [ResultCard.jsx:265-626](file://app/frontend/src/components/ResultCard.jsx#L265-L626)
- [ResultCard.jsx:198-244](file://app/frontend/src/components/ResultCard.jsx#L198-L244)

### Analysis Source Badge System
**Enhanced** - The Analysis Source Badge now provides clear distinction between AI-generated and fallback narratives:

- **AI Enhanced Report Badge** (ai_enhanced === true):
  - Green background with sparkles icon
  - Shows analysis quality rating (high/medium/low)
  - Indicates real LLM-generated narrative
  - Used when hybrid pipeline successfully generates AI narrative

- **Analysis Complete Badge** (ai_enhanced === false):
  - Gray background with check circle icon
  - Indicates fallback deterministic narrative
  - Used when LLM is unavailable or times out

- **Polling State Badge** (isPolling === true):
  - Loading spinner with AI analysis enhancing report message
  - Shown during background LLM processing

```mermaid
flowchart TD
Input["ai_enhanced flag"] --> CheckPolling{"isPolling?"}
CheckPolling -- Yes --> PollingBadge["Show polling badge"]
CheckPolling -- No --> CheckEnhanced{"ai_enhanced === true?"}
CheckEnhanced -- Yes --> AIEnhancedBadge["Show AI Enhanced Report badge<br/>+ analysis quality"]
CheckEnhanced -- No --> CheckFallback{"ai_enhanced === false?"}
CheckFallback -- Yes --> FallbackBadge["Show Analysis complete badge"]
CheckFallback -- No --> NoBadge["No badge shown"]
```

**Diagram sources**
- [ResultCard.jsx:198-244](file://app/frontend/src/components/ResultCard.jsx#L198-L244)

**Section sources**
- [ResultCard.jsx:198-244](file://app/frontend/src/components/ResultCard.jsx#L198-L244)

### ScoreGauge: Fit Score Visualization
- Thresholds: ≥72 Strong Fit, ≥45 Moderate Fit, else Low Fit
- Pending state displays "Manual Review" with neutral styling
- Animated arc indicates score percentage
- Recommendation label updates dynamically

```mermaid
flowchart TD
Input["score"] --> CheckPending{"score is null/undefined?"}
CheckPending -- Yes --> Pending["Show pending UI"]
CheckPending -- No --> Thresholds{"score thresholds"}
Thresholds --> |≥72| Strong["Green arc + Strong Fit"]
Thresholds --> |≥45| Moderate["Amber arc + Moderate Fit"]
Thresholds --> |<45| Low["Default arc + Low Fit"]
```

**Diagram sources**
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)

**Section sources**
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)

### Timeline: Employment History and Gaps
- Sorts jobs by start date descending
- Highlights short tenures
- Renders gaps with severity and duration
- Uses icons and subtle timelines

```mermaid
flowchart TD
Jobs["workExperience[]"] --> Sort["Sort by start_date desc"]
Sort --> Render["Render job entries"]
Render --> ShortTenure{"Duration < 6 months?"}
ShortTenure -- Yes --> Alert["Highlight with alert icon"]
ShortTenure -- No --> Normal["Standard briefcase icon"]
Render --> Gaps["Map gaps to jobs"]
Gaps --> Severity["Severity badge"]
```

**Diagram sources**
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-L115)

**Section sources**
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-L115)

### Sharing Mechanism
- Generates a random ID and stores the result in session storage
- Copies shareable URL to clipboard; falls back to prompting if clipboard API fails
- Uses window origin for absolute URL construction

```mermaid
sequenceDiagram
participant User as "User"
participant RP as "ReportPage"
participant SS as "sessionStorage"
User->>RP : Click Share
RP->>RP : crypto.randomUUID()
RP->>SS : setItem("report_{id}", JSON.stringify(result))
RP->>RP : Construct URL with id param
RP->>User : navigator.clipboard.writeText(url)
alt Clipboard fails
RP->>User : window.prompt("Copy this link : ", url)
end
```

**Diagram sources**
- [ReportPage.jsx:127-135](file://app/frontend/src/pages/ReportPage.jsx#L127-L135)

**Section sources**
- [ReportPage.jsx:127-135](file://app/frontend/src/pages/ReportPage.jsx#L127-L135)

### PDF Download and Print Optimization
- Download triggers browser print dialog
- Print styles minimize UI, adjust fonts, and remove shadows
- Print-only header appears at the top of printed pages

```mermaid
flowchart TD
Click["User clicks Download PDF"] --> Print["window.print()"]
Print --> Browser["Browser print dialog"]
Browser --> Styles["@media print styles apply"]
Styles --> Header["Print-only header"]
Styles --> RemoveUI["Remove interactive UI"]
Styles --> AdjustFonts["Adjust font sizes"]
```

**Diagram sources**
- [ReportPage.jsx:137-137](file://app/frontend/src/pages/ReportPage.jsx#L137-L137)
- [index.css:136-160](file://app/frontend/src/index.css#L136-L160)

**Section sources**
- [ReportPage.jsx:137-137](file://app/frontend/src/pages/ReportPage.jsx#L137-L137)
- [index.css:136-160](file://app/frontend/src/index.css#L136-L160)

### Export Formats: CSV and Excel
- CSV export: Streams CSV rows with selected fields
- Excel export: Streams XLSX with a single sheet
- Client-side download triggered via Blob and anchor element

```mermaid
sequenceDiagram
participant User as "User"
participant API as "api.js.exportCsv/exportExcel"
participant BE as "export.py"
User->>API : exportCsv(ids) or exportExcel(ids)
API->>BE : GET /api/export/csv?ids=... or /api/export/excel?ids=...
BE-->>API : StreamingResponse (text/csv or application/vnd.openxmlformats...)
API-->>User : _triggerDownload(Blob, filename, type)
```

**Diagram sources**
- [api.js:183-204](file://app/frontend/src/lib/api.js#L183-L204)
- [export.py:55-104](file://app/backend/routes/export.py#L55-L104)

**Section sources**
- [api.js:183-204](file://app/frontend/src/lib/api.js#L183-L204)
- [export.py:55-104](file://app/backend/routes/export.py#L55-L104)

### Email Generation Integration
- ResultCard opens a modal to generate shortlist/rejection/screening-call emails
- Uses backend email generation endpoint powered by Ollama
- Falls back to templates if LLM is unavailable

```mermaid
sequenceDiagram
participant User as "User"
participant RC as "ResultCard"
participant API as "api.js.generateEmail"
participant BE as "email_gen.py"
User->>RC : Click "Email"
RC->>API : POST /api/email/generate
API->>BE : POST /api/email/generate
BE-->>API : {subject, body}
API-->>RC : Draft ready
RC-->>User : Modal shows subject/body
```

**Diagram sources**
- [ResultCard.jsx:94-194](file://app/frontend/src/components/ResultCard.jsx#L94-L194)
- [api.js:246-249](file://app/frontend/src/lib/api.js#L246-L249)
- [email_gen.py:39-104](file://app/backend/routes/email_gen.py#L39-L104)

**Section sources**
- [ResultCard.jsx:94-194](file://app/frontend/src/components/ResultCard.jsx#L94-L194)
- [api.js:246-249](file://app/frontend/src/lib/api.js#L246-L249)
- [email_gen.py:39-104](file://app/backend/routes/email_gen.py#L39-L104)

## Dependency Analysis
- ReportPage depends on ResultCard, ScoreGauge, Timeline, and api.js
- ResultCard depends on SkillsRadar and uses api.js for email generation
- **Enhanced backend services now propagate ai_enhanced flags** through the analysis pipeline
- Export and analysis flows depend on backend routes
- Print styles are centralized in index.css

```mermaid
graph LR
RP["ReportPage.jsx"] --> RC["ResultCard.jsx"]
RP --> SG["ScoreGauge.jsx"]
RP --> TL["Timeline.jsx"]
RP --> API["api.js"]
RC --> ASB["AnalysisSourceBadge.jsx"]
RC --> SR["SkillsRadar.jsx"]
RC --> API
API --> EX["export.py"]
API --> AN["analyze.py"]
AN --> HP["hybrid_pipeline.py"]
HP --> LS["llm_service.py"]
LS --> AS["analysis_service.py"]
API --> EG["email_gen.py"]
CSS["index.css"] --> RP
CSS --> RC
```

**Diagram sources**
- [ReportPage.jsx:82-296](file://app/frontend/src/pages/ReportPage.jsx#L82-L296)
- [ResultCard.jsx:265-626](file://app/frontend/src/components/ResultCard.jsx#L265-L626)
- [ResultCard.jsx:198-244](file://app/frontend/src/components/ResultCard.jsx#L198-L244)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)
- [SkillsRadar.jsx:110-261](file://app/frontend/src/components/SkillsRadar.jsx#L110-L261)
- [Timeline.jsx:3-115](file://app/frontend/src/components/Timeline.jsx#L3-L115)
- [api.js:1-395](file://app/frontend/src/lib/api.js#L1-L395)
- [index.css:136-160](file://app/frontend/src/index.css#L136-L160)
- [export.py:55-104](file://app/backend/routes/export.py#L55-L104)
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [email_gen.py:39-104](file://app/backend/routes/email_gen.py#L39-L104)
- [hybrid_pipeline.py:1322-1335](file://app/backend/services/hybrid_pipeline.py#L1322-L1335)
- [llm_service.py:256-273](file://app/backend/services/llm_service.py#L256-L273)

**Section sources**
- [ReportPage.jsx:82-296](file://app/frontend/src/pages/ReportPage.jsx#L82-L296)
- [ResultCard.jsx:265-626](file://app/frontend/src/components/ResultCard.jsx#L265-L626)
- [ResultCard.jsx:198-244](file://app/frontend/src/components/ResultCard.jsx#L198-L244)
- [api.js:1-395](file://app/frontend/src/lib/api.js#L1-L395)
- [export.py:55-104](file://app/backend/routes/export.py#L55-L104)
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [email_gen.py:39-104](file://app/backend/routes/email_gen.py#L39-L104)
- [index.css:136-160](file://app/frontend/src/index.css#L136-L160)
- [hybrid_pipeline.py:1322-1335](file://app/backend/services/hybrid_pipeline.py#L1322-L1335)
- [llm_service.py:256-273](file://app/backend/services/llm_service.py#L256-L273)

## Performance Considerations
- Printing: The print stylesheet removes shadows and adjusts font sizes to reduce layout overhead during print
- Export streaming: CSV and Excel are streamed from the backend to avoid large memory usage on the client
- Client-side sharing: Uses session storage to avoid network requests for sharing within the same tab
- **AI Enhancement Flag Propagation**: Backend services consistently set ai_enhanced flag to ensure frontend displays accurate badge states
- Recommendations:
  - Keep print styles minimal to avoid layout thrashing
  - Prefer server-side exports for large datasets
  - Debounce name edits to avoid frequent PATCH requests
  - **Monitor LLM availability for optimal AI Enhanced Report badge display**

## Troubleshooting Guide
Common issues and resolutions:
- Share link does not open report:
  - Ensure the report ID exists in session storage
  - Verify the URL includes the id query parameter
- Download PDF does nothing:
  - Confirm browser print dialog is enabled
  - Check that print styles are applied
- Export downloads blank or partial data:
  - Verify backend endpoints are reachable
  - Confirm ids parameter is correctly passed
- Email generation fails:
  - Check Ollama availability and model readiness
  - Confirm candidate exists and has a recent analysis result
- **AI Enhancement Badge Issues**:
  - **AI Enhanced Report badge not showing**: Verify ai_enhanced flag is properly set in backend analysis result
  - **Analysis complete badge appears incorrectly**: Check that fallback narrative is being generated when LLM is unavailable
  - **Polling badge stuck**: Ensure background LLM processing is completing and setting narrative_ready flag

**Section sources**
- [ReportPage.jsx:127-135](file://app/frontend/src/pages/ReportPage.jsx#L127-L135)
- [ReportPage.jsx:137-137](file://app/frontend/src/pages/ReportPage.jsx#L137-L137)
- [api.js:183-204](file://app/frontend/src/lib/api.js#L183-L204)
- [email_gen.py:77-104](file://app/backend/routes/email_gen.py#L77-L104)
- [ResultCard.jsx:198-244](file://app/frontend/src/components/ResultCard.jsx#L198-L244)

## Conclusion
The individual report system combines a responsive frontend with robust backend support to deliver a complete candidate analysis experience. ReportPage orchestrates the UI, ResultCard presents detailed insights with enhanced AI distinction badges, ScoreGauge communicates fit quickly, and Timeline contextualizes work history. Sharing and PDF printing are streamlined for productivity, while CSV and Excel exports enable scalable data handling. Print optimization and branding are integrated through centralized styles. **The enhanced narrative distinction system now provides clear visual indicators of whether reports are AI-generated or fallback narratives, improving transparency and trust in the analysis process.**

## Appendices

### Customization Options
- Report layout:
  - Sidebar and main content split is controlled in ReportPage
  - Additional sections can be added by extending ResultCard
- Branding integration:
  - Brand colors and gradients are defined in Tailwind utilities and CSS
  - Update color classes to align with brand guidelines
- Print optimization:
  - Modify @media print rules in index.css to adjust margins, fonts, and UI removal
- Export formats:
  - Extend backend export.py to add new columns or sheets
  - Update frontend api.js to support additional formats
- **AI Enhancement Badge Customization**:
  - Modify AnalysisSourceBadge component to change badge appearance
  - Update color schemes for different analysis quality levels
  - Customize badge text and icons for different AI enhancement states

**Section sources**
- [ReportPage.jsx:153-296](file://app/frontend/src/pages/ReportPage.jsx#L153-L296)
- [ResultCard.jsx:265-626](file://app/frontend/src/components/ResultCard.jsx#L265-L626)
- [ResultCard.jsx:198-244](file://app/frontend/src/components/ResultCard.jsx#L198-L244)
- [index.css:136-160](file://app/frontend/src/index.css#L136-L160)
- [export.py:27-52](file://app/backend/routes/export.py#L27-L52)