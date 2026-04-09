# Testing Strategy

<cite>
**Referenced Files in This Document**
- [ci.yml](file://.github/workflows/ci.yml)
- [cd.yml](file://.github/workflows/cd.yml)
- [conftest.py](file://app/backend/tests/conftest.py)
- [test_api.py](file://app/backend/tests/test_api.py)
- [test_auth.py](file://app/backend/tests/test_auth.py)
- [test_subscription.py](file://app/backend/tests/test_subscription.py)
- [test_llm_service.py](file://app/backend/tests/test_llm_service.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)
- [test_agent_pipeline.py](file://app/backend/tests/test_agent_pipeline.py)
- [test_analysis_service.py](file://app/backend/tests/test_analysis_service.py)
- [test_transcript_service.py](file://app/backend/tests/test_transcript_service.py)
- [test_transcript_api.py](file://app/backend/tests/test_transcript_api.py)
- [test_video_service.py](file://app/backend/tests/test_video_service.py)
- [test_video_routes.py](file://app/backend/tests/test_video_routes.py)
- [test_video_downloader.py](file://app/backend/tests/test_video_downloader.py)
- [test_parser_service.py](file://app/backend/tests/test_parser_service.py)
- [test_gap_detector.py](file://app/backend/tests/test_gap_detector.py)
- [test_candidate_dedup.py](file://app/backend/tests/test_candidate_dedup.py)
- [test_routes_phase1.py](file://app/backend/tests/test_routes_phase1.py)
- [test_routes_phase2.py](file://app/backend/tests/test_routes_phase2.py)
- [test_usage_enforcement.py](file://app/backend/tests/test_usage_enforcement.py)
- [test_llm_json_parse.py](file://app/backend/tests/test_llm_json_parse.py)
- [run-full-tests.sh](file://scripts/run-full-tests.sh)
- [run-full-tests.bat](file://scripts/run-full-tests.bat)
- [test-locally.ps1](file://test-locally.ps1)
- [setup.js](file://app/frontend/src/__tests__/setup.js)
- [api.test.js](file://app/frontend/src/__tests__/api.test.js)
- [UploadForm.test.jsx](file://app/frontend/src/__tests__/UploadForm.test.jsx)
- [ResultCard.test.jsx](file://app/frontend/src/__tests__/ResultCard.test.jsx)
- [ScoreGauge.test.jsx](file://app/frontend/src/__tests__/ScoreGauge.test.jsx)
- [VideoPage.test.jsx](file://app/frontend/src/__tests__/VideoPage.test.jsx)
- [api.js](file://app/frontend/src/lib/api.js)
- [package.json](file://app/frontend/package.json)
</cite>

## Update Summary
**Changes Made**
- Significantly expanded test suite with 73+ new tests covering LLM service, authentication flows, API endpoints, and integration scenarios
- Enhanced coverage of error handling, retry mechanisms, and background task processing
- Added comprehensive testing for LLM service layer, hybrid pipeline, agent pipeline, and analysis service
- Expanded transcript service and video processing test coverage
- Enhanced subscription and usage enforcement testing
- Improved test fixtures for better isolation and reliability

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
This document defines a comprehensive testing strategy for Resume AI by ThetaLogics. It covers backend testing with pytest, frontend testing with Vitest and React Testing Library, API and integration testing patterns, test configuration and mocking, test data management, performance testing, end-to-end workflows, continuous integration with GitHub Actions, and best practices for writing maintainable tests.

**Updated** Significantly expanded test suite now includes 73+ new tests covering LLM service layer, authentication flows, API endpoints, and integration scenarios with enhanced error handling, retry mechanisms, and background task processing.

## Project Structure
The repository organizes tests by domain with a comprehensive test suite:
- Backend: extensive tests under app/backend/tests/ covering all major components with shared fixtures in conftest.py
- Frontend: component and integration tests under app/frontend/src/__tests__/ using Vitest and React Testing Library
- CI/CD: GitHub Actions workflows for automated test execution and deployment

```mermaid
graph TB
subgraph "Backend Test Suite (73+ tests)"
B1["pytest"]
B2["FastAPI TestClient"]
B3["SQLAlchemy in-memory DB"]
B4["Shared fixtures in conftest.py"]
B5["LLM Service Tests"]
B6["Pipeline Tests"]
B7["Service Layer Tests"]
B8["Integration Tests"]
end
subgraph "Frontend Test Suite"
F1["Vitest"]
F2["React Testing Library"]
F3["Mocked axios and DOM APIs"]
end
subgraph "CI/CD"
C1[".github/workflows/ci.yml"]
C2[".github/workflows/cd.yml"]
end
B1 --> B2
B1 --> B3
B1 --> B4
B1 --> B5
B1 --> B6
B1 --> B7
B1 --> B8
F1 --> F2
F1 --> F3
C1 --> B1
C1 --> F1
C2 --> B1
C2 --> F1
```

**Diagram sources**
- [ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)
- [conftest.py:1-589](file://app/backend/tests/conftest.py#L1-L589)
- [api.test.js:1-265](file://app/frontend/src/__tests__/api.test.js#L1-L265)

**Section sources**
- [ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

## Core Components
- Backend test harness with comprehensive fixture system
  - Shared fixtures for database, HTTP client, authentication, and service mocks
  - In-memory SQLite database with per-test lifecycle
  - Authentication fixtures that register and log in users, injecting Authorization headers
  - Mocks for external services (Ollama, Whisper, hybrid pipeline) to isolate unit tests
  - Extensive test data fixtures for resumes, transcripts, and subscription plans
  - Specialized fixtures for LLM service testing, pipeline validation, and error scenarios
- Frontend test harness
  - Global setup for DOM matchers
  - Mocked axios with explicit request/response spies
  - Mocked browser APIs for downloads and localStorage
  - Component tests for UploadForm, ResultCard, ScoreGauge, VideoPage
  - API module tests validating request shapes and behaviors

**Updated** Significantly enhanced with 73+ new tests covering LLM service layer, authentication flows, API endpoints, and integration scenarios with comprehensive error handling and retry mechanisms.

**Section sources**
- [conftest.py:1-589](file://app/backend/tests/conftest.py#L1-L589)
- [setup.js:1-2](file://app/frontend/src/__tests__/setup.js#L1-L2)
- [api.test.js:1-265](file://app/frontend/src/__tests__/api.test.js#L1-L265)

## Architecture Overview
The testing architecture separates concerns across layers with comprehensive coverage:
- Unit tests for backend services and routes using pytest fixtures and mocked dependencies
- Component and integration tests for frontend using Vitest and React Testing Library
- CI/CD pipelines that run backend and frontend tests in parallel and upload coverage
- Specialized testing for LLM services, pipelines, and background task processing

```mermaid
sequenceDiagram
participant GH as "GitHub Actions"
participant Py as "pytest (backend - 73+ tests)"
participant VT as "Vitest (frontend)"
participant Cov as "Codecov"
GH->>Py : "Run comprehensive backend tests"
Py-->>GH : "Coverage XML"
GH->>Cov : "Upload coverage"
GH->>VT : "Run frontend tests"
VT-->>GH : "Test results"
```

**Diagram sources**
- [ci.yml:27-37](file://.github/workflows/ci.yml#L27-L37)
- [cd.yml:30-48](file://.github/workflows/cd.yml#L30-L48)

## Detailed Component Analysis

### Backend Testing with pytest - Comprehensive Test Suite
Key patterns with expanded coverage:
- Database isolation using an in-memory SQLite engine and per-test metadata creation/drop
- HTTP client testing with FastAPI TestClient and dependency overrides
- Authentication fixtures that register/log in users and attach Authorization headers
- Service-level mocks for external integrations (Ollama, Whisper, hybrid pipeline)
- Subscription system fixtures for seeding plans and simulating usage limits
- **New**: LLM service testing with specialized fixtures for JSON parsing and error handling
- **New**: Pipeline testing covering hybrid and agent pipeline validation
- **New**: Transcript service and video processing comprehensive testing
- **New**: Background task and retry mechanism testing

Representative fixtures and expanded test coverage:
- Database fixture: creates and tears down tables per test
- HTTP client fixture: initializes app routes and cleans up after each test
- Auth fixtures: register and login users; return clients with Authorization headers
- Mocks: Ollama communication/malpractice/transcript/email; Whisper transcription; hybrid pipeline
- Subscription fixtures: seed plans, assign plans to tenants, enforce usage limits
- **New**: LLM service fixtures for JSON parsing validation and error scenarios
- **New**: Pipeline fixtures for hybrid and agent pipeline testing
- **New**: Transcript and video processing fixtures with comprehensive mocking

```mermaid
flowchart TD
Start(["Test starts"]) --> DB["Create in-memory DB tables"]
DB --> Client["Initialize TestClient and override dependencies"]
Client --> Auth["Authenticate via register/login and inject headers"]
Auth --> Mocks["Patch external services with AsyncMock/MagicMock"]
Mocks --> LLM["Test LLM service layer"]
LLM --> Pipelines["Test hybrid/agent pipelines"]
Pipelines --> Services["Test analysis/transcript/video services"]
Services --> RouteCall["Invoke route under test"]
RouteCall --> Asserts["Assert response status and payload"]
Asserts --> Cleanup["Drop DB tables and close sessions"]
Cleanup --> End(["Test ends"])
```

**Diagram sources**
- [conftest.py:57-123](file://app/backend/tests/conftest.py#L57-L123)
- [test_api.py:23-100](file://app/backend/tests/test_api.py#L23-L100)

**Section sources**
- [conftest.py:57-123](file://app/backend/tests/conftest.py#L57-L123)
- [test_api.py:23-100](file://app/backend/tests/test_api.py#L23-L100)
- [test_auth.py:15-95](file://app/backend/tests/test_auth.py#L15-L95)
- [test_subscription.py:12-132](file://app/backend/tests/test_subscription.py#L12-L132)
- [test_llm_service.py](file://app/backend/tests/test_llm_service.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)
- [test_agent_pipeline.py](file://app/backend/tests/test_agent_pipeline.py)
- [test_analysis_service.py](file://app/backend/tests/test_analysis_service.py)
- [test_transcript_service.py](file://app/backend/tests/test_transcript_service.py)
- [test_video_service.py](file://app/backend/tests/test_video_service.py)

### Frontend Testing with Vitest and React Testing Library
Key patterns with enhanced component coverage:
- Global setup for DOM matchers
- Mocked axios with spies for get/post/put/delete and interceptors
- Mocked browser APIs for URL.createObjectURL, revokeObjectURL, and anchor element creation
- localStorage mock for persistence behavior
- Component tests asserting rendering, interactivity, and state transitions
- API module tests verifying request shape, headers, timeouts, and download triggers
- **Enhanced**: Comprehensive ResultCard testing with AI pipeline feature validation

```mermaid
sequenceDiagram
participant Test as "Vitest test"
participant Comp as "Component"
participant RT as "React Testing Library"
participant API as "api.js"
participant AX as "Mocked axios"
Test->>Comp : "render(...)"
Test->>RT : "fireEvent / getByRole"
Comp->>API : "call exported function"
API->>AX : "axios.post/get with config"
AX-->>API : "resolved/rejected promise"
API-->>Comp : "return data"
Comp-->>Test : "DOM updates observed"
```

**Diagram sources**
- [api.test.js:5-66](file://app/frontend/src/__tests__/api.test.js#L5-L66)
- [UploadForm.test.jsx:1-60](file://app/frontend/src/__tests__/UploadForm.test.jsx#L1-L60)
- [VideoPage.test.jsx:6-26](file://app/frontend/src/__tests__/VideoPage.test.jsx#L6-L26)

**Section sources**
- [setup.js:1-2](file://app/frontend/src/__tests__/setup.js#L1-L2)
- [api.test.js:1-265](file://app/frontend/src/__tests__/api.test.js#L1-L265)
- [UploadForm.test.jsx:1-60](file://app/frontend/src/__tests__/UploadForm.test.jsx#L1-L60)
- [ResultCard.test.jsx:1-133](file://app/frontend/src/__tests__/ResultCard.test.jsx#L1-L133)
- [ScoreGauge.test.jsx:1-26](file://app/frontend/src/__tests__/ScoreGauge.test.jsx#L1-L26)
- [VideoPage.test.jsx:1-377](file://app/frontend/src/__tests__/VideoPage.test.jsx#L1-L377)
- [api.js:1-395](file://app/frontend/src/lib/api.js#L1-L395)

### API Testing Strategies - Expanded Coverage
Backend API tests now validate comprehensive endpoint coverage:
- Root and health endpoints
- Authentication endpoints (register, login, refresh, profile)
- Analysis endpoints (single and batch resume analysis)
- History and comparison endpoints
- Video analysis endpoints (upload and URL-based)
- Subscription endpoints (plans, usage checks, history, admin controls)
- **New**: Transcript analysis endpoints with comprehensive validation
- **New**: Background task and retry mechanism endpoints
- **New**: Usage enforcement and rate limiting endpoints

Frontend API tests validate:
- Export CSV/Excel requests and download behavior
- Video analysis requests with appropriate timeouts
- Resume analysis requests with multipart/form-data
- Candidate and template endpoints
- Subscription endpoints

```mermaid
flowchart TD
A["Route under test"] --> B["Validate request shape and headers"]
B --> C{"External service used?"}
C --> |Yes| D["Patch with AsyncMock/MagicMock"]
C --> |No| E["Use real service"]
D --> F["Invoke handler"]
E --> F
F --> G["Assert status and payload"]
```

**Diagram sources**
- [test_api.py:23-153](file://app/backend/tests/test_api.py#L23-L153)
- [api.test.js:76-263](file://app/frontend/src/__tests__/api.test.js#L76-L263)

**Section sources**
- [test_api.py:1-153](file://app/backend/tests/test_api.py#L1-L153)
- [api.test.js:1-265](file://app/frontend/src/__tests__/api.test.js#L1-L265)

### Integration Testing Approaches - Comprehensive Coverage
Backend integration tests now cover:
- Use TestClient to exercise routes with real app wiring
- Override database dependency to use in-memory SQLite
- Use auth fixtures to simulate logged-in users
- Mock external services to keep tests deterministic
- **New**: LLM service integration testing with error handling scenarios
- **New**: Pipeline integration testing with retry mechanisms
- **New**: Background task processing validation
- **New**: Subscription and usage enforcement integration

Frontend integration tests:
- Page-level tests (e.g., VideoPage) mock API module and router dependencies
- Validate UI interactions, state transitions, and error handling
- Ensure platform detection and supported platforms list rendering
- **Enhanced**: Comprehensive AI pipeline feature integration testing

**Section sources**
- [conftest.py:32-42](file://app/backend/tests/conftest.py#L32-L42)
- [VideoPage.test.jsx:1-377](file://app/frontend/src/__tests__/VideoPage.test.jsx#L1-L377)

### Test Configuration and Mock Services - Enhanced Infrastructure
Backend:
- PYTHONPATH set in CI to resolve imports
- pytest-cov enabled for comprehensive coverage reporting
- Shared fixtures centralize DB setup, auth, and service mocks
- **New**: Specialized fixtures for LLM service testing and pipeline validation
- **New**: Enhanced error handling and retry mechanism testing infrastructure

Frontend:
- Vitest configuration via package.json scripts
- DOM matchers via jest-dom
- Mocked axios and browser APIs in api.test.js setup

**Section sources**
- [ci.yml:25-58](file://.github/workflows/ci.yml#L25-L58)
- [package.json:6-12](file://app/frontend/package.json#L6-L12)
- [api.test.js:1-265](file://app/frontend/src/__tests__/api.test.js#L1-L265)

### Test Data Management - Comprehensive Coverage
Backend:
- Sample resume text and job description fixtures
- Minimal MP4 bytes for file-type validation
- Transcript fixtures (VTT, SRT, plain text)
- Subscription plan fixtures with seeded limits and features
- **New**: LLM service test data with JSON parsing scenarios
- **New**: Pipeline test data with error conditions and edge cases
- **New**: Transcript and video processing test fixtures

Frontend:
- Mock result objects for video analysis (low and high risk)
- Component props populated with mock data
- **Enhanced**: Comprehensive AI pipeline result objects with explainability features

**Section sources**
- [conftest.py:294-421](file://app/backend/tests/conftest.py#L294-L421)
- [VideoPage.test.jsx:28-86](file://app/frontend/src/__tests__/VideoPage.test.jsx#L28-L86)

### Continuous Integration Testing with GitHub Actions
Workflows:
- ci.yml: runs backend tests with comprehensive coverage and uploads to Codecov; runs frontend tests and builds
- cd.yml: runs backend and frontend tests as part of build-and-push images job

Execution:
- Python 3.11 and Node.js 20 environments
- Backend coverage collected for services package with 73+ test suite
- Frontend tests executed via npm test

**Section sources**
- [ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

### Writing Effective Tests for New Features - Enhanced Guidelines
Guidelines derived from expanded test suite:
- Backend
  - Use pytest fixtures to minimize duplication (db, client, auth_client)
  - Prefer AsyncMock/MagicMock for external services to avoid flaky network calls
  - Validate both success and failure paths (e.g., invalid file types, missing fields)
  - For subscription features, use seed fixtures and tenant plan assignments
  - **New**: Test LLM service error handling and retry mechanisms
  - **New**: Validate pipeline processing with comprehensive edge cases
  - **New**: Test background task processing and queue handling
- Frontend
  - Mock axios and browser APIs to focus on component behavior
  - Test user interactions (clicks, input changes) and resulting UI updates
  - Validate request shapes, headers, and timeouts for API calls
  - Ensure error messages are surfaced and handled gracefully
  - **Enhanced**: Test AI pipeline explainability and risk analysis features

**Section sources**
- [conftest.py:125-176](file://app/backend/tests/conftest.py#L125-L176)
- [test_api.py:71-87](file://app/backend/tests/test_api.py#L71-L87)
- [api.test.js:167-200](file://app/frontend/src/__tests__/api.test.js#L167-L200)

## Dependency Analysis
Backend test dependencies with expanded coverage:
- pytest, FastAPI TestClient, SQLAlchemy in-memory DB, passlib sha256_crypt for bcrypt compatibility
- External service mocks via unittest.mock
- **New**: Enhanced LLM service testing dependencies and specialized fixtures

Frontend test dependencies:
- Vitest, React Testing Library, jest-dom
- Mocked axios and DOM APIs

```mermaid
graph LR
Py["pytest"] --> FA["FastAPI TestClient"]
Py --> SA["SQLAlchemy in-memory DB"]
Py --> UM["unittest.mock"]
VT["Vitest"] --> RTL["React Testing Library"]
VT --> AX["Mocked axios"]
VT --> DOM["Mocked DOM APIs"]
```

**Diagram sources**
- [conftest.py:1-12](file://app/backend/tests/conftest.py#L1-L12)
- [package.json:23-38](file://app/frontend/package.json#L23-L38)

**Section sources**
- [conftest.py:1-12](file://app/backend/tests/conftest.py#L1-L12)
- [package.json:23-38](file://app/frontend/package.json#L23-L38)

## Performance Considerations
- Backend
  - Use in-memory SQLite to avoid disk I/O overhead
  - Keep external service mocks synchronous where possible to reduce test runtime
  - Limit heavy computations in tests; rely on mocks for LLM and transcription services
  - **New**: Optimize LLM service testing with efficient mock implementations
  - **New**: Minimize pipeline testing overhead with focused fixtures
- Frontend
  - Avoid real network calls by mocking axios
  - Use minimal DOM queries and focus on user-centric assertions
  - Prefer component-level tests over full-page integration tests when feasible
  - **Enhanced**: Optimize AI pipeline feature testing with selective mocking

## Troubleshooting Guide
Common issues and resolutions with expanded test coverage:
- Authentication failures in backend tests
  - Ensure auth_client fixture registers and logs in users before invoking protected routes
  - Verify Authorization header is attached to the client
- Coverage not uploaded
  - Confirm pytest-cov is installed and coverage report path matches workflow configuration
- Frontend tests failing due to missing mocks
  - Ensure global setup mocks are applied before importing modules under test
  - Clear mocks between tests to prevent cross-contamination
- CI failures on Windows/Linux differences
  - Use provided scripts to validate imports, migrations, and frontend files before pushing
  - Align Node/npm versions with CI configuration
- **New**: LLM service test failures
  - Verify JSON parsing fixtures and error handling scenarios
  - Check mock responses match expected LLM service interface
- **New**: Pipeline testing issues
  - Ensure pipeline fixtures properly mock external dependencies
  - Validate error scenarios and retry mechanisms
- **New**: Background task testing problems
  - Verify task queue mocking and background process simulation
  - Check retry mechanism validation and error propagation

**Section sources**
- [test-locally.ps1:36-96](file://test-locally.ps1#L36-L96)
- [run-full-tests.sh:163-168](file://scripts/run-full-tests.sh#L163-L168)
- [run-full-tests.bat:100-107](file://scripts/run-full-tests.bat#L100-L107)

## Conclusion
The testing strategy leverages pytest and FastAPI TestClient for comprehensive backend unit and integration tests, with significantly expanded coverage including 73+ new tests for LLM services, pipelines, and integration scenarios. Frontend tests use Vitest and React Testing Library with mocked axios and DOM APIs. CI/CD pipelines automate test execution and coverage reporting. The expanded test suite ensures robust validation of advanced features including error handling, retry mechanisms, and background task processing, providing reliable coverage for all major components.

## Appendices

### Appendix A: Local Test Execution Scripts
- run-full-tests.sh: Validates Python syntax, imports, migrations, database models, route registration, and frontend files; useful for pre-commit checks
- run-full-tests.bat: Windows counterpart to run-full-tests.sh
- test-locally.ps1: Runs backend and frontend tests locally with colored output and summarized results

**Section sources**
- [run-full-tests.sh:1-256](file://scripts/run-full-tests.sh#L1-L256)
- [run-full-tests.bat:1-274](file://scripts/run-full-tests.bat#L1-L274)
- [test-locally.ps1:1-119](file://test-locally.ps1#L1-L119)

### Appendix B: Enhanced Test Coverage Areas
The expanded test suite now includes comprehensive coverage for:

- **LLM Service Testing**: Dedicated tests for LLM service layer with JSON parsing validation and error handling scenarios
- **Pipeline Testing**: Comprehensive testing for hybrid and agent pipelines with retry mechanisms and background task processing
- **Analysis Service Testing**: Validation of analysis service functionality with error scenarios and edge cases
- **Transcript Service Testing**: Complete coverage of transcript processing with multiple formats and error handling
- **Video Processing Testing**: End-to-end testing of video analysis workflows with downloader and service validation
- **Subscription and Usage Testing**: Comprehensive validation of subscription system, usage enforcement, and rate limiting
- **Background Task Testing**: Validation of asynchronous task processing and queue management
- **Error Handling Testing**: Extensive testing of error scenarios, retry mechanisms, and graceful degradation
- **Integration Testing**: End-to-end testing of complex workflows and cross-service interactions

**Section sources**
- [test_llm_service.py](file://app/backend/tests/test_llm_service.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)
- [test_agent_pipeline.py](file://app/backend/tests/test_agent_pipeline.py)
- [test_analysis_service.py](file://app/backend/tests/test_analysis_service.py)
- [test_transcript_service.py](file://app/backend/tests/test_transcript_service.py)
- [test_transcript_api.py](file://app/backend/tests/test_transcript_api.py)
- [test_video_service.py](file://app/backend/tests/test_video_service.py)
- [test_video_routes.py](file://app/backend/tests/test_video_routes.py)
- [test_video_downloader.py](file://app/backend/tests/test_video_downloader.py)
- [test_parser_service.py](file://app/backend/tests/test_parser_service.py)
- [test_gap_detector.py](file://app/backend/tests/test_gap_detector.py)
- [test_candidate_dedup.py](file://app/backend/tests/test_candidate_dedup.py)
- [test_routes_phase1.py](file://app/backend/tests/test_routes_phase1.py)
- [test_routes_phase2.py](file://app/backend/tests/test_routes_phase2.py)
- [test_usage_enforcement.py](file://app/backend/tests/test_usage_enforcement.py)
- [test_llm_json_parse.py](file://app/backend/tests/test_llm_json_parse.py)