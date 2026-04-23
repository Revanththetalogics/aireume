# Testing Strategy

<cite>
**Referenced Files in This Document**
- [ci.yml](file://.github/workflows/ci.yml)
- [cd.yml](file://.github/workflows/cd.yml)
- [conftest.py](file://app/backend/tests/conftest.py)
- [rate_limit.py](file://app/backend/middleware/rate_limit.py)
- [subscription.py](file://app/backend/routes/subscription.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [test_rate_limiting.py](file://app/backend/tests/test_rate_limiting.py)
- [test_subscription.py](file://app/backend/tests/test_subscription.py)
- [test_quota_enforcement.py](file://app/backend/tests/test_quota_enforcement.py)
- [test_usage_enforcement.py](file://app/backend/tests/test_usage_enforcement.py)
- [run-full-tests.sh](file://scripts/run-full-tests.sh)
- [test-locally.ps1](file://test-locally.ps1)
- [.gitignore](file://.gitignore)
</cite>

## Update Summary
**Changes Made**
- Enhanced rate limiter reset mechanism with improved CI stability through comprehensive test infrastructure cleanup
- Added systematic cleanup of temporary test output files and refined .gitignore patterns to exclude test artifacts
- Implemented automatic rate limit bucket clearing in test fixtures to prevent 429 errors in CI environments
- Strengthened monthly usage reset functionality with comprehensive test coverage for subscription system
- Improved CI/CD stability through better test artifact management and cleaner test execution environments

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

**Updated** The test suite has been substantially enhanced with improved rate limiter reset mechanisms, comprehensive CI stability improvements, and systematic cleanup of temporary test artifacts. The enhanced infrastructure ensures reliable test execution in CI environments while maintaining comprehensive coverage of administrative APIs, billing systems, email services, feature flags, quota enforcement, rate limiting, tenant suspension, and webhooks.

## Project Structure
The repository organizes tests by domain with enhanced infrastructure:
- Backend: extensive tests under app/backend/tests/ covering all major components with shared fixtures in conftest.py, now including sophisticated rate limiter reset mechanisms and comprehensive CI stability improvements
- Frontend: component and integration tests under app/frontend/src/__tests__/ using Vitest and React Testing Library
- CI/CD: GitHub Actions workflows for automated test execution and deployment with improved stability

```mermaid
graph TB
subgraph "Backend Test Suite (Enhanced Infrastructure)"
B1["pytest"]
B2["FastAPI TestClient"]
B3["SQLAlchemy in-memory DB"]
B4["Shared fixtures in conftest.py"]
B5["Rate Limiter Reset Mechanism"]
B6["Monthly Usage Reset System"]
B7["CI Stability Improvements"]
B8["Test Artifact Cleanup"]
B9["Queue System Tests"]
B10["Administrative API Tests"]
end
subgraph "Frontend Test Suite"
F1["Vitest"]
F2["React Testing Library"]
F3["Mocked axios and DOM APIs"]
end
subgraph "CI/CD"
C1[".github/workflows/ci.yml"]
C2[".github/workflows/cd.yml"]
C3[".gitignore (Enhanced Patterns)"]
end
B1 --> B2
B1 --> B3
B1 --> B4
B1 --> B5
B1 --> B6
B1 --> B7
B1 --> B8
B1 --> B9
B1 --> B10
F1 --> F2
F1 --> F3
C1 --> B1
C1 --> F1
C2 --> B1
C2 --> F1
C3 --> B8
```

**Diagram sources**
- [ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)
- [conftest.py:196-204](file://app/backend/tests/conftest.py#L196-L204)
- [rate_limit.py:196-204](file://app/backend/middleware/rate_limit.py#L196-L204)
- [subscription.py:85-97](file://app/backend/routes/subscription.py#L85-L97)

**Section sources**
- [ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)
- [.gitignore:42-47](file://.gitignore#L42-L47)

## Core Components
- Backend test harness with enhanced fixture system and rate limiter reset mechanisms
  - Shared fixtures for database, HTTP client, authentication, and service mocks
  - In-memory SQLite database with per-test lifecycle and sophisticated queue table management
  - Authentication fixtures that register and log in users, injecting Authorization headers
  - Mocks for external services (Ollama, Whisper, hybrid pipeline) to isolate unit tests
  - Extensive test data fixtures for resumes, transcripts, and subscription plans
  - Specialized fixtures for LLM service testing, pipeline validation, and error scenarios
  - **Enhanced**: Sophisticated queue system database infrastructure with custom table creation/destruction
  - **Enhanced**: AsyncMock-based queue worker mocking to prevent database access during tests
  - **Enhanced**: Automatic rate limiter bucket clearing in test fixtures to prevent CI 429 errors
  - **Enhanced**: Comprehensive monthly usage reset testing with edge case validation
  - **New**: Administrative API fixtures for tenant management and billing operations
  - **New**: Billing provider fixtures for Stripe, Razorpay, and manual payment processing
  - **New**: Email service fixtures for SMTP configuration and notification testing
  - **New**: Feature flag fixtures for tenant overrides and permission testing
  - **New**: Quota enforcement fixtures for subscription plan validation
  - **New**: Rate limiting fixtures for API throttling and abuse prevention
  - **New**: Tenant suspension fixtures for audit logging and recovery workflows
  - **New**: Webhook fixtures for payment processor event handling
- Frontend test harness
  - Global setup for DOM matchers
  - Mocked axios with explicit request/response spies
  - Mocked browser APIs for downloads and localStorage
  - Component tests for UploadForm, ResultCard, ScoreGauge, VideoPage
  - API module tests validating request shapes and behaviors

**Updated** The test suite now emphasizes comprehensive coverage of administrative operations, billing integrations, and operational monitoring with enhanced CI stability through systematic rate limiter reset mechanisms and test artifact cleanup. The expanded testing infrastructure ensures robust validation of the new administrative and billing functionality with 73+ existing tests plus numerous new test suites covering critical operational aspects.

**Section sources**
- [conftest.py:196-204](file://app/backend/tests/conftest.py#L196-L204)
- [rate_limit.py:16-144](file://app/backend/middleware/rate_limit.py#L16-L144)
- [subscription.py:85-97](file://app/backend/routes/subscription.py#L85-L97)
- [test_rate_limiting.py:1-85](file://app/backend/tests/test_rate_limiting.py#L1-L85)
- [test_subscription.py:312-355](file://app/backend/tests/test_subscription.py#L312-L355)

## Architecture Overview
The testing architecture separates concerns across layers with enhanced CI stability:
- Unit tests for backend services and routes using pytest fixtures and mocked dependencies
- Component and integration tests for frontend using Vitest and React Testing Library
- CI/CD pipelines that run backend and frontend tests in parallel and upload coverage
- Specialized testing for LLM services, pipelines, and background task processing
- **Enhanced**: Comprehensive queue system testing with dedicated database infrastructure
- **Enhanced**: Automatic rate limiter reset mechanisms to prevent CI instability
- **Enhanced**: Systematic test artifact cleanup for improved CI reliability
- **New**: Administrative API testing with tenant management and billing operations
- **New**: Billing system testing with provider abstraction and webhook handling
- **New**: Email service testing with SMTP configuration and notification delivery
- **New**: Feature flag testing with tenant overrides and permission enforcement
- **New**: Operational monitoring testing with quota enforcement and rate limiting

```mermaid
sequenceDiagram
participant GH as "GitHub Actions"
participant Py as "pytest (backend - enhanced stability)"
participant VT as "Vitest (frontend)"
participant Clean as "Artifact Cleanup"
participant RL as "Rate Limiter Reset"
GH->>Clean : "Setup test environment"
Clean->>RL : "Initialize rate limiter buckets"
RL->>Py : "Run comprehensive backend tests"
Py-->>GH : "Coverage XML"
GH->>VT : "Run frontend tests"
VT-->>GH : "Test results"
```

**Diagram sources**
- [ci.yml:27-37](file://.github/workflows/ci.yml#L27-L37)
- [cd.yml:30-48](file://.github/workflows/cd.yml#L30-L48)
- [conftest.py:196-204](file://app/backend/tests/conftest.py#L196-L204)

## Detailed Component Analysis

### Backend Testing with pytest - Enhanced Infrastructure
Key patterns with enhanced CI stability:
- Database isolation using an in-memory SQLite engine and per-test metadata creation/drop
- **Enhanced**: Sophisticated queue table creation using raw SQL to avoid FK resolution issues
- HTTP client testing with FastAPI TestClient and dependency overrides
- Authentication fixtures that register/log in users and attach Authorization headers
- Service-level mocks for external integrations (Ollama, Whisper, hybrid pipeline)
- Subscription system fixtures for seeding plans and simulating usage limits
- **Enhanced**: Automatic rate limiter bucket clearing using autouse fixtures to prevent CI 429 errors
- **Enhanced**: Comprehensive monthly usage reset testing with edge case validation
- **New**: Administrative API testing with comprehensive tenant management validation
- **New**: Billing system testing with provider abstraction and webhook processing
- **New**: Email service testing with SMTP configuration and notification delivery
- **New**: Feature flag testing with tenant overrides and permission enforcement
- **New**: Quota enforcement testing with subscription plan validation
- **New**: Rate limiting testing with API throttling and abuse prevention
- **New**: Tenant suspension testing with audit logging and recovery workflows
- **New**: Webhook testing with payment processor event handling
- **Enhanced**: Queue system testing with comprehensive database schema support

Representative fixtures and enhanced test coverage:
- Database fixture: creates and tears down tables per test with queue system support
- HTTP client fixture: initializes app routes and cleans up after each test
- Auth fixtures: register and login users; return clients with Authorization headers
- Mocks: Ollama communication/malpractice/transcript/email; Whisper transcription; hybrid pipeline
- Subscription fixtures: seed plans, assign plans to tenants, enforce usage limits
- **Enhanced**: Rate limiter reset fixture: automatically clears token buckets before each test
- **Enhanced**: Monthly usage reset fixture: validates automatic quota reset functionality
- **New**: Administrative fixtures for tenant CRUD operations and billing management
- **New**: Billing fixtures for provider configuration and webhook validation
- **New**: Email fixtures for SMTP settings and notification testing
- **New**: Feature flag fixtures for tenant overrides and permission testing
- **New**: Quota enforcement fixtures for subscription plan validation
- **New**: Rate limiting fixtures for API throttling and abuse prevention
- **New**: Tenant suspension fixtures for audit logging and recovery workflows
- **New**: Webhook fixtures for payment processor event handling
- **Enhanced**: Queue system fixtures with AsyncMock-based worker mocking

```mermaid
flowchart TD
Start(["Test starts"]) --> Cleanup["Cleanup test artifacts<br/>and temporary files"]
Cleanup --> RLClear["Clear rate limiter buckets<br/>to prevent CI 429 errors"]
RLClear --> DB["Create in-memory DB tables<br/>including queue tables"]
DB --> Client["Initialize TestClient and override dependencies"]
Client --> Auth["Authenticate via register/login and inject headers"]
Auth --> Mocks["Patch external services with AsyncMock/MagicMock"]
Mocks --> Admin["Test administrative APIs"]
Admin --> Billing["Test billing providers"]
Billing --> Email["Test email notifications"]
Email --> Flags["Test feature flags"]
Flags --> Quota["Test quota enforcement"]
Quota --> Rate["Test rate limiting"]
Rate --> Suspension["Test tenant suspension"]
Suspension --> Webhooks["Test webhook processing"]
Webhooks --> Queue["Mock queue workers with AsyncMock"]
Queue --> LLM["Test LLM service layer"]
LLM --> Pipelines["Test hybrid/agent pipelines"]
Pipelines --> Services["Test analysis/transcript/video services"]
Services --> RouteCall["Invoke route under test"]
RouteCall --> Asserts["Assert response status and payload"]
Asserts --> Cleanup2["Drop queue tables then main tables<br/>and close sessions"]
Cleanup2 --> End(["Test ends"])
```

**Diagram sources**
- [conftest.py:58-170](file://app/backend/tests/conftest.py#L58-L170)
- [conftest.py:196-204](file://app/backend/tests/conftest.py#L196-L204)
- [rate_limit.py:100-121](file://app/backend/middleware/rate_limit.py#L100-L121)
- [subscription.py:85-97](file://app/backend/routes/subscription.py#L85-L97)

**Section sources**
- [conftest.py:58-170](file://app/backend/tests/conftest.py#L58-L170)
- [conftest.py:196-204](file://app/backend/tests/conftest.py#L196-L204)
- [rate_limit.py:16-144](file://app/backend/middleware/rate_limit.py#L16-L144)
- [subscription.py:85-97](file://app/backend/routes/subscription.py#L85-L97)
- [test_rate_limiting.py:1-85](file://app/backend/tests/test_rate_limiting.py#L1-L85)
- [test_subscription.py:312-355](file://app/backend/tests/test_subscription.py#L312-L355)

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

### API Testing Strategies - Enhanced Coverage
Backend API tests now validate comprehensive endpoint coverage:
- Root and health endpoints
- Authentication endpoints (register, login, refresh, profile)
- Analysis endpoints (single and batch resume analysis)
- History and comparison endpoints
- Video analysis endpoints (upload and URL-based)
- Subscription endpoints (plans, usage checks, history, admin controls)
- **Enhanced**: Rate limiter reset endpoints for administrative control
- **Enhanced**: Monthly usage reset validation for quota management
- **New**: Administrative API endpoints (tenant management, billing configuration)
- **New**: Billing system endpoints (checkout, webhook, subscription status)
- **New**: Email notification endpoints (SMTP configuration, test emails)
- **New**: Feature flag endpoints (global flags, tenant overrides)
- **New**: Operational monitoring endpoints (metrics, usage trends)
- **New**: Quota enforcement endpoints (usage validation, limit checking)
- **New**: Rate limiting endpoints (API throttling, abuse prevention)
- **New**: Tenant suspension endpoints (suspend/reactivate operations)
- **New**: Webhook processing endpoints (payment events, status updates)
- **Enhanced**: Queue system endpoints with comprehensive testing

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

### Integration Testing Approaches - Enhanced Stability
Backend integration tests now cover:
- Use TestClient to exercise routes with real app wiring
- Override database dependency to use in-memory SQLite
- Use auth fixtures to simulate logged-in users
- Mock external services to keep tests deterministic
- **Enhanced**: Automatic rate limiter bucket clearing to prevent CI instability
- **Enhanced**: Comprehensive monthly usage reset validation with edge cases
- **New**: Administrative API integration testing with tenant management
- **New**: Billing system integration testing with provider abstractions
- **New**: Email service integration testing with SMTP configuration
- **New**: Feature flag integration testing with tenant overrides
- **New**: Quota enforcement integration testing with subscription validation
- **New**: Rate limiting integration testing with API throttling
- **New**: Tenant suspension integration testing with audit logging
- **New**: Webhook integration testing with payment processor events
- **Enhanced**: Queue system integration testing with comprehensive database support

Frontend integration tests:
- Page-level tests (e.g., VideoPage) mock API module and router dependencies
- Validate UI interactions, state transitions, and error handling
- Ensure platform detection and supported platforms list rendering
- **Enhanced**: Comprehensive AI pipeline feature integration testing

**Updated** The batch analysis integration tests now focus on comprehensive validation mechanisms including file content validation, size limits, extension filtering, and error handling scenarios without relying on specific PDF header validation patterns.

**Section sources**
- [conftest.py:32-42](file://app/backend/tests/conftest.py#L32-L42)
- [VideoPage.test.jsx:1-377](file://app/frontend/src/__tests__/VideoPage.test.jsx#L1-L377)

### Test Configuration and Mock Services - Enhanced Infrastructure
Backend:
- PYTHONPATH set in CI to resolve imports
- pytest-cov enabled for comprehensive coverage reporting
- Shared fixtures centralize DB setup, auth, and service mocks
- **Enhanced**: Automatic rate limiter bucket clearing using autouse fixtures
- **Enhanced**: Comprehensive monthly usage reset validation infrastructure
- **New**: Specialized fixtures for administrative API testing and tenant management
- **New**: Enhanced fixtures for billing provider testing and webhook validation
- **New**: Comprehensive fixtures for email service testing and SMTP configuration
- **New**: Feature flag fixtures for tenant overrides and permission testing
- **New**: Quota enforcement fixtures for subscription plan validation
- **New**: Rate limiting fixtures for API throttling and abuse prevention
- **New**: Webhook fixtures for payment processor event handling
- **Enhanced**: Sophisticated queue system database infrastructure with AsyncMock-based worker mocking

Frontend:
- Vitest configuration via package.json scripts
- DOM matchers via jest-dom
- Mocked axios and browser APIs in api.test.js setup

**Section sources**
- [ci.yml:25-58](file://.github/workflows/ci.yml#L25-L58)
- [package.json:6-12](file://app/frontend/package.json#L6-L12)
- [api.test.js:1-265](file://app/frontend/src/__tests__/api.test.js#L1-L265)

### Test Data Management - Enhanced Coverage
Backend:
- Sample resume text and job description fixtures
- Minimal MP4 bytes for file-type validation
- Transcript fixtures (VTT, SRT, plain text)
- Subscription plan fixtures with seeded limits and features
- **Enhanced**: Automatic rate limiter reset validation with edge case scenarios
- **Enhanced**: Comprehensive monthly usage reset testing with historical data
- **New**: Administrative test data with tenant management scenarios
- **New**: Billing test data with provider configurations and webhook events
- **New**: Email service test data with SMTP settings and notification templates
- **New**: Feature flag test data with tenant overrides and permission scenarios
- **New**: Quota enforcement test data with subscription plan validation
- **New**: Rate limiting test data with API throttling scenarios
- **New**: Tenant suspension test data with audit logging scenarios
- **New**: Webhook test data with payment processor events
- **Enhanced**: Queue system test data with comprehensive job/result structures
- **Updated**: Test data fixtures now use DOCX header patterns for validation testing

Frontend:
- Mock result objects for video analysis (low and high risk)
- Component props populated with mock data
- **Enhanced**: Comprehensive AI pipeline result objects with explainability features

**Updated** Test data fixtures have been updated to use DOCX header patterns for validation testing, replacing the previous PDF-specific header validation scenarios that were removed from the test suite.

**Section sources**
- [conftest.py:294-421](file://app/backend/tests/conftest.py#L294-L421)
- [VideoPage.test.jsx:28-86](file://app/frontend/src/__tests__/VideoPage.test.jsx#L28-L86)

### Enhanced Rate Limiter Reset Mechanism - New Critical Infrastructure
**New Section**: The enhanced test infrastructure now includes sophisticated rate limiter reset mechanisms for improved CI stability:

#### Automatic Rate Limiter Bucket Clearing
The `_clear_rate_limit_buckets()` autouse fixture ensures CI stability by:
- Automatically clearing token buckets before every test execution
- Preventing 429 rate limit errors in CI environments
- Maintaining consistent test state across test runs
- Using RateLimitMiddleware singleton instance for cleanup

#### Rate Limiter Configuration Caching
The RateLimitMiddleware implements intelligent caching:
- Config cache TTL of 60 seconds to balance freshness and performance
- Thread-safe bucket management with lock-based synchronization
- Dynamic RPM (requests per minute) configuration per tenant
- Whitelist paths that bypass rate limiting (health, auth, docs)

#### Token Bucket Algorithm Implementation
The rate limiter uses a sophisticated token bucket algorithm:
- Time-based token refill calculation
- Configurable refill rates per tenant
- Proper token consumption and deficit calculation
- Retry-After header generation for rate limit exceeded responses

```mermaid
flowchart TD
Start(["Test Fixture Setup"]) --> Check["Check RateLimitMiddleware instance"]
Check --> Exists{"Instance exists?"}
Exists --> |Yes| Clear["Clear buckets and config cache"]
Exists --> |No| Skip["Skip cleanup"]
Clear --> Continue["Continue with test"]
Skip --> Continue
Continue --> TestRun["Execute test"]
TestRun --> End(["Test Complete"])
```

**Diagram sources**
- [conftest.py:196-204](file://app/backend/tests/conftest.py#L196-L204)
- [rate_limit.py:31-36](file://app/backend/middleware/rate_limit.py#L31-L36)
- [rate_limit.py:100-121](file://app/backend/middleware/rate_limit.py#L100-L121)

**Section sources**
- [conftest.py:196-204](file://app/backend/tests/conftest.py#L196-L204)
- [rate_limit.py:16-144](file://app/backend/middleware/rate_limit.py#L16-L144)
- [test_rate_limiting.py:1-85](file://app/backend/tests/test_rate_limiting.py#L1-L85)

### Enhanced Monthly Usage Reset System - New Critical Infrastructure
**New Section**: The enhanced test infrastructure now includes comprehensive monthly usage reset validation:

#### Automatic Monthly Reset Logic
The `_ensure_monthly_reset()` function provides robust quota management:
- Detects month-over-month usage counter resets
- Handles edge cases for year transitions
- Maintains UTC timezone consistency
- Preserves usage reset timestamps for audit trails

#### Comprehensive Test Coverage
The monthly reset system includes extensive validation:
- New month detection with proper timestamp comparison
- Same month preservation with unchanged counters
- Historical data validation across calendar boundaries
- Integration with analysis route usage tracking

```mermaid
flowchart TD
Start(["Usage Check"]) --> GetTenant["Get tenant from DB"]
GetTenant --> CheckReset["Check usage_reset_at timestamp"]
CheckReset --> MonthChanged{"Month changed?"}
MonthChanged --> |Yes| ResetCounters["Reset analyses_count_this_month = 0"]
MonthChanged --> |No| PreserveCounters["Preserve existing counters"]
ResetCounters --> UpdateTimestamp["Update usage_reset_at to current month"]
PreserveCounters --> Continue["Continue with usage check"]
UpdateTimestamp --> Continue
Continue --> End(["Complete"])
```

**Diagram sources**
- [subscription.py:85-97](file://app/backend/routes/subscription.py#L85-L97)
- [test_subscription.py:312-355](file://app/backend/tests/test_subscription.py#L312-L355)

**Section sources**
- [subscription.py:85-97](file://app/backend/routes/subscription.py#L85-L97)
- [test_subscription.py:312-355](file://app/backend/tests/test_subscription.py#L312-L355)

### Enhanced CI Stability and Test Artifact Management - New Infrastructure
**New Section**: The enhanced test infrastructure now includes systematic cleanup of temporary test artifacts:

#### Comprehensive Test Artifact Cleanup
The .gitignore patterns now exclude test artifacts:
- `.coverage` - Coverage reports
- `htmlcov/` - HTML coverage reports
- `.pytest_cache/` - Pytest cache directories
- `pytest_summary.txt` - Test summary files
- `test_full_output.txt` - Full test output logs
- `*_output*.txt` - Various output files
- `*_results*.txt` - Test results files
- `*_summary*.txt` - Test summary files

#### Enhanced Test Runner Scripts
The test runner scripts now include systematic cleanup:
- Temporary test output logging with rotation
- Error handling with detailed output capture
- Cross-platform compatibility with PowerShell and Bash
- Comprehensive validation of test environment prerequisites

#### CI/CD Stability Improvements
GitHub Actions workflows now benefit from:
- Cleaner test execution environments
- Reduced test flakiness through artifact isolation
- Better resource management in CI containers
- Improved test reliability across different runners

```mermaid
flowchart TD
Start(["Test Execution"]) --> Setup["Setup test environment"]
Setup --> RunTests["Execute tests with cleanup"]
RunTests --> CleanupArtifacts["Cleanup test artifacts<br/>and temporary files"]
CleanupArtifacts --> Validate["Validate cleanup success"]
Validate --> Success{"Cleanup successful?"}
Success --> |Yes| Complete["Complete test run"]
Success --> |No| Error["Handle cleanup error"]
Error --> Complete
Complete --> End(["Test complete"])
```

**Diagram sources**
- [.gitignore:42-47](file://.gitignore#L42-L47)
- [run-full-tests.sh:31-42](file://scripts/run-full-tests.sh#L31-L42)
- [test-locally.ps1:54-59](file://test-locally.ps1#L54-L59)

**Section sources**
- [.gitignore:42-47](file://.gitignore#L42-L47)
- [run-full-tests.sh:1-256](file://scripts/run-full-tests.sh#L1-L256)
- [test-locally.ps1:1-119](file://test-locally.ps1#L1-L119)

### Administrative API Testing - New Comprehensive Coverage
**New Section**: The expanded test suite now includes comprehensive administrative API testing:

#### Administrative API Test Coverage
The administrative API tests validate:
- **Permission enforcement**: Regular users receive 403 on all admin endpoints
- **Tenant management**: Listing, searching, and filtering tenants with pagination
- **Tenant detail retrieval**: Full tenant information with users and usage logs
- **Tenant lifecycle management**: Suspend and reactivate operations with audit logging
- **Plan management**: Changing tenant subscription plans with audit trails
- **Usage adjustment**: Modifying analyses count and storage usage
- **Usage history**: Retrieving tenant usage logs with filtering
- **Audit logging**: Comprehensive audit trail validation
- **Metrics reporting**: Platform-wide analytics and usage trends

#### Administrative API Testing Patterns
Key testing patterns include:
- **Permission testing**: Verifying 403 responses for unauthorized access attempts
- **Data validation**: Ensuring proper response structures and field presence
- **Audit logging**: Verifying audit trail creation for administrative actions
- **Business logic validation**: Testing tenant lifecycle and plan management workflows
- **Integration testing**: Validating administrative endpoints with real database operations

```mermaid
flowchart TD
AdminTests["Administrative API Tests"] --> Permissions["Permission Enforcement Tests"]
AdminTests --> Tenants["Tenant Management Tests"]
AdminTests --> Plans["Plan Management Tests"]
AdminTests --> Usage["Usage Adjustment Tests"]
AdminTests --> Metrics["Metrics & Analytics Tests"]
Permissions --> Unauthorized["403 for Non-Admin Users"]
Tenants --> CRUD["Tenant CRUD Operations"]
Tenants --> Search["Search & Filter Functionality"]
Plans --> Lifecycle["Plan Change Lifecycle"]
Usage --> Adjustment["Usage Adjustment Validation"]
Metrics --> Reporting["Metrics & Trends Reporting"]
```

**Diagram sources**
- [test_admin_api.py:43-75](file://app/backend/tests/test_admin_api.py#L43-75)
- [test_admin_api.py:79-128](file://app/backend/tests/test_admin_api.py#L79-128)
- [test_admin_api.py:156-226](file://app/backend/tests/test_admin_api.py#L156-226)
- [test_admin_api.py:230-274](file://app/backend/tests/test_admin_api.py#L230-274)
- [test_admin_api.py:278-351](file://app/backend/tests/test_admin_api.py#L278-351)
- [test_admin_metrics.py:27-114](file://app/backend/tests/test_admin_metrics.py#L27-114)
- [test_admin_metrics.py:116-159](file://app/backend/tests/test_admin_metrics.py#L116-159)

**Section sources**
- [test_admin_api.py:1-467](file://app/backend/tests/test_admin_api.py#L1-467)
- [test_admin_metrics.py:1-159](file://app/backend/tests/test_admin_metrics.py#L1-159)

### Billing System Testing - New Comprehensive Provider Coverage
**New Section**: The expanded test suite includes comprehensive billing system testing:

#### Billing Provider Testing
The billing system tests validate:
- **Manual provider**: Reference ID creation, subscription cancellation, and webhook handling
- **Factory pattern**: Provider selection based on configuration with fallback mechanisms
- **Stripe provider**: Provider name validation and error handling for missing dependencies
- **Razorpay provider**: Provider name validation and error handling for missing dependencies
- **Configuration management**: Admin endpoints for billing configuration and provider setup
- **Route integration**: Checkout sessions, webhook processing, and subscription status checking

#### Billing Integration Testing
Key integration patterns include:
- **Provider abstraction**: Testing provider interfaces and factory selection logic
- **Configuration persistence**: Validating billing configuration storage and retrieval
- **Webhook processing**: Testing payment processor event handling and status updates
- **Subscription management**: Validating subscription lifecycle and status reporting
- **Error handling**: Testing graceful degradation for unavailable payment providers

```mermaid
flowchart TD
BillingTests["Billing System Tests"] --> Providers["Provider Testing"]
BillingTests --> Factory["Factory Pattern Testing"]
BillingTests --> Routes["Route Integration Testing"]
Providers --> Manual["Manual Provider Tests"]
Providers --> Stripe["Stripe Provider Tests"]
Providers --> Razorpay["Razorpay Provider Tests"]
Factory --> Selection["Provider Selection Logic"]
Factory --> Fallback["Fallback Mechanisms"]
Routes --> Checkout["Checkout Session Testing"]
Routes --> Webhooks["Webhook Processing"]
Routes --> Status["Subscription Status"]
```

**Diagram sources**
- [test_billing.py:9-75](file://app/backend/tests/test_billing.py#L9-75)
- [test_billing.py:77-126](file://app/backend/tests/test_billing.py#L77-126)
- [test_billing.py:128-222](file://app/backend/tests/test_billing.py#L128-222)
- [test_billing.py:223-288](file://app/backend/tests/test_billing.py#L223-288)
- [test_billing.py:290-328](file://app/backend/tests/test_billing.py#L290-328)

**Section sources**
- [test_billing.py:1-328](file://app/backend/tests/test_billing.py#L1-328)

### Email Service Testing - New Notification Coverage
**New Section**: The expanded test suite includes comprehensive email service testing:

#### Email Service Test Coverage
The email service tests validate:
- **Configuration validation**: SMTP settings verification and configuration status
- **Email delivery**: SMTP connection, authentication, and message sending
- **Template formatting**: Quota warnings, subscription expiry notices, and suspension notifications
- **Error handling**: Graceful handling of SMTP failures and missing credentials
- **Admin endpoints**: Configuration retrieval and test email sending for notification validation

#### Email Integration Testing
Key testing patterns include:
- **SMTP mocking**: Isolating email delivery with SMTP server mocking
- **Template validation**: Ensuring proper HTML formatting and content injection
- **Security validation**: Preventing credential exposure in configuration responses
- **Integration testing**: Validating admin notification endpoints with real service integration
- **Error scenario testing**: Testing email delivery failures and partial credential setups

```mermaid
flowchart TD
EmailTests["Email Service Tests"] --> Unit["Unit Testing"]
EmailTests --> Integration["Integration Testing"]
Unit --> Config["Configuration Validation"]
Unit --> Delivery["Email Delivery"]
Unit --> Templates["Template Formatting"]
Delivery --> SMTP["SMTP Connection Testing"]
Delivery --> Security["Credential Security"]
Templates --> Quota["Quota Warning Templates"]
Templates --> Expiry["Subscription Expiry Templates"]
Templates --> Suspension["Suspension Notice Templates"]
Integration --> AdminEndpoints["Admin Notification Endpoints"]
Integration --> ServiceIntegration["Service Integration Testing"]
```

**Diagram sources**
- [test_email_service.py:15-144](file://app/backend/tests/test_email_service.py#L15-144)
- [test_email_service.py:149-232](file://app/backend/tests/test_email_service.py#L149-232)

**Section sources**
- [test_email_service.py:1-232](file://app/backend/tests/test_email_service.py#L1-232)

### Feature Flag Testing - New Control Coverage
**New Section**: The expanded test suite includes comprehensive feature flag testing:

#### Feature Flag Test Coverage
The feature flag tests validate:
- **Global flag management**: Enabling/disabling features globally with caching
- **Tenant overrides**: Individual tenant feature control and inheritance
- **Permission enforcement**: Middleware integration for feature access control
- **Cache invalidation**: Proper cache clearing and data synchronization
- **Admin endpoints**: Feature flag management and tenant override operations

#### Feature Flag Integration Testing
Key testing patterns include:
- **Cache management**: Testing cache invalidation and data consistency
- **Tenant override validation**: Ensuring proper override precedence over global settings
- **Middleware integration**: Validating require_feature middleware behavior
- **Admin endpoint testing**: Testing feature flag CRUD operations with proper authorization
- **Permission validation**: Ensuring unauthorized access is properly denied

```mermaid
flowchart TD
FeatureFlagTests["Feature Flag Tests"] --> Core["Core Functionality"]
FeatureFlagTests --> Admin["Admin Endpoints"]
FeatureFlagTests --> Middleware["Middleware Integration"]
Core --> GlobalFlags["Global Flag Management"]
Core --> TenantOverrides["Tenant Override Management"]
Core --> Cache["Cache Management"]
Admin --> CRUD["Feature Flag CRUD Operations"]
Admin --> Overrides["Tenant Override Operations"]
Middleware --> Permission["Permission Enforcement"]
Middleware --> RequireFeature["require_feature Middleware"]
```

**Diagram sources**
- [test_feature_flags.py:42-111](file://app/backend/tests/test_feature_flags.py#L42-111)
- [test_feature_flags.py:113-182](file://app/backend/tests/test_feature_flags.py#L113-182)
- [test_feature_flags.py:184-233](file://app/backend/tests/test_feature_flags.py#L184-233)

**Section sources**
- [test_feature_flags.py:1-233](file://app/backend/tests/test_feature_flags.py#L1-233)

### Quota Enforcement Testing - New Subscription Coverage
**New Section**: The expanded test suite includes comprehensive quota enforcement testing:

#### Quota Enforcement Test Coverage
The quota enforcement tests validate:
- **Subscription plan limits**: Free, Pro, and Enterprise plan quota validation
- **Usage tracking**: Monthly usage counting and limit enforcement
- **Quota reset logic**: Calendar month-based quota reset functionality
- **HTTP endpoint integration**: Analysis endpoint quota checking and 403 responses
- **Edge case handling**: Non-existent tenants, unlimited plans, and partial usage scenarios

#### Quota Enforcement Integration Testing
Key testing patterns include:
- **Plan limit validation**: Testing quota limits for different subscription tiers
- **Usage calculation**: Validating monthly usage counting and limit enforcement
- **Reset logic testing**: Ensuring quotas reset appropriately at calendar month boundaries
- **Endpoint integration**: Testing quota checking in analysis endpoints
- **Error scenario validation**: Testing quota exceeded responses and error details

```mermaid
flowchart TD
QuotaTests["Quota Enforcement Tests"] --> Unit["Unit Testing"]
QuotaTests --> Integration["Integration Testing"]
Unit --> PlanLimits["Plan Limit Validation"]
Unit --> UsageTracking["Usage Tracking Logic"]
Unit --> ResetLogic["Quota Reset Logic"]
Integration --> HTTPIntegration["HTTP Endpoint Integration"]
Integration --> ErrorScenarios["Error Scenario Testing"]
PlanLimits --> FreeTier["Free Tier Limits"]
PlanLimits --> ProTier["Pro Tier Limits"]
PlanLimits --> EnterpriseTier["Enterprise Unlimited"]
UsageTracking --> MonthlyCounting["Monthly Usage Counting"]
UsageTracking --> LimitEnforcement["Limit Enforcement"]
ResetLogic --> CalendarMonth["Calendar Month Reset"]
ResetLogic --> EdgeCases["Edge Case Handling"]
HTTPIntegration --> AnalysisEndpoint["Analysis Endpoint Testing"]
HTTPIntegration --> ErrorResponses["403 Error Responses"]
ErrorScenarios --> NonExistentTenant["Non-existent Tenant Testing"]
ErrorScenarios --> UnlimitedPlans["Unlimited Plan Testing"]
```

**Diagram sources**
- [test_quota_enforcement.py:55-176](file://app/backend/tests/test_quota_enforcement.py#L55-176)
- [test_quota_enforcement.py:180-240](file://app/backend/tests/test_quota_enforcement.py#L180-240)

**Section sources**
- [test_quota_enforcement.py:1-240](file://app/backend/tests/test_quota_enforcement.py#L1-240)

### Rate Limiting Testing - New Protection Coverage
**New Section**: The expanded test suite includes comprehensive rate limiting testing:

#### Rate Limiting Test Coverage
The rate limiting tests validate:
- **API throttling**: Request rate limiting and throttling mechanisms
- **Abuse prevention**: Protection against excessive API usage and abuse
- **Configuration management**: Rate limiting configuration and enforcement
- **Integration testing**: Rate limiting integration with authentication and authorization
- **Error handling**: Proper rate limit exceeded responses and retry mechanisms

#### Rate Limiting Integration Testing
Key testing patterns include:
- **Throttling validation**: Testing request rate limiting and enforcement mechanisms
- **Configuration testing**: Validating rate limiting configuration and persistence
- **Integration validation**: Testing rate limiting with authentication and authorization flows
- **Error scenario testing**: Validating rate limit exceeded responses and error handling
- **Performance testing**: Testing rate limiting under load and high-traffic scenarios

**Section sources**
- [test_rate_limiting.py](file://app/backend/tests/test_rate_limiting.py)

### Tenant Suspension Testing - New Operational Coverage
**New Section**: The expanded test suite includes comprehensive tenant suspension testing:

#### Tenant Suspension Test Coverage
The tenant suspension tests validate:
- **Suspension lifecycle**: Complete suspend → reactivate workflow with audit logging
- **Status validation**: Suspension status updates and validation
- **Audit logging**: Comprehensive audit trail creation for suspension operations
- **Business logic validation**: Proper suspension and reactivation business rules
- **Integration testing**: Suspension integration with subscription management and usage tracking

#### Tenant Suspension Integration Testing
Key testing patterns include:
- **Lifecycle validation**: Testing complete suspension and reactivation workflows
- **Status validation**: Ensuring proper status updates and validations
- **Audit logging**: Validating comprehensive audit trail creation and retrieval
- **Business rule testing**: Testing suspension business logic and constraints
- **Integration validation**: Testing suspension with subscription and usage management

**Section sources**
- [test_tenant_suspension.py](file://app/backend/tests/test_tenant_suspension.py)

### Webhook Testing - New Payment Coverage
**New Section**: The expanded test suite includes comprehensive webhook testing:

#### Webhook Test Coverage
The webhook tests validate:
- **Payment processor integration**: Webhook handling for Stripe, Razorpay, and manual providers
- **Event processing**: Payment event processing and status updates
- **Security validation**: Webhook signature validation and security measures
- **Error handling**: Graceful handling of malformed webhook events
- **Integration testing**: Webhook integration with billing system and subscription management

#### Webhook Integration Testing
Key testing patterns include:
- **Event processing validation**: Testing webhook event processing and status updates
- **Security testing**: Validating webhook signature validation and security measures
- **Provider integration**: Testing webhook integration with different payment processors
- **Error scenario testing**: Validating webhook handling of malformed and malicious events
- **Integration validation**: Testing webhook integration with billing and subscription systems

**Section sources**
- [test_webhooks.py](file://app/backend/tests/test_webhooks.py)

### Queue System Testing Infrastructure - Enhanced Database Setup
**New Section**: The enhanced test infrastructure now includes sophisticated queue system database management:

#### Sophisticated Table Creation Mechanisms
The `_create_all_tables()` function implements a two-phase table creation process:
1. **Main Tables Creation**: Creates standard application tables using SQLAlchemy metadata
2. **Queue Tables Creation**: Uses raw SQL to create queue system tables without FK constraints
   - `analysis_jobs`: Main queue table for tracking analysis tasks
   - `analysis_results`: Immutable storage for completed analyses  
   - `analysis_artifacts`: Store intermediate processing artifacts
   - `job_metrics`: Performance and quality metrics for monitoring

#### Advanced Table Destruction
The `_drop_all_tables()` function implements careful cleanup:
1. **Queue Tables First**: Drops queue tables in reverse order to avoid FK violations
2. **Main Tables Second**: Drops standard application tables
3. **Proper Cleanup Order**: Ensures referential integrity during test teardown

#### Enhanced Queue Worker Mocking
Queue workers are mocked using AsyncMock to prevent database access:
- `start_queue_worker` mocked with AsyncMock
- `stop_queue_worker` mocked with AsyncMock
- Prevents actual queue processing during tests

#### Queue System Database Schema Support
The test infrastructure supports the complete queue system schema:
- UUID primary keys for all tables
- JSONB columns for flexible data storage
- Proper indexing for queue operations
- Foreign key relationships with appropriate constraints
- Triggers and views for enhanced functionality

```mermaid
flowchart TD
CreateTables["_create_all_tables()"] --> Main["Create main application tables<br/>using SQLAlchemy metadata"]
CreateTables --> Queue["Create queue tables using raw SQL<br/>without FK constraints"]
Queue --> Jobs["analysis_jobs table<br/>with UUID primary keys"]
Queue --> Results["analysis_results table<br/>immutable completed data"]
Queue --> Artifacts["analysis_artifacts table<br/>intermediate data storage"]
Queue --> Metrics["job_metrics table<br/>performance tracking"]
Cleanup["_drop_all_tables()"] --> QueueDrop["Drop queue tables first<br/>reverse order of creation"]
Cleanup --> MainDrop["Drop main tables second<br/>standard metadata drop"]
```

**Diagram sources**
- [conftest.py:58-170](file://app/backend/tests/conftest.py#L58-L170)
- [queue_manager.py:46-183](file://app/backend/services/queue_manager.py#L46-L183)
- [008_analysis_queue_system.py:29-236](file://alembic/versions/008_analysis_queue_system.py#L29-L236)

**Section sources**
- [conftest.py:58-170](file://app/backend/tests/conftest.py#L58-L170)
- [queue_manager.py:46-183](file://app/backend/services/queue_manager.py#L46-L183)
- [008_analysis_queue_system.py:29-236](file://alembic/versions/008_analysis_queue_system.py#L29-L236)

### Continuous Integration Testing with GitHub Actions
Workflows:
- ci.yml: runs backend tests with comprehensive coverage and uploads to Codecov; runs frontend tests and builds
- cd.yml: runs backend and frontend tests as part of build-and-push images job

Execution:
- Python 3.11 and Node.js 20 environments
- Backend coverage collected for services package with 150+ test suite
- Frontend tests executed via npm test
- **Enhanced**: Improved CI stability through systematic rate limiter reset and artifact cleanup

**Section sources**
- [ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

### Writing Effective Tests for New Features - Enhanced Guidelines
Guidelines derived from enhanced test suite:
- Backend
  - Use pytest fixtures to minimize duplication (db, client, auth_client)
  - Prefer AsyncMock/MagicMock for external services to avoid flaky network calls
  - Validate both success and failure paths (e.g., invalid file types, missing fields)
  - For subscription features, use seed fixtures and tenant plan assignments
  - **Enhanced**: Leverage automatic rate limiter bucket clearing for CI stability
  - **Enhanced**: Test monthly usage reset logic with edge case scenarios
  - **New**: Test administrative API permissions and tenant management workflows
  - **New**: Validate billing provider abstraction and webhook processing
  - **New**: Test email service configuration and notification delivery
  - **New**: Validate feature flag management and tenant override scenarios
  - **New**: Test quota enforcement with subscription plan validation
  - **New**: Validate rate limiting and API throttling mechanisms
  - **New**: Test tenant suspension and audit logging workflows
  - **New**: Validate webhook processing with payment processor events
  - **Enhanced**: Leverage sophisticated queue system database infrastructure
  - **Enhanced**: Focus on comprehensive validation mechanisms rather than specific PDF header patterns
  - **Enhanced**: Implement systematic cleanup of test artifacts for CI reliability
- Frontend
  - Mock axios and browser APIs to focus on component behavior
  - Test user interactions (clicks, input changes) and resulting UI updates
  - Validate request shapes, headers, and timeouts for API calls
  - Ensure error messages are surfaced and handled gracefully
  - **Enhanced**: Test AI pipeline explainability and risk analysis features

**Updated** Test writing guidelines now emphasize comprehensive validation mechanisms, CI stability through rate limiter reset, and systematic artifact cleanup without reliance on specific PDF header validation patterns.

**Section sources**
- [conftest.py:125-176](file://app/backend/tests/conftest.py#L125-L176)
- [test_api.py:71-87](file://app/backend/tests/test_api.py#L71-L87)
- [api.test.js:167-200](file://app/frontend/src/__tests__/api.test.js#L167-L200)

## Dependency Analysis
Backend test dependencies with enhanced coverage:
- pytest, FastAPI TestClient, SQLAlchemy in-memory DB, passlib sha256_crypt for bcrypt compatibility
- External service mocks via unittest.mock
- **Enhanced**: Automatic rate limiter bucket clearing for CI stability
- **Enhanced**: Comprehensive monthly usage reset testing infrastructure
- **New**: Enhanced administrative API testing dependencies and fixtures
- **New**: Comprehensive billing system testing dependencies and provider fixtures
- **New**: Email service testing dependencies and SMTP configuration fixtures
- **New**: Feature flag testing dependencies and tenant override fixtures
- **New**: Quota enforcement testing dependencies and subscription plan fixtures
- **New**: Rate limiting testing dependencies and API throttling fixtures
- **New**: Tenant suspension testing dependencies and audit logging fixtures
- **New**: Webhook testing dependencies and payment processor fixtures
- **Enhanced**: Queue system testing dependencies with AsyncMock support

Frontend test dependencies:
- Vitest, React Testing Library, jest-dom
- Mocked axios and DOM APIs

```mermaid
graph LR
Py["pytest"] --> FA["FastAPI TestClient"]
Py --> SA["SQLAlchemy in-memory DB"]
Py --> UM["unittest.mock"]
Py --> AM["AsyncMock"]
Py --> RL["Rate Limiter Reset"]
VT["Vitest"] --> RTL["React Testing Library"]
VT --> AX["Mocked axios"]
VT --> DOM["Mocked DOM APIs"]
RL --> AC["Automatic Cleanup"]
```

**Diagram sources**
- [conftest.py:1-12](file://app/backend/tests/conftest.py#L1-L12)
- [package.json:23-38](file://app/frontend/package.json#L23-L38)
- [conftest.py:196-204](file://app/backend/tests/conftest.py#L196-L204)

**Section sources**
- [conftest.py:1-12](file://app/backend/tests/conftest.py#L1-L12)
- [package.json:23-38](file://app/frontend/package.json#L23-L38)

## Performance Considerations
- Backend
  - Use in-memory SQLite to avoid disk I/O overhead
  - Keep external service mocks synchronous where possible to reduce test runtime
  - Limit heavy computations in tests; rely on mocks for LLM and transcription services
  - **Enhanced**: Optimize rate limiter reset performance with efficient bucket clearing
  - **Enhanced**: Minimize monthly usage reset overhead with timestamp-based comparisons
  - **New**: Optimize administrative API testing with efficient tenant management fixtures
  - **New**: Minimize billing system testing overhead with provider abstraction mocking
  - **New**: Reduce email service testing overhead with SMTP mocking
  - **New**: Minimize feature flag testing overhead with cache management fixtures
  - **New**: Optimize quota enforcement testing with subscription plan fixtures
  - **New**: Minimize rate limiting testing overhead with API throttling mocks
  - **New**: Reduce tenant suspension testing overhead with audit logging fixtures
  - **New**: Optimize webhook testing with payment processor event mocking
  - **Enhanced**: Queue system testing optimized with AsyncMock-based worker mocking
  - **Enhanced**: Efficient queue table creation/destruction mechanisms
  - **Enhanced**: Automatic cleanup reduces test execution time through artifact management
  - **Updated**: Focus on comprehensive validation mechanisms for better test performance
- Frontend
  - Avoid real network calls by mocking axios
  - Use minimal DOM queries and focus on user-centric assertions
  - Prefer component-level tests over full-page integration tests when feasible
  - **Enhanced**: Optimize AI pipeline feature testing with selective mocking

## Troubleshooting Guide
Common issues and resolutions with enhanced test coverage:
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
  - **Enhanced**: Verify rate limiter bucket cleanup in CI environments
  - **Enhanced**: Check test artifact cleanup completion in CI logs
- **New**: Rate limiter 429 errors in CI
  - Verify automatic rate limiter bucket clearing fixture is active
  - Check RateLimitMiddleware singleton instance availability
  - Ensure proper cleanup timing in test fixtures
- **New**: Monthly usage reset failures
  - Verify timestamp comparison logic in _ensure_monthly_reset
  - Check UTC timezone handling in reset calculations
  - Validate edge case handling for year transitions
- **New**: Test artifact pollution in CI
  - Verify .gitignore patterns include test artifact exclusions
  - Check cleanup script execution in test runners
  - Monitor temporary file handling in test processes
- **New**: Administrative API test failures
  - Verify permission enforcement and tenant management workflows
  - Check audit logging for administrative actions
  - Ensure proper authorization headers for admin endpoints
- **New**: Billing system test failures
  - Verify provider configuration and factory pattern logic
  - Check webhook processing and subscription status validation
  - Ensure proper error handling for unavailable payment providers
- **New**: Email service test failures
  - Verify SMTP configuration and credential security
  - Check template formatting and email delivery mocking
  - Ensure proper error handling for SMTP failures
- **New**: Feature flag test failures
  - Verify cache invalidation and data synchronization
  - Check tenant override precedence and middleware integration
  - Ensure proper permission enforcement for feature access
- **New**: Quota enforcement test failures
  - Verify subscription plan limits and usage tracking
  - Check quota reset logic and monthly boundary handling
  - Ensure proper HTTP endpoint integration and error responses
- **New**: Rate limiting test failures
  - Verify request throttling and API protection mechanisms
  - Check configuration persistence and integration testing
  - Ensure proper error handling for rate limit exceeded scenarios
- **New**: Tenant suspension test failures
  - Verify suspension lifecycle and status validation
  - Check audit logging and business rule enforcement
  - Ensure proper integration with subscription management
- **New**: Webhook test failures
  - Verify payment processor integration and event processing
  - Check security validation and error handling
  - Ensure proper integration with billing and subscription systems
- **Enhanced**: LLM service test failures
  - Verify JSON parsing fixtures and error handling scenarios
  - Check mock responses match expected LLM service interface
  - Ensure model configuration matches current `gemma4:31b-cloud` settings
- **Enhanced**: Pipeline testing issues
  - Ensure pipeline fixtures properly mock external dependencies
  - Validate error scenarios and retry mechanisms
- **Enhanced**: Background task testing problems
  - Verify task queue mocking and background process simulation
  - Check retry mechanism validation and error propagation
- **Enhanced**: Queue system test failures
  - Verify queue table creation order and FK constraint handling
  - Ensure AsyncMock-based worker mocking prevents database access
  - Check queue system database schema compliance
- **Enhanced**: Test artifact cleanup failures
  - Verify cleanup script execution in CI environments
  - Check file permission handling for artifact deletion
  - Ensure proper cleanup timing in test teardown
- **Updated**: Batch analysis test failures
  - Verify file content validation mechanisms are working correctly
  - Check magic-byte signature validation for different file types
  - Ensure size and extension filtering are properly enforced

**Updated** Troubleshooting guidance now includes specific guidance for the enhanced rate limiter reset mechanisms, monthly usage reset functionality, and systematic test artifact cleanup processes.

**Section sources**
- [test-locally.ps1:36-96](file://test-locally.ps1#L36-L96)
- [run-full-tests.sh:163-168](file://scripts/run-full-tests.sh#L163-L168)
- [run-full-tests.bat:100-107](file://scripts/run-full-tests.bat#L100-L107)

## Conclusion
The testing strategy leverages pytest and FastAPI TestClient for comprehensive backend unit and integration tests, with substantially expanded coverage including 150+ new tests for administrative APIs, billing systems, email services, feature flags, quota enforcement, rate limiting, tenant suspension, and webhooks. Frontend tests use Vitest and React Testing Library with mocked axios and DOM APIs. CI/CD pipelines automate test execution and coverage reporting with enhanced stability through systematic rate limiter reset mechanisms and test artifact cleanup. The expanded test suite ensures robust validation of advanced administrative and billing functionality, including comprehensive tenant management, provider abstraction, notification delivery, feature control, usage enforcement, and operational monitoring, providing reliable coverage for all major components.

**Updated** Recent updates ensure test infrastructure consistency with the new `gemma4:31b-cloud` model configuration, validating proper model selection across all service integrations and maintaining test reliability. The enhanced queue system testing infrastructure provides comprehensive coverage for the scalable job queue architecture with sophisticated database management and worker mocking capabilities. The substantially expanded administrative and billing test suites provide complete coverage of the new operational functionality with comprehensive permission testing, provider abstraction validation, and integration testing patterns. The enhanced rate limiter reset mechanisms and systematic artifact cleanup ensure improved CI stability and test reliability across all environments.

## Appendices

### Appendix A: Local Test Execution Scripts
- run-full-tests.sh: Validates Python syntax, imports, migrations, database models, route registration, and frontend files; useful for pre-commit checks
- test-locally.ps1: Runs backend and frontend tests locally with colored output and summarized results
- **Enhanced**: Improved error handling and cross-platform compatibility

**Section sources**
- [run-full-tests.sh:1-256](file://scripts/run-full-tests.sh#L1-L256)
- [test-locally.ps1:1-119](file://test-locally.ps1#L1-L119)

### Appendix B: Enhanced Test Coverage Areas
The substantially expanded test suite now includes comprehensive coverage for:

- **Administrative API Testing**: Complete coverage of tenant management, billing configuration, and operational controls with permission enforcement and audit logging
- **Billing System Testing**: Comprehensive testing of provider abstraction, factory pattern, checkout sessions, webhook processing, and subscription management across Stripe, Razorpay, and manual providers
- **Email Service Testing**: Complete coverage of SMTP configuration, notification delivery, template formatting, and admin notification endpoints with security validation
- **Feature Flag Testing**: Comprehensive testing of global flag management, tenant overrides, middleware integration, cache management, and admin endpoint operations
- **Quota Enforcement Testing**: Complete coverage of subscription plan limits, usage tracking, quota reset logic, and HTTP endpoint integration with proper error handling
- **Rate Limiting Testing**: Comprehensive testing of API throttling, abuse prevention, configuration management, and integration with authentication flows
- **Tenant Suspension Testing**: Complete coverage of suspension lifecycle, status validation, audit logging, and integration with subscription management
- **Webhook Testing**: Comprehensive testing of payment processor integration, event processing, security validation, and integration with billing systems
- **LLM Service Testing**: Dedicated tests for LLM service layer with JSON parsing validation and error handling scenarios
- **Pipeline Testing**: Comprehensive testing for hybrid and agent pipelines with retry mechanisms and background task processing
- **Analysis Service Testing**: Validation of analysis service functionality with error scenarios and edge cases
- **Transcript Service Testing**: Complete coverage of transcript processing with multiple formats and error handling
- **Video Processing Testing**: End-to-end testing of video analysis workflows with downloader and service validation
- **Subscription and Usage Testing**: Comprehensive validation of subscription system, usage enforcement, and rate limiting
- **Background Task Testing**: Validation of asynchronous task processing and queue management
- **Error Handling Testing**: Extensive testing of error scenarios, retry mechanisms, and graceful degradation
- **Integration Testing**: End-to-end testing of complex workflows and cross-service interactions
- **Queue System Testing**: Comprehensive testing of the scalable job queue architecture with database schema validation
- **Batch Analysis Testing**: Comprehensive validation of batch processing with file content validation, size limits, and error handling
- **Rate Limiter Reset Testing**: Enhanced testing of automatic rate limiter bucket clearing and CI stability mechanisms
- **Monthly Usage Reset Testing**: Comprehensive testing of automatic quota reset functionality with edge case validation
- **Test Artifact Cleanup Testing**: Systematic validation of temporary file cleanup and CI stability improvements

**Updated** Recent updates ensure model configuration consistency across all test coverage areas, with particular emphasis on validating the `gemma4:31b-cloud` model settings in LLM service tests and pipeline integrations. The enhanced queue system testing infrastructure provides complete coverage of the job queue architecture with sophisticated database management and worker mocking. The substantially expanded administrative and billing test suites provide comprehensive coverage of the new operational functionality with permission testing, provider abstraction validation, and integration testing patterns. The enhanced rate limiter reset mechanisms and systematic artifact cleanup ensure improved CI stability and test reliability.

**Section sources**
- [test_admin_api.py:1-467](file://app/backend/tests/test_admin_api.py#L1-467)
- [test_admin_metrics.py:1-159](file://app/backend/tests/test_admin_metrics.py#L1-159)
- [test_billing.py:1-328](file://app/backend/tests/test_billing.py#L1-328)
- [test_email_service.py:1-232](file://app/backend/tests/test_email_service.py#L1-232)
- [test_feature_flags.py:1-233](file://app/backend/tests/test_feature_flags.py#L1-233)
- [test_quota_enforcement.py:1-240](file://app/backend/tests/test_quota_enforcement.py#L1-240)
- [test_rate_limiting.py](file://app/backend/tests/test_rate_limiting.py)
- [test_tenant_suspension.py](file://app/backend/tests/test_tenant_suspension.py)
- [test_webhooks.py](file://app/backend/tests/test_webhooks.py)
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

### Appendix C: Model Configuration Updates
Recent changes to model configuration ensure consistency across the entire application stack:

- **LLM Service**: Updated default model from `qwen3.5:4b` to `gemma4:31b-cloud` for improved performance and capabilities
- **Health Sentinel**: Model configuration updated to reflect new `gemma4:31b-cloud` setting in health monitoring
- **Agent Pipeline**: Fast and reasoning models configured to use `gemma4:31b-cloud` for consistent performance
- **Training Routes**: Model references updated to `gemma4:31b-cloud` for training workflows
- **Wait Script**: Model detection and warmup procedures updated for new model configuration

These changes ensure that all service integrations consistently use the `gemma4:31b-cloud` model, providing reliable performance and compatibility across the Resume AI platform.

**Section sources**
- [llm_service.py:163-167](file://app/backend/services/llm_service.py#L163-L167)
- [llm_service.py:56-59](file://app/backend/services/llm_service.py#L56-L59)
- [agent_pipeline.py:50-52](file://app/backend/services/agent_pipeline.py#L50-L52)
- [training.py:113-114](file://app/backend/routes/training.py#L113-L114)
- [wait_for_ollama.py:51-52](file://app/backend/scripts/wait_for_ollama.py#L51-L52)
- [main.py:157](file://app/backend/main.py#L157)

### Appendix D: Enhanced Rate Limiter Infrastructure
**New Section**: The enhanced test infrastructure now includes sophisticated rate limiter reset mechanisms:

#### Automatic Rate Limiter Bucket Management
The enhanced rate limiter system provides:
- **Autouse fixture integration**: Automatic bucket clearing before every test execution
- **Thread-safe operation**: Lock-based synchronization for concurrent test access
- **Config cache optimization**: 60-second TTL for rate limit configuration caching
- **Whitelist path handling**: Automatic bypass for health, auth, and documentation endpoints
- **Retry-After header generation**: Proper rate limit exceeded response formatting

#### CI Stability Enhancements
The rate limiter reset mechanism ensures:
- **Consistent test execution**: Prevention of 429 rate limit errors in CI environments
- **Clean test state**: Fresh token buckets for each test run
- **Reliable test results**: Elimination of rate limit interference in test outcomes
- **Cross-platform compatibility**: Consistent behavior across different operating systems

#### Test Coverage Validation
The rate limiter testing includes:
- **Whitelisted path validation**: Ensuring non-rate-limited access for essential endpoints
- **Normal request handling**: Verification of normal request processing under limits
- **Rate limit exceeded scenarios**: Testing 429 responses with proper Retry-After headers
- **Unauthenticated request handling**: Validation of auth middleware interaction
- **Bucket state management**: Testing token bucket refill and consumption logic

**Section sources**
- [conftest.py:196-204](file://app/backend/tests/conftest.py#L196-L204)
- [rate_limit.py:16-144](file://app/backend/middleware/rate_limit.py#L16-L144)
- [test_rate_limiting.py:1-85](file://app/backend/tests/test_rate_limiting.py#L1-L85)

### Appendix E: Enhanced Monthly Usage Reset Infrastructure
**New Section**: The enhanced test infrastructure now includes comprehensive monthly usage reset validation:

#### Automatic Reset Logic Implementation
The enhanced monthly reset system provides:
- **UTC timezone consistency**: Proper handling of time zone conversions
- **Edge case handling**: Year transition logic for December to January resets
- **Timestamp preservation**: Maintenance of usage_reset_at for audit trails
- **Integration with analysis routes**: Automatic reset during usage tracking
- **Database transaction safety**: Proper commit handling for reset operations

#### Comprehensive Test Coverage
The monthly reset testing includes:
- **New month detection**: Validation of month boundary detection logic
- **Same month preservation**: Testing of unchanged counter behavior
- **Historical data validation**: Edge case handling for reset scenarios
- **Integration testing**: Validation of reset logic in analysis route context
- **Error scenario testing**: Testing of reset failures and edge cases

#### Usage Tracking Integration
The reset system integrates with:
- **Analysis route usage tracking**: Automatic reset before usage increments
- **Subscription check endpoints**: Reset validation for usage checking
- **Admin reset functionality**: Manual reset capability for testing scenarios
- **Usage history reporting**: Audit trail maintenance for reset operations

**Section sources**
- [subscription.py:85-97](file://app/backend/routes/subscription.py#L85-L97)
- [test_subscription.py:312-355](file://app/backend/tests/test_subscription.py#L312-L355)
- [analyze.py:490-525](file://app/backend/routes/analyze.py#L490-L525)

### Appendix F: Enhanced Test Artifact Cleanup Infrastructure
**New Section**: The enhanced test infrastructure now includes systematic cleanup of temporary test artifacts:

#### Comprehensive Artifact Exclusion Patterns
The enhanced .gitignore patterns now include:
- **Coverage reports**: `.coverage`, `htmlcov/`
- **Pytest cache**: `.pytest_cache/`
- **Test output files**: `pytest_summary.txt`, `test_full_output.txt`
- **Generic output patterns**: `*_output*.txt`, `*_results*.txt`, `*_summary*.txt`
- **Temporary files**: `.commit-msg.txt`

#### Enhanced Test Runner Cleanup
The enhanced test runners provide:
- **Temporary file logging**: Structured output capture with rotation
- **Cross-platform compatibility**: PowerShell and Bash script support
- **Error handling**: Detailed error output capture and reporting
- **Environment validation**: Prerequisite checking and validation
- **Resource cleanup**: Proper cleanup of test artifacts and temporary files

#### CI/CD Stability Improvements
The enhanced cleanup infrastructure ensures:
- **Clean test environments**: Isolation of test artifacts from source code
- **Improved CI reliability**: Reduced test flakiness through artifact isolation
- **Better resource management**: Efficient cleanup of temporary files and logs
- **Cross-platform consistency**: Uniform cleanup behavior across different environments

**Section sources**
- [.gitignore:42-47](file://.gitignore#L42-L47)
- [run-full-tests.sh:31-42](file://scripts/run-full-tests.sh#L31-L42)
- [test-locally.ps1:54-59](file://test-locally.ps1#L54-L59)

### Appendix G: Enhanced Administrative and Billing Test Coverage
**New Section**: The substantially expanded test suite now includes comprehensive coverage of administrative and billing functionality:

#### Administrative API Test Coverage
- **Permission Testing**: Comprehensive 403 response validation for unauthorized access attempts
- **Tenant Management**: Full CRUD operations with pagination, search, and filtering
- **Plan Management**: Subscription plan changes with audit logging and validation
- **Usage Management**: Analyses count and storage usage adjustments
- **Audit Logging**: Comprehensive audit trail validation for all administrative actions
- **Metrics Reporting**: Platform-wide analytics and usage trend validation

#### Billing System Test Coverage
- **Provider Abstraction**: Manual, Stripe, and Razorpay provider testing
- **Factory Pattern**: Provider selection logic and fallback mechanisms
- **Configuration Management**: Billing configuration persistence and retrieval
- **Route Integration**: Checkout sessions, webhook processing, and subscription status
- **Error Handling**: Graceful degradation for unavailable payment providers

#### Operational Monitoring Test Coverage
- **Email Service**: SMTP configuration, notification delivery, and template formatting
- **Feature Flags**: Global flags, tenant overrides, and middleware integration
- **Quota Enforcement**: Subscription plan limits, usage tracking, and HTTP endpoint integration
- **Rate Limiting**: API throttling, abuse prevention, and configuration management
- **Tenant Suspension**: Suspension lifecycle, status validation, and audit logging
- **Webhook Processing**: Payment processor integration and event handling

**Section sources**
- [test_admin_api.py:1-467](file://app/backend/tests/test_admin_api.py#L1-467)
- [test_admin_metrics.py:1-159](file://app/backend/tests/test_admin_metrics.py#L1-159)
- [test_billing.py:1-328](file://app/backend/tests/test_billing.py#L1-328)
- [test_email_service.py:1-232](file://app/backend/tests/test_email_service.py#L1-232)
- [test_feature_flags.py:1-233](file://app/backend/tests/test_feature_flags.py#L1-233)
- [test_quota_enforcement.py:1-240](file://app/backend/tests/test_quota_enforcement.py#L1-240)
- [test_rate_limiting.py](file://app/backend/tests/test_rate_limiting.py)
- [test_tenant_suspension.py](file://app/backend/tests/test_tenant_suspension.py)
- [test_webhooks.py](file://app/backend/tests/test_webhooks.py)