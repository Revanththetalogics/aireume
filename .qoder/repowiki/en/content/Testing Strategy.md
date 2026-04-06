# Testing Strategy

<cite>
**Referenced Files in This Document**
- [ci.yml](file://.github/workflows/ci.yml)
- [cd.yml](file://.github/workflows/cd.yml)
- [conftest.py](file://app/backend/tests/conftest.py)
- [test_api.py](file://app/backend/tests/test_api.py)
- [test_auth.py](file://app/backend/tests/test_auth.py)
- [test_subscription.py](file://app/backend/tests/test_subscription.py)
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

## Project Structure
The repository organizes tests by domain:
- Backend: tests under app/backend/tests/, driven by pytest with shared fixtures in conftest.py
- Frontend: tests under app/frontend/src/__tests__/, using Vitest and React Testing Library
- CI/CD: GitHub Actions workflows for automated test execution and deployment

```mermaid
graph TB
subgraph "Backend Tests"
B1["pytest"]
B2["FastAPI TestClient"]
B3["SQLAlchemy in-memory DB"]
B4["Shared fixtures in conftest.py"]
end
subgraph "Frontend Tests"
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
- Backend test harness
  - Shared fixtures for database, HTTP client, authentication, and service mocks
  - In-memory SQLite database with per-test lifecycle
  - Authentication fixtures that register and log in a user, injecting Authorization headers
  - Mocks for external services (Ollama, Whisper, hybrid pipeline) to isolate unit tests
  - Test data fixtures for resumes, transcripts, and subscription plans
- Frontend test harness
  - Global setup for DOM matchers
  - Mocked axios with explicit request/response spies
  - Mocked browser APIs for downloads and localStorage
  - Component tests for UploadForm, ResultCard, ScoreGauge, VideoPage
  - API module tests validating request shapes and behaviors

**Section sources**
- [conftest.py:1-589](file://app/backend/tests/conftest.py#L1-L589)
- [setup.js:1-2](file://app/frontend/src/__tests__/setup.js#L1-L2)
- [api.test.js:1-265](file://app/frontend/src/__tests__/api.test.js#L1-L265)

## Architecture Overview
The testing architecture separates concerns across layers:
- Unit tests for backend services and routes using pytest fixtures and mocked dependencies
- Component and integration tests for frontend using Vitest and React Testing Library
- CI/CD pipelines that run backend and frontend tests in parallel and upload coverage

```mermaid
sequenceDiagram
participant GH as "GitHub Actions"
participant Py as "pytest (backend)"
participant VT as "Vitest (frontend)"
participant Cov as "Codecov"
GH->>Py : "Run backend tests"
Py-->>GH : "Coverage XML"
GH->>Cov : "Upload coverage"
GH->>VT : "Run frontend tests"
VT-->>GH : "Test results"
```

**Diagram sources**
- [ci.yml:27-37](file://.github/workflows/ci.yml#L27-L37)
- [cd.yml:30-48](file://.github/workflows/cd.yml#L30-L48)

## Detailed Component Analysis

### Backend Testing with pytest
Key patterns:
- Database isolation using an in-memory SQLite engine and per-test metadata creation/drop
- HTTP client testing with FastAPI TestClient and dependency overrides
- Authentication fixtures that register/log in a user and attach Authorization headers
- Service-level mocks for external integrations (Ollama, Whisper, hybrid pipeline)
- Subscription system fixtures for seeding plans and simulating usage limits

Representative fixtures and tests:
- Database fixture: creates and tears down tables per test
- HTTP client fixture: initializes app routes and cleans up after each test
- Auth fixtures: register and login a user; return a client with Authorization header
- Mocks: Ollama communication/malpractice/transcript/email; Whisper transcription; hybrid pipeline
- Subscription fixtures: seed plans, assign plan to tenant, enforce usage limits

```mermaid
flowchart TD
Start(["Test starts"]) --> DB["Create in-memory DB tables"]
DB --> Client["Initialize TestClient and override dependencies"]
Client --> Auth["Authenticate via register/login and inject headers"]
Auth --> Mocks["Patch external services with AsyncMock/MagicMock"]
Mocks --> RouteCall["Invoke route under test"]
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

### Frontend Testing with Vitest and React Testing Library
Key patterns:
- Global setup for DOM matchers
- Mocked axios with spies for get/post/put/delete and interceptors
- Mocked browser APIs for URL.createObjectURL, revokeObjectURL, and anchor element creation
- localStorage mock for persistence behavior
- Component tests asserting rendering, interactivity, and state transitions
- API module tests verifying request shape, headers, timeouts, and download triggers

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
- [ResultCard.test.jsx:1-45](file://app/frontend/src/__tests__/ResultCard.test.jsx#L1-L45)
- [ScoreGauge.test.jsx:1-26](file://app/frontend/src/__tests__/ScoreGauge.test.jsx#L1-L26)
- [VideoPage.test.jsx:1-377](file://app/frontend/src/__tests__/VideoPage.test.jsx#L1-L377)
- [api.js:1-395](file://app/frontend/src/lib/api.js#L1-L395)

### API Testing Strategies
Backend API tests validate:
- Root and health endpoints
- Authentication endpoints (register, login, refresh, profile)
- Analysis endpoints (single and batch resume analysis)
- History and comparison endpoints
- Video analysis endpoints (upload and URL-based)
- Subscription endpoints (plans, usage checks, history, admin controls)

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

### Integration Testing Approaches
Backend integration tests:
- Use TestClient to exercise routes with real app wiring
- Override database dependency to use in-memory SQLite
- Use auth fixtures to simulate logged-in users
- Mock external services to keep tests deterministic

Frontend integration tests:
- Page-level tests (e.g., VideoPage) mock API module and router dependencies
- Validate UI interactions, state transitions, and error handling
- Ensure platform detection and supported platforms list rendering

**Section sources**
- [conftest.py:32-42](file://app/backend/tests/conftest.py#L32-L42)
- [VideoPage.test.jsx:1-377](file://app/frontend/src/__tests__/VideoPage.test.jsx#L1-L377)

### Test Configuration and Mock Services
Backend:
- PYTHONPATH set in CI to resolve imports
- pytest-cov enabled for coverage reporting
- Shared fixtures centralize DB setup, auth, and service mocks

Frontend:
- Vitest configuration via package.json scripts
- DOM matchers via jest-dom
- Mocked axios and browser APIs in api.test.js setup

**Section sources**
- [ci.yml:25-58](file://.github/workflows/ci.yml#L25-L58)
- [package.json:6-12](file://app/frontend/package.json#L6-L12)
- [api.test.js:1-265](file://app/frontend/src/__tests__/api.test.js#L1-L265)

### Test Data Management
Backend:
- Sample resume text and job description fixtures
- Minimal MP4 bytes for file-type validation
- Transcript fixtures (VTT, SRT, plain text)
- Subscription plan fixtures with seeded limits and features

Frontend:
- Mock result objects for video analysis (low and high risk)
- Component props populated with mock data

**Section sources**
- [conftest.py:294-421](file://app/backend/tests/conftest.py#L294-L421)
- [VideoPage.test.jsx:28-86](file://app/frontend/src/__tests__/VideoPage.test.jsx#L28-L86)

### Continuous Integration Testing with GitHub Actions
Workflows:
- ci.yml: runs backend tests with coverage and uploads to Codecov; runs frontend tests and builds
- cd.yml: runs backend and frontend tests as part of build-and-push images job

Execution:
- Python 3.11 and Node.js 20 environments
- Backend coverage collected for services package
- Frontend tests executed via npm test

**Section sources**
- [ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

### Writing Effective Tests for New Features
Guidelines derived from existing tests:
- Backend
  - Use pytest fixtures to minimize duplication (db, client, auth_client)
  - Prefer AsyncMock/MagicMock for external services to avoid flaky network calls
  - Validate both success and failure paths (e.g., invalid file types, missing fields)
  - For subscription features, use seed fixtures and tenant plan assignments
- Frontend
  - Mock axios and browser APIs to focus on component behavior
  - Test user interactions (clicks, input changes) and resulting UI updates
  - Validate request shapes, headers, and timeouts for API calls
  - Ensure error messages are surfaced and handled gracefully

**Section sources**
- [conftest.py:125-176](file://app/backend/tests/conftest.py#L125-L176)
- [test_api.py:71-87](file://app/backend/tests/test_api.py#L71-L87)
- [api.test.js:167-200](file://app/frontend/src/__tests__/api.test.js#L167-L200)

## Dependency Analysis
Backend test dependencies:
- pytest, FastAPI TestClient, SQLAlchemy in-memory DB, passlib sha256_crypt for bcrypt compatibility
- External service mocks via unittest.mock

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
- Frontend
  - Avoid real network calls by mocking axios
  - Use minimal DOM queries and focus on user-centric assertions
  - Prefer component-level tests over full-page integration tests when feasible

## Troubleshooting Guide
Common issues and resolutions:
- Authentication failures in backend tests
  - Ensure auth_client fixture registers and logs in a user before invoking protected routes
  - Verify Authorization header is attached to the client
- Coverage not uploaded
  - Confirm pytest-cov is installed and coverage report path matches workflow configuration
- Frontend tests failing due to missing mocks
  - Ensure global setup mocks are applied before importing modules under test
  - Clear mocks between tests to prevent cross-contamination
- CI failures on Windows/Linux differences
  - Use provided scripts to validate imports, migrations, and frontend files before pushing
  - Align Node/npm versions with CI configuration

**Section sources**
- [test-locally.ps1:36-96](file://test-locally.ps1#L36-L96)
- [run-full-tests.sh:163-168](file://scripts/run-full-tests.sh#L163-L168)
- [run-full-tests.bat:100-107](file://scripts/run-full-tests.bat#L100-L107)

## Conclusion
The testing strategy leverages pytest and FastAPI TestClient for backend unit and integration tests, with comprehensive fixtures and service mocks. Frontend tests use Vitest and React Testing Library with mocked axios and DOM APIs. CI/CD pipelines automate test execution and coverage reporting. By following the established patterns and guidelines, contributors can reliably add new tests and maintain high coverage.

## Appendices

### Appendix A: Local Test Execution Scripts
- run-full-tests.sh: Validates Python syntax, imports, migrations, database models, route registration, and frontend files; useful for pre-commit checks
- run-full-tests.bat: Windows counterpart to run-full-tests.sh
- test-locally.ps1: Runs backend and frontend tests locally with colored output and summarized results

**Section sources**
- [run-full-tests.sh:1-256](file://scripts/run-full-tests.sh#L1-L256)
- [run-full-tests.bat:1-274](file://scripts/run-full-tests.bat#L1-L274)
- [test-locally.ps1:1-119](file://test-locally.ps1#L1-L119)