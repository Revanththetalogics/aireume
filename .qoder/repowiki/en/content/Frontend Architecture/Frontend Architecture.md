# Frontend Architecture

<cite>
**Referenced Files in This Document**
- [main.jsx](file://app/frontend/src/main.jsx)
- [App.jsx](file://app/frontend/src/App.jsx)
- [ErrorBoundary.jsx](file://app/frontend/src/components/ErrorBoundary.jsx)
- [AppShell.jsx](file://app/frontend/src/components/AppShell.jsx)
- [NavBar.jsx](file://app/frontend/src/components/NavBar.jsx)
- [ProtectedRoute.jsx](file://app/frontend/src/components/ProtectedRoute.jsx)
- [AuthContext.jsx](file://app/frontend/src/contexts/AuthContext.jsx)
- [api.js](file://app/frontend/src/lib/api.js)
- [UploadForm.jsx](file://app/frontend/src/components/UploadForm.jsx)
- [ResultCard.jsx](file://app/frontend/src/components/ResultCard.jsx)
- [ScoreGauge.jsx](file://app/frontend/src/components/ScoreGauge.jsx)
- [Timeline.jsx](file://app/frontend/src/components/Timeline.jsx)
- [SkillsRadar.jsx](file://app/frontend/src/components/SkillsRadar.jsx)
- [Dashboard.jsx](file://app/frontend/src/pages/Dashboard.jsx)
- [CandidatesPage.jsx](file://app/frontend/src/pages/CandidatesPage.jsx)
- [ReportPage.jsx](file://app/frontend/src/pages/ReportPage.jsx)
- [useSubscription.jsx](file://app/frontend/src/hooks/useSubscription.jsx)
- [package.json](file://app/frontend/package.json)
</cite>

## Update Summary
**Changes Made**
- Added comprehensive ErrorBoundary implementation for graceful degradation
- Enhanced API retry mechanisms with exponential backoff for transient errors
- Improved error handling patterns throughout frontend components
- Added global error handlers for uncaught exceptions
- Implemented robust retry logic with idempotency considerations

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Testing Strategy](#testing-strategy)
9. [Extensibility Guidelines](#extensibility-guidelines)
10. [Accessibility and Responsive Design](#accessibility-and-responsive-design)
11. [Error Handling and Resilience](#error-handling-and-resilience)
12. [Troubleshooting Guide](#troubleshooting-guide)
13. [Conclusion](#conclusion)

## Introduction
This document describes the frontend architecture for Resume AI by ThetaLogics. It covers the React 18 component model, routing, state management, component library, styling and responsiveness, API integration, authentication and subscription management, error handling and resilience patterns, testing strategy, and extension guidelines. The system emphasizes a clean separation of concerns, composable UI components, robust integration with backend services via Axios interceptors and dedicated hooks, and comprehensive error handling for graceful degradation.

## Project Structure
The frontend is organized around a classic React 18 + Vite setup with modular components, pages, contexts, hooks, and a centralized API client. Routing is handled by React Router v7 with lazy-loaded pages and protected routes. Styling leverages TailwindCSS with a consistent design system and brand palette. The architecture now includes comprehensive error handling through React ErrorBoundary components and enhanced API retry mechanisms.

```mermaid
graph TB
subgraph "Entry Point"
M["main.jsx"]
A["App.jsx"]
EB["ErrorBoundary.jsx"]
end
subgraph "Routing"
R["React Router v7<br/>lazy routes"]
PR["ProtectedRoute.jsx"]
end
subgraph "UI Shell"
AS["AppShell.jsx"]
NB["NavBar.jsx"]
end
subgraph "Pages"
D["Dashboard.jsx"]
RP["ReportPage.jsx"]
CP["CandidatesPage.jsx"]
end
subgraph "Components"
UF["UploadForm.jsx"]
RC["ResultCard.jsx"]
SG["ScoreGauge.jsx"]
TL["Timeline.jsx"]
SR["SkillsRadar.jsx"]
end
subgraph "State & Auth"
AC["AuthContext.jsx"]
USC["useSubscription.jsx"]
end
subgraph "API Layer"
API["api.js"]
end
M --> A
A --> EB
EB --> R
R --> PR
PR --> AS
AS --> NB
AS --> D
D --> UF
D --> RP
RP --> RC
RP --> SG
RP --> TL
RC --> SR
A --> CP
A --> API
A --> AC
A --> USC
```

**Diagram sources**
- [main.jsx:1-23](file://app/frontend/src/main.jsx#L1-L23)
- [App.jsx:1-67](file://app/frontend/src/App.jsx#L1-L67)
- [ErrorBoundary.jsx:1-54](file://app/frontend/src/components/ErrorBoundary.jsx#L1-L54)
- [ProtectedRoute.jsx:1-24](file://app/frontend/src/components/ProtectedRoute.jsx#L1-L24)
- [AppShell.jsx:1-13](file://app/frontend/src/components/AppShell.jsx#L1-L13)
- [NavBar.jsx](file://app/frontend/src/components/NavBar.jsx)
- [Dashboard.jsx:1-330](file://app/frontend/src/pages/Dashboard.jsx#L1-L330)
- [ReportPage.jsx:1-297](file://app/frontend/src/pages/ReportPage.jsx#L1-L297)
- [CandidatesPage.jsx:1-204](file://app/frontend/src/pages/CandidatesPage.jsx#L1-L204)
- [UploadForm.jsx:1-484](file://app/frontend/src/components/UploadForm.jsx#L1-L484)
- [ResultCard.jsx:1-627](file://app/frontend/src/components/ResultCard.jsx#L1-L627)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)
- [Timeline.jsx:1-115](file://app/frontend/src/components/Timeline.jsx#L1-L115)
- [SkillsRadar.jsx](file://app/frontend/src/components/SkillsRadar.jsx)
- [AuthContext.jsx:1-71](file://app/frontend/src/contexts/AuthContext.jsx#L1-L71)
- [useSubscription.jsx:1-186](file://app/frontend/src/hooks/useSubscription.jsx#L1-L186)
- [api.js:1-486](file://app/frontend/src/lib/api.js#L1-L486)

**Section sources**
- [main.jsx:1-23](file://app/frontend/src/main.jsx#L1-L23)
- [App.jsx:1-67](file://app/frontend/src/App.jsx#L1-L67)
- [ErrorBoundary.jsx:1-54](file://app/frontend/src/components/ErrorBoundary.jsx#L1-L54)
- [package.json:1-41](file://app/frontend/package.json#L1-L41)

## Core Components
- **ErrorBoundary**: React ErrorBoundary component for graceful degradation with user-friendly error messages and retry options.
- **AppShell**: Provides a consistent layout with navigation and scrollable content area.
- **ProtectedRoute**: Guards routes requiring authentication.
- **UploadForm**: Multi-mode job description input (text, file, URL), scoring weights, and resume upload with drag-and-drop.
- **ResultCard**: Comprehensive analysis results with collapsible sections, explainability, skills radar, interview kit, and email generation.
- **ScoreGauge**: Visual fit score with thresholds and pending state.
- **Timeline**: Employment history visualization with gaps and severity indicators.
- **Dashboard**: Real-time agent pipeline progress, usage widget, and submission flow with enhanced error handling.
- **CandidatesPage**: List and search candidates with pagination and detail modal.
- **ReportPage**: Single-result presentation with sharing, printing, labeling, and inline editing.
- **AuthContext**: JWT lifecycle, login/register/logout, and tenant/user state.
- **useSubscription**: Subscription and usage checks, optimistic updates, and plan features with improved error handling.

**Section sources**
- [ErrorBoundary.jsx:1-54](file://app/frontend/src/components/ErrorBoundary.jsx#L1-L54)
- [AppShell.jsx:1-13](file://app/frontend/src/components/AppShell.jsx#L1-L13)
- [ProtectedRoute.jsx:1-24](file://app/frontend/src/components/ProtectedRoute.jsx#L1-L24)
- [UploadForm.jsx:1-484](file://app/frontend/src/components/UploadForm.jsx#L1-L484)
- [ResultCard.jsx:1-627](file://app/frontend/src/components/ResultCard.jsx#L1-L627)
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)
- [Timeline.jsx:1-115](file://app/frontend/src/components/Timeline.jsx#L1-L115)
- [Dashboard.jsx:1-330](file://app/frontend/src/pages/Dashboard.jsx#L1-L330)
- [CandidatesPage.jsx:1-204](file://app/frontend/src/pages/CandidatesPage.jsx#L1-L204)
- [ReportPage.jsx:1-297](file://app/frontend/src/pages/ReportPage.jsx#L1-L297)
- [AuthContext.jsx:1-71](file://app/frontend/src/contexts/AuthContext.jsx#L1-L71)
- [useSubscription.jsx:1-186](file://app/frontend/src/hooks/useSubscription.jsx#L1-L186)

## Architecture Overview
The frontend follows a layered architecture with enhanced error handling:
- Entry point initializes React 18 StrictMode, Router, global error handlers, and ErrorBoundary wrapper.
- App wraps routes with ErrorBoundary, AuthProvider, sets up lazy routes, and renders shell wrappers.
- ErrorBoundary provides graceful degradation with user-friendly error messages and retry options.
- AppShell hosts NavBar and page content.
- Pages orchestrate UI components and API interactions with improved error handling.
- API client centralizes HTTP requests, JWT injection, automatic refresh, and enhanced retry mechanisms.
- Contexts and hooks manage authentication and subscription state with robust error handling.

```mermaid
sequenceDiagram
participant U as "User"
participant EB as "ErrorBoundary"
participant R as "Router(App.jsx)"
participant P as "ProtectedRoute"
participant S as "AppShell"
participant D as "Dashboard"
participant UF as "UploadForm"
participant API as "api.js"
participant BE as "Backend"
U->>R : Navigate to "/"
R->>EB : Wrap routes
EB->>P : Render route
P->>P : Check auth (AuthContext)
alt Not authenticated
P-->>U : Redirect to "/login"
else Authenticated
P->>S : Render shell
S->>D : Render Dashboard
D->>UF : Render UploadForm
U->>UF : Submit (resume + JD)
UF->>API : analyzeResumeStream(...)
API->>BE : POST /analyze/stream
BE-->>API : Handle 5xx errors with retry
BE-->>API : Handle network errors with retry
API-->>D : SSE chunks
D-->>U : Progress updates
D->>R : Navigate("/report", {state : result})
end
```

**Diagram sources**
- [App.jsx:1-67](file://app/frontend/src/App.jsx#L1-L67)
- [ErrorBoundary.jsx:1-54](file://app/frontend/src/components/ErrorBoundary.jsx#L1-L54)
- [ProtectedRoute.jsx:1-24](file://app/frontend/src/components/ProtectedRoute.jsx#L1-L24)
- [AppShell.jsx:1-13](file://app/frontend/src/components/AppShell.jsx#L1-L13)
- [Dashboard.jsx:1-330](file://app/frontend/src/pages/Dashboard.jsx#L1-L330)
- [UploadForm.jsx:1-484](file://app/frontend/src/components/UploadForm.jsx#L1-L484)
- [api.js:64-90](file://app/frontend/src/lib/api.js#L64-L90)

**Section sources**
- [App.jsx:1-67](file://app/frontend/src/App.jsx#L1-L67)
- [ErrorBoundary.jsx:1-54](file://app/frontend/src/components/ErrorBoundary.jsx#L1-L54)
- [api.js:1-486](file://app/frontend/src/lib/api.js#L1-L486)

## Detailed Component Analysis

### ErrorBoundary Implementation
The ErrorBoundary component provides comprehensive error handling for the entire application:
- Catches JavaScript errors anywhere in the child component tree
- Displays user-friendly error messages with actionable retry options
- Implements exponential backoff retry mechanism
- Maintains application state during error conditions
- Provides both manual retry and automatic refresh options

```mermaid
flowchart TD
Start(["ErrorBoundary"]) --> Check{"Error caught?"}
Check --> |No| Children["Render children"]
Check --> |Yes| Display["Display error UI"]
Display --> Options["Show retry options"]
Options --> Manual["Manual Retry"]
Options --> Refresh["Refresh Page"]
Manual --> Reset["Reset error state"]
Reset --> Children
Refresh --> Reload["Window reload"]
```

**Diagram sources**
- [ErrorBoundary.jsx:1-54](file://app/frontend/src/components/ErrorBoundary.jsx#L1-L54)

**Section sources**
- [ErrorBoundary.jsx:1-54](file://app/frontend/src/components/ErrorBoundary.jsx#L1-L54)

### Authentication and Routing
- AuthContext manages user, tenant, and loading state. It loads persisted tokens via httpOnly cookies, logs in/out, and exposes helpers to child components.
- ProtectedRoute enforces authentication for protected shells and shows a loader while resolving session state.
- App.jsx defines lazy routes for all pages and wraps them in ErrorBoundary, ProtectedRoute, and SubscriptionProvider, then AppShell.

```mermaid
flowchart TD
Start(["App.jsx"]) --> ErrorWrap["ErrorBoundary Wrapper"]
ErrorWrap --> Auth["AuthProvider"]
Auth --> Routes["Define lazy routes"]
Routes --> Guard["ProtectedRoute"]
Guard --> Shell["SubscriptionProvider -> AppShell"]
Shell --> Pages["Pages render"]
Guard --> |No user| Redirect["Navigate to /login"]
```

**Diagram sources**
- [App.jsx:1-67](file://app/frontend/src/App.jsx#L1-L67)
- [ProtectedRoute.jsx:1-24](file://app/frontend/src/components/ProtectedRoute.jsx#L1-L24)
- [AuthContext.jsx:1-71](file://app/frontend/src/contexts/AuthContext.jsx#L1-L71)

**Section sources**
- [AuthContext.jsx:1-71](file://app/frontend/src/contexts/AuthContext.jsx#L1-L71)
- [ProtectedRoute.jsx:1-24](file://app/frontend/src/components/ProtectedRoute.jsx#L1-L24)
- [App.jsx:1-67](file://app/frontend/src/App.jsx#L1-L67)

### Enhanced API Integration Layer
- api.js creates an Axios instance with base URL from environment.
- Request interceptor attaches CSRF token for non-GET requests and handles httpOnly cookies automatically.
- Response interceptor handles 401 by refreshing token via refresh endpoint and retrying the original request.
- **NEW**: Enhanced retry interceptor with exponential backoff for 5xx errors and network failures.
- **NEW**: Idempotency checking to prevent retrying non-idempotent POST requests.
- **NEW**: Configurable retry limits (MAX_RETRIES = 3) with delays [1s, 2s, 4s].
- Exposes domain-specific functions for analysis, batch, history, comparison, exports, templates, candidates, email generation, JD URL extraction, team actions, training, video, transcript, health, and subscription management.

```mermaid
sequenceDiagram
participant C as "Component"
participant AX as "Axios Instance(api.js)"
participant INT as "Interceptors"
participant RET as "Retry Interceptor"
participant REF as "Refresh Endpoint"
participant BE as "Backend"
C->>AX : api.analyzeResumeStream(...)
AX->>INT : Request Interceptor (attach CSRF)
INT->>RET : Response Interceptor
alt 5xx Error or Network Error
RET->>RET : Check retry conditions
RET->>RET : Exponential backoff (1s, 2s, 4s)
RET->>AX : Retry request
else 401 Unauthorized
INT->>REF : POST /auth/refresh
REF-->>INT : New access_token
INT->>AX : Retry original request
else Success
AX-->>C : Response data
end
```

**Diagram sources**
- [api.js:64-90](file://app/frontend/src/lib/api.js#L64-L90)

**Section sources**
- [api.js:1-486](file://app/frontend/src/lib/api.js#L1-L486)

### UploadForm
- Supports three job description modes: text, file, URL.
- Drag-and-drop for resume and JD via react-dropzone with accept rules and size limits.
- Scoring weights presets and custom sliders.
- Saved JD templates picker with save-to-library flow.
- Submission guarded by validation and loading state.
- **Enhanced**: Improved error handling with user-friendly error messages and retry capabilities.

```mermaid
flowchart TD
Start(["UploadForm"]) --> Mode{"JD Mode"}
Mode --> |Text| Text["Textarea + Save to Library"]
Mode --> |File| File["Dropzone for JD file"]
Mode --> |URL| Url["Extract from URL"]
Text --> Weights["Weights Panel"]
File --> Weights
Url --> Weights
Weights --> Submit{"Valid?"}
Submit --> |No| Error["Show error"]
Submit --> |Yes| Analyze["Call analyzeResumeStream(...)"]
```

**Diagram sources**
- [UploadForm.jsx:1-484](file://app/frontend/src/components/UploadForm.jsx#L1-L484)
- [api.js:122-205](file://app/frontend/src/lib/api.js#L122-L205)

**Section sources**
- [UploadForm.jsx:1-484](file://app/frontend/src/components/UploadForm.jsx#L1-L484)

### ResultCard
- Renders recommendation badge, analysis source indicator, pending banner, score breakdown bars, matched/missing skills, adjacent skills, skills radar, strengths/weaknesses/risk signals, explainability, education analysis, domain fit/architecture, and interview kit tabs.
- Email modal integrates with backend email generation.

```mermaid
classDiagram
class ResultCard {
+props result
+defaultExpandEducation boolean
+render()
}
class SkillsRadar
class EmailModal
ResultCard --> SkillsRadar : "composition"
ResultCard --> EmailModal : "optional"
```

**Diagram sources**
- [ResultCard.jsx:1-627](file://app/frontend/src/components/ResultCard.jsx#L1-L627)
- [SkillsRadar.jsx](file://app/frontend/src/components/SkillsRadar.jsx)

**Section sources**
- [ResultCard.jsx:1-627](file://app/frontend/src/components/ResultCard.jsx#L1-L627)

### ScoreGauge
- Visualizes fit score with thresholds and pending state. Uses SVG arcs and transitions.

```mermaid
flowchart TD
Start(["ScoreGauge"]) --> Pending{"score is null?"}
Pending --> |Yes| PendingView["Render pending state"]
Pending --> |No| Arc["Render arc with color bands"]
```

**Diagram sources**
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)

**Section sources**
- [ScoreGauge.jsx:1-97](file://app/frontend/src/components/ScoreGauge.jsx#L1-L97)

### Timeline
- Sorts and renders work experience with optional employment gaps and severity badges.

```mermaid
flowchart TD
Start(["Timeline"]) --> Check{"Has workExperience?"}
Check --> |No| Empty["No data message"]
Check --> |Yes| Sort["Sort by start_date desc"]
Sort --> Loop["Render jobs with gaps"]
```

**Diagram sources**
- [Timeline.jsx:1-115](file://app/frontend/src/components/Timeline.jsx#L1-L115)

**Section sources**
- [Timeline.jsx:1-115](file://app/frontend/src/components/Timeline.jsx#L1-L115)

### Dashboard
- Orchestrates agent pipeline progress visualization during streaming analysis.
- Integrates usage widget via useSubscription and navigates to ReportPage upon completion.
- **Enhanced**: Improved error handling with graceful degradation and user feedback.

```mermaid
sequenceDiagram
participant D as "Dashboard"
participant UF as "UploadForm"
participant API as "api.js"
participant RP as "ReportPage"
D->>UF : Collect inputs
UF->>D : onSubmit()
D->>API : analyzeResumeStream(selectedFile, jobDescription, jobFile, weights, onStageComplete)
API-->>D : Stage events
D->>D : Update completedStages
D->>RP : Navigate("/report", {state : result})
```

**Diagram sources**
- [Dashboard.jsx:1-330](file://app/frontend/src/pages/Dashboard.jsx#L1-L330)
- [api.js:122-205](file://app/frontend/src/lib/api.js#L122-L205)

**Section sources**
- [Dashboard.jsx:1-330](file://app/frontend/src/pages/Dashboard.jsx#L1-L330)

### CandidatesPage
- Lists candidates with search, pagination, and detail modal showing history and quick navigation to reports.

```mermaid
flowchart TD
Start(["CandidatesPage"]) --> Fetch["getCandidates({search, page, page_size})"]
Fetch --> Render["Render table + pagination"]
Render --> Detail{"Open detail?"}
Detail --> |Yes| Modal["CandidateDetail modal"]
Detail --> |No| Idle["Idle"]
```

**Diagram sources**
- [CandidatesPage.jsx:1-204](file://app/frontend/src/pages/CandidatesPage.jsx#L1-L204)
- [api.js:287-295](file://app/frontend/src/lib/api.js#L287-L295)

**Section sources**
- [CandidatesPage.jsx:1-204](file://app/frontend/src/pages/CandidatesPage.jsx#L1-L204)

### ReportPage
- Presents a single result with sidebar actions (share, download PDF), inline candidate name editor, label training buttons, and full ResultCard plus Timeline.

```mermaid
sequenceDiagram
participant RP as "ReportPage"
participant RC as "ResultCard"
participant TL as "Timeline"
participant API as "api.js"
RP->>RC : Render with result
RP->>TL : Render with work_experience + gaps
RP->>API : labelTrainingExample(result_id, outcome)
RP->>API : updateResultStatus(result_id, outcome)
```

**Diagram sources**
- [ReportPage.jsx:1-297](file://app/frontend/src/pages/ReportPage.jsx#L1-L297)
- [ResultCard.jsx:1-627](file://app/frontend/src/components/ResultCard.jsx#L1-L627)
- [Timeline.jsx:1-115](file://app/frontend/src/components/Timeline.jsx#L1-L115)
- [api.js:340-343](file://app/frontend/src/lib/api.js#L340-L343)

**Section sources**
- [ReportPage.jsx:1-297](file://app/frontend/src/pages/ReportPage.jsx#L1-L297)

### Subscription Management Hooks
- useSubscription provides cached subscription data, available plans, usage stats, feature checks, and optimistic refresh after analysis.
- useUsageCheck performs preflight checks against remaining analyses and server-side limits.
- **Enhanced**: Improved error handling with graceful degradation and user feedback.

```mermaid
flowchart TD
Start(["useSubscription"]) --> Fetch["fetchSubscription(force=false)"]
Fetch --> Cache{"Within cache window?"}
Cache --> |Yes| Return["Return cached subscription"]
Cache --> |No| Call["GET /subscription"]
Call --> Update["Set state + lastFetch"]
Update --> Return
Return --> Widgets["UsageWidget / Dashboard"]
```

**Diagram sources**
- [useSubscription.jsx:1-186](file://app/frontend/src/hooks/useSubscription.jsx#L1-L186)

**Section sources**
- [useSubscription.jsx:1-186](file://app/frontend/src/hooks/useSubscription.jsx#L1-L186)

## Dependency Analysis
- React 18 with React DOM for rendering.
- React Router v7 for routing and lazy loading.
- Axios for HTTP with enhanced interceptors and retry mechanisms.
- lucide-react for icons.
- react-dropzone for drag-and-drop.
- recharts for optional visualizations.
- TailwindCSS for styling and responsive design.

```mermaid
graph LR
Pkg["package.json"] --> React["react@^18"]
Pkg --> Router["react-router-dom@^7"]
Pkg --> Axios["axios@^1.7"]
Pkg --> Icons["lucide-react@^0.469"]
Pkg --> Drop["react-dropzone@^14"]
Pkg --> Charts["recharts@^3"]
Pkg --> Tailwind["tailwindcss@^3"]
```

**Diagram sources**
- [package.json:1-41](file://app/frontend/package.json#L1-L41)

**Section sources**
- [package.json:1-41](file://app/frontend/package.json#L1-L41)

## Performance Considerations
- Lazy loading: Pages are lazy-imported to reduce initial bundle size.
- Suspense: Fallback spinner during page load.
- Optimistic updates: Subscription usage increments immediately, followed by server sync.
- Efficient rendering: Components use minimal state and avoid unnecessary re-renders; lists paginated.
- Streaming: SSE-based analysis updates UI progressively without polling.
- Image/icon assets: lucide-react icons are tree-shaken; keep only used icons.
- **Enhanced**: Error boundaries prevent cascading failures and improve perceived performance.
- **Enhanced**: Retry mechanisms with exponential backoff reduce user frustration from transient failures.

## Testing Strategy
- Unit and integration tests use React Testing Library and Vitest.
- Tests cover components like UploadForm, ResultCard, ScoreGauge, and pages like VideoPage.
- Mock services and API endpoints are used to isolate component behavior.
- Setup includes DOM testing with jsdom and React Testing Library matchers.
- **Enhanced**: Error boundary testing with user interaction scenarios and retry logic validation.

**Section sources**
- [UploadForm.test.jsx](file://app/frontend/src/__tests__/UploadForm.test.jsx)
- [ResultCard.test.jsx](file://app/frontend/src/__tests__/ResultCard.test.jsx)
- [ScoreGauge.test.jsx](file://app/frontend/src/__tests__/ScoreGauge.test.jsx)
- [VideoPage.test.jsx](file://app/frontend/src/__tests__/VideoPage.test.jsx)
- [api.test.js](file://app/frontend/src/__tests__/api.test.js)
- [setup.js](file://app/frontend/src/__tests__/setup.js)

## Extensibility Guidelines
- Add new pages under pages/ and register them in App.jsx with lazy import, ErrorBoundary wrapper, ProtectedRoute wrapper, and SubscriptionProvider.
- Create reusable components in components/ following existing patterns: props interface, controlled state, Tailwind classes, and accessibility attributes.
- Extend API client in lib/api.js with new endpoints and reuse enhanced interceptors for auth, refresh, and retry logic.
- Introduce new contexts or hooks under contexts/ or hooks/ respectively, and wrap providers at App.jsx level with ErrorBoundary.
- Keep styling consistent with existing Tailwind utilities and brand tokens; avoid ad-hoc CSS.
- For new features gated by plan, use useSubscription.isFeatureAvailable and guard UI accordingly.
- **Enhanced**: Implement ErrorBoundary for critical components that require graceful degradation.

## Accessibility and Responsive Design
- Accessible semantics: Buttons, inputs, and modals use appropriate roles and labels; focus management in dialogs.
- Keyboard navigation: Focus traps in modals, Enter/Escape handlers in editors.
- Responsive breakpoints: Use flex/grid utilities to adapt layouts across screen sizes; sidebar collapses on mobile.
- Color contrast: Maintain sufficient contrast for text and interactive elements; brand palette is used consistently.
- ARIA patterns: Dialogs and modals announce content; loading states expose spinners with accessible labels.
- **Enhanced**: Error messages provide clear guidance and actionable next steps for users.

## Error Handling and Resilience

### Global Error Handling
The application implements comprehensive error handling at multiple levels:

#### Application-Level Error Boundary
- Wraps the entire application to prevent crashes and provide graceful degradation
- Displays user-friendly error messages with retry options
- Handles both JavaScript errors and component rendering failures
- Provides manual retry and automatic refresh capabilities

#### API-Level Error Handling
- **Enhanced Retry Logic**: Automatic retry for 5xx errors and network failures with exponential backoff
- **Idempotency Protection**: Prevents retrying non-idempotent POST requests
- **Configurable Limits**: Maximum 3 retry attempts with delays of 1s, 2s, and 4s
- **Smart Error Classification**: Differentiates between retryable and non-retryable errors

#### Component-Level Error Handling
- Individual components implement specific error handling patterns
- User feedback through error banners and notifications
- Graceful degradation when features fail
- Clear messaging about recovery options

```mermaid
flowchart TD
Error["Error Occurs"] --> Level{"Error Level"}
Level --> |JavaScript| AppBoundary["Application ErrorBoundary"]
Level --> |API| ApiRetry["API Retry Logic"]
Level --> |Component| ComponentError["Component Error State"]
AppBoundary --> UserMsg["User-Friendly Message"]
UserMsg --> Retry["Retry Options"]
Retry --> Manual["Manual Retry"]
Retry --> Auto["Automatic Retry"]
ApiRetry --> Check{"Retry Conditions"}
Check --> |5xx Error| Backoff["Exponential Backoff"]
Check --> |Network Error| Backoff
Check --> |401| AuthRefresh["Authentication Refresh"]
Check --> |Other| FailFast["Fail Fast"]
Backoff --> Limit{"Retry Count < 3?"}
Limit --> |Yes| RetryRequest["Retry Request"]
Limit --> |No| Fail["Propagate Error"]
AuthRefresh --> RetryRequest
```

**Diagram sources**
- [ErrorBoundary.jsx:1-54](file://app/frontend/src/components/ErrorBoundary.jsx#L1-L54)
- [api.js:64-90](file://app/frontend/src/lib/api.js#L64-L90)

**Section sources**
- [ErrorBoundary.jsx:1-54](file://app/frontend/src/components/ErrorBoundary.jsx#L1-L54)
- [api.js:64-90](file://app/frontend/src/lib/api.js#L64-L90)

## Troubleshooting Guide
- Authentication issues: Verify tokens in localStorage; AuthContext clears tokens on 401; check interceptor retry flow.
- Streaming errors: analyzeResumeStream throws on invalid responses; ensure backend SSE endpoint availability.
- Usage limits: useUsageCheck returns remaining analyses and server-side checks; handle allowed=false gracefully.
- Network failures: Axios interceptors surface errors; confirm API_URL environment variable and CORS on backend.
- **Enhanced**: Error boundary failures: Check console for ErrorBoundary caught errors; verify retry logic and user feedback.
- **Enhanced**: API retry failures: Monitor retry counts and backoff delays; ensure idempotency for retryable requests.
- **Enhanced**: Global error handling: Check window.onerror and unhandledrejection handlers for uncaught exceptions.

**Section sources**
- [AuthContext.jsx:1-71](file://app/frontend/src/contexts/AuthContext.jsx#L1-L71)
- [api.js:64-90](file://app/frontend/src/lib/api.js#L64-L90)
- [Dashboard.jsx:267-275](file://app/frontend/src/pages/Dashboard.jsx#L267-L275)
- [useSubscription.jsx:164-182](file://app/frontend/src/hooks/useSubscription.jsx#L164-L182)
- [ErrorBoundary.jsx:13-15](file://app/frontend/src/components/ErrorBoundary.jsx#L13-L15)
- [main.jsx:7-14](file://app/frontend/src/main.jsx#L7-L14)

## Conclusion
The Resume AI frontend is a modular, scalable React 18 application with clear separation between routing, state, UI components, and API integration. It leverages modern tooling, robust authentication and subscription management, comprehensive error handling through ErrorBoundary components, and enhanced API retry mechanisms with exponential backoff. The architecture now provides graceful degradation, improved resilience against transient failures, and a cohesive design system to deliver a responsive, accessible, and performant user experience even under adverse conditions.