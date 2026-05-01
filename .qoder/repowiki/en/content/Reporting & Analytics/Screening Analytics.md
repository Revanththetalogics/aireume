# Screening Analytics

<cite>
**Referenced Files in This Document**
- [dashboard.py](file://app/backend/routes/dashboard.py)
- [metrics.py](file://app/backend/services/metrics.py)
- [consensus_analyzer.py](file://app/backend/services/consensus_analyzer.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [AnalyticsPage.jsx](file://app/frontend/src/pages/AnalyticsPage.jsx)
- [analysis_service.py](file://app/backend/services/analysis_service.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [fit_scorer.py](file://app/backend/services/fit_scorer.py)
- [main.py](file://app/backend/main.py)
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

## Introduction

Screening Analytics is a comprehensive system within the ARIA (AI Resume Intelligence) platform that provides real-time insights into the candidate screening process. The system combines automated resume analysis with advanced analytics capabilities to deliver actionable intelligence for recruitment teams. It features a sophisticated multi-model consensus analyzer, comprehensive dashboard metrics, and a modern React-based frontend interface.

The analytics system processes screening results through multiple analytical lenses, providing organizations with detailed insights into their recruitment pipeline performance, candidate quality trends, and decision-making effectiveness. Built with scalability and reliability in mind, the system handles large volumes of screening data while maintaining real-time responsiveness.

## Project Structure

The Screening Analytics system follows a layered architecture with clear separation of concerns:

```mermaid
graph TB
subgraph "Frontend Layer"
FE1[AnalyticsPage.jsx]
FE2[React Components]
FE3[Chart Libraries]
end
subgraph "Backend API Layer"
API1[Dashboard Routes]
API2[Analysis Routes]
API3[Authentication Middleware]
end
subgraph "Service Layer"
SVC1[Consensus Analyzer]
SVC2[Fit Scorer]
SVC3[Hybrid Pipeline]
SVC4[Metrics Collector]
end
subgraph "Data Layer"
DB1[Screening Results]
DB2[Candidates]
DB3[Role Templates]
DB4[Usage Logs]
end
FE1 --> API1
FE2 --> API1
FE3 --> API1
API1 --> SVC1
API1 --> SVC2
API1 --> SVC3
API1 --> SVC4
SVC1 --> DB1
SVC2 --> DB1
SVC3 --> DB1
SVC4 --> DB1
```

**Diagram sources**
- [dashboard.py:1-382](file://app/backend/routes/dashboard.py#L1-L382)
- [AnalyticsPage.jsx:1-452](file://app/frontend/src/pages/AnalyticsPage.jsx#L1-L452)

**Section sources**
- [dashboard.py:1-382](file://app/backend/routes/dashboard.py#L1-L382)
- [AnalyticsPage.jsx:1-452](file://app/frontend/src/pages/AnalyticsPage.jsx#L1-L452)

## Core Components

### Dashboard Analytics Engine

The dashboard analytics engine serves as the central hub for screening analytics, providing comprehensive insights into the recruitment pipeline. It processes screening results through multiple analytical filters to generate actionable metrics.

Key features include:
- Real-time dashboard summaries with action items and pipeline status
- Weekly activity tracking with candidate analysis trends
- Comprehensive screening analytics with score distributions and recommendation breakdowns
- JD effectiveness tracking across different roles and departments
- Pass-through funnel analysis showing conversion rates from initial screening to final hiring decisions

### Consensus Analyzer

The consensus analyzer implements a sophisticated multi-model approach to reduce single-model bias in candidate evaluation. By running analyses through multiple language models and aggregating results statistically, it provides more reliable and consistent screening outcomes.

Core capabilities:
- Parallel analysis execution across multiple models (gemma2:27b, llama3.1:8b, qwen2.5:14b)
- Statistical aggregation using median-based scoring for robustness
- Model agreement metrics to assess confidence levels
- Fallback mechanisms when individual models fail
- Comprehensive result merging for strengths, weaknesses, and recommendations

### Analytics Data Models

The system utilizes a comprehensive set of data models to capture and analyze screening analytics:

```mermaid
classDiagram
class ScreeningResult {
+int id
+int tenant_id
+int candidate_id
+int role_template_id
+string analysis_result
+string status
+datetime timestamp
+int deterministic_score
+float domain_match_score
+float core_skill_score
}
class Candidate {
+int id
+int tenant_id
+string name
+string email
+string resume_file_hash
+string raw_resume_text
+string parsed_skills
+string gap_analysis_json
+float total_years_exp
}
class RoleTemplate {
+int id
+int tenant_id
+string name
+string jd_text
+string scoring_weights
+datetime created_at
}
class AnalysisResponse {
+int fit_score
+string final_recommendation
+string[] strengths
+string[] weaknesses
+dict[] employment_gaps
+dict risk_signals
+dict score_breakdown
+string[] missing_skills
}
ScreeningResult --> Candidate : "belongs to"
ScreeningResult --> RoleTemplate : "evaluated for"
AnalysisResponse --> ScreeningResult : "populates"
```

**Diagram sources**
- [db_models.py:135-170](file://app/backend/models/db_models.py#L135-L170)
- [db_models.py:102-133](file://app/backend/models/db_models.py#L102-L133)
- [db_models.py:175-188](file://app/backend/models/db_models.py#L175-L188)
- [schemas.py:119-165](file://app/backend/models/schemas.py#L119-L165)

**Section sources**
- [db_models.py:135-170](file://app/backend/models/db_models.py#L135-L170)
- [schemas.py:119-165](file://app/backend/models/schemas.py#L119-L165)

## Architecture Overview

The Screening Analytics system employs a microservices architecture with clear separation between data processing, analytics computation, and presentation layers:

```mermaid
sequenceDiagram
participant Client as "AnalyticsPage.jsx"
participant API as "Dashboard Routes"
participant Service as "Analytics Services"
participant DB as "Database"
participant LLM as "Consensus Analyzer"
Client->>API : GET /api/analytics/screening
API->>Service : Process analytics request
Service->>DB : Query screening results
DB-->>Service : Return filtered results
Service->>Service : Aggregate metrics
Service->>LLM : Generate consensus analysis
LLM-->>Service : Return aggregated results
Service-->>API : Return analytics data
API-->>Client : JSON response with charts
Note over Client,LLM : Real-time analytics with multi-model consensus
```

**Diagram sources**
- [dashboard.py:240-382](file://app/backend/routes/dashboard.py#L240-L382)
- [consensus_analyzer.py:66-131](file://app/backend/services/consensus_analyzer.py#L66-L131)

The architecture ensures high availability and fault tolerance through:
- Asynchronous processing for long-running analytics computations
- Database caching for frequently accessed analytics data
- Multi-model consensus for improved accuracy and reliability
- Comprehensive error handling and fallback mechanisms

**Section sources**
- [dashboard.py:240-382](file://app/backend/routes/dashboard.py#L240-L382)
- [consensus_analyzer.py:66-131](file://app/backend/services/consensus_analyzer.py#L66-L131)

## Detailed Component Analysis

### Dashboard Analytics Implementation

The dashboard analytics implementation provides comprehensive screening insights through multiple analytical dimensions:

#### Summary Dashboard
The summary dashboard aggregates key metrics for quick operational oversight:
- Pending review items requiring immediate attention
- Active analyses currently in progress
- Shortlisted candidates awaiting final decisions
- Pipeline distribution by job role and department
- Weekly performance metrics including average fit scores and shortlist rates

#### Activity Feed
The activity feed provides real-time visibility into recent screening activities:
- Recent candidate analyses with timestamps
- Fit scores and final recommendations
- Candidate and job role associations
- Status updates and decision timelines

#### Comprehensive Analytics
The comprehensive analytics endpoint delivers detailed screening insights:
- Fit score distributions across different ranges (0-20, 21-40, etc.)
- Recommendation distribution (Shortlist, Consider, Reject)
- Daily analysis volume trends
- Top skill gaps identified across the candidate pool
- JD effectiveness metrics including average scores and shortlist rates
- Pass-through funnel analysis showing conversion rates

```mermaid
flowchart TD
Start([Analytics Request]) --> Filter[Filter by Period]
Filter --> Query[Query Screening Results]
Query --> Aggregate[Aggregate Metrics]
Aggregate --> Scores[Calculate Fit Scores]
Aggregate --> Recommendations[Count Recommendations]
Aggregate --> Trends[Track Daily Trends]
Aggregate --> Gaps[Analyze Skill Gaps]
Aggregate --> JD[JD Effectiveness]
Scores --> Results[Return Analytics Data]
Recommendations --> Results
Trends --> Results
Gaps --> Results
JD --> Results
Results --> End([Render Charts])
```

**Diagram sources**
- [dashboard.py:240-382](file://app/backend/routes/dashboard.py#L240-L382)

**Section sources**
- [dashboard.py:240-382](file://app/backend/routes/dashboard.py#L240-L382)

### Consensus Analyzer Architecture

The consensus analyzer implements a sophisticated multi-model approach to candidate evaluation:

#### Multi-Model Analysis
The system runs candidate analyses through multiple language models in parallel:
- Primary model: gemma2:27b (balanced performance)
- Alternative model: llama3.1:8b (efficient processing)
- Diverse model: qwen2.5:14b (different training data perspective)

#### Statistical Aggregation
Results are aggregated using robust statistical methods:
- Median-based scoring for fit scores, technical depth, and communication quality
- Consensus recommendation through majority voting
- Model agreement calculation based on coefficient of variation
- Comprehensive merging of strengths, weaknesses, and risk assessments

#### Quality Assurance
The system includes comprehensive quality assurance measures:
- Model failure detection and fallback mechanisms
- Latency tracking for performance monitoring
- Confidence scoring based on model agreement
- Bias mitigation through multi-perspective analysis

```mermaid
classDiagram
class ConsensusAnalyzer {
+string[] models
+float timeout
+analyze_with_consensus(transcript, jd_text, candidate_name) Dict
+_aggregate_results(model_results) Dict
+_calculate_agreement(model_results) float
}
class ModelResult {
+string model_name
+bool success
+Dict~Any~ result
+string error
+int latency_ms
}
class TranscriptAnalysisResult {
+int fit_score
+int technical_depth
+int communication_quality
+JdAlignmentItem[] jd_alignment
+string[] strengths
+string[] areas_for_improvement
+string bias_note
+string recommendation
}
ConsensusAnalyzer --> ModelResult : "processes"
ConsensusAnalyzer --> TranscriptAnalysisResult : "produces"
```

**Diagram sources**
- [consensus_analyzer.py:44-131](file://app/backend/services/consensus_analyzer.py#L44-L131)
- [consensus_analyzer.py:34-42](file://app/backend/services/consensus_analyzer.py#L34-L42)
- [schemas.py:364-387](file://app/backend/models/schemas.py#L364-L387)

**Section sources**
- [consensus_analyzer.py:44-131](file://app/backend/services/consensus_analyzer.py#L44-L131)
- [schemas.py:364-387](file://app/backend/models/schemas.py#L364-L387)

### Frontend Analytics Interface

The frontend analytics interface provides an intuitive dashboard for exploring screening insights:

#### Interactive Charts and Visualizations
The interface features responsive charts powered by Recharts:
- Area charts for daily analysis trends
- Bar charts for score distributions and skill gaps
- Pie charts for recommendation distributions
- Interactive dashboards with customizable time periods

#### Real-Time Data Updates
The frontend implements real-time data synchronization:
- Period selection (Last 7 Days, 30 Days, 90 Days)
- Manual refresh capabilities
- Loading states and error handling
- Responsive design for various screen sizes

#### User Experience Features
Enhanced user experience through:
- Color-coded score indicators (green for high, amber for medium, red for low)
- Sortable tables for JD effectiveness analysis
- Hover tooltips with detailed metric information
- Persistent user preferences and selections

```mermaid
sequenceDiagram
participant User as "Recruiter"
participant UI as "AnalyticsPage.jsx"
participant API as "Dashboard API"
participant Charts as "Chart Components"
User->>UI : Select time period
UI->>API : Fetch analytics data
API-->>UI : Return JSON analytics
UI->>Charts : Render visualizations
Charts-->>User : Display interactive charts
User->>UI : Interact with charts
UI->>Charts : Update visualization
Charts-->>User : Enhanced insights
```

**Diagram sources**
- [AnalyticsPage.jsx:189-452](file://app/frontend/src/pages/AnalyticsPage.jsx#L189-L452)

**Section sources**
- [AnalyticsPage.jsx:189-452](file://app/frontend/src/pages/AnalyticsPage.jsx#L189-L452)

### Analytics Data Processing Pipeline

The analytics data processing pipeline transforms raw screening results into actionable insights:

#### Data Collection and Filtering
The system collects screening results within specified time periods and applies tenant-based filtering for multi-tenant environments. Data is processed through multiple aggregation layers to ensure accuracy and completeness.

#### Metric Calculation
Comprehensive metrics are calculated across multiple dimensions:
- Statistical aggregations (averages, distributions, conversions)
- Trend analysis across selected time periods
- Comparative analysis between different job roles and departments
- Performance benchmarking against historical data

#### Quality Assurance
Data quality is ensured through:
- Input validation and sanitization
- Missing data handling and fallback mechanisms
- Consistency checks across different analytical dimensions
- Performance monitoring and alerting

**Section sources**
- [dashboard.py:240-382](file://app/backend/routes/dashboard.py#L240-L382)

## Dependency Analysis

The Screening Analytics system exhibits well-managed dependencies with clear boundaries between components:

```mermaid
graph TB
subgraph "External Dependencies"
EX1[FastAPI]
EX2[SQLAlchemy]
EX3[Prometheus Client]
EX4[Recharts]
end
subgraph "Internal Dependencies"
INT1[Dashboard Routes]
INT2[Consensus Analyzer]
INT3[Fit Scorer]
INT4[Hybrid Pipeline]
INT5[Metrics Service]
end
subgraph "Data Dependencies"
DB1[Screening Results]
DB2[Candidates]
DB3[Role Templates]
DB4[Usage Logs]
end
EX1 --> INT1
EX2 --> INT1
EX3 --> INT5
EX4 --> INT1
INT1 --> INT2
INT1 --> INT3
INT1 --> INT4
INT1 --> INT5
INT2 --> DB1
INT3 --> DB1
INT4 --> DB1
INT5 --> DB1
```

**Diagram sources**
- [main.py:325-393](file://app/backend/main.py#L325-L393)
- [dashboard.py:10-20](file://app/backend/routes/dashboard.py#L10-L20)

The dependency structure ensures:
- Loose coupling between components through well-defined interfaces
- Clear separation of concerns with specialized services
- Scalable architecture supporting concurrent analytics processing
- Robust error handling and graceful degradation

**Section sources**
- [main.py:325-393](file://app/backend/main.py#L325-L393)
- [dashboard.py:10-20](file://app/backend/routes/dashboard.py#L10-L20)

## Performance Considerations

The Screening Analytics system is designed for high performance and scalability:

### Database Optimization
- Indexes on frequently queried fields (tenant_id, timestamp, status)
- Efficient query patterns using SQLAlchemy ORM
- Caching strategies for frequently accessed analytics data
- Connection pooling for optimal database resource utilization

### Asynchronous Processing
- Non-blocking analytics computation using asyncio
- Background task processing for heavy analytics operations
- Semaphore-based concurrency control for external API calls
- Graceful shutdown handling for background processes

### Memory Management
- Efficient data structures for large-scale analytics
- Streaming responses for large datasets
- Memory-efficient aggregation algorithms
- Proper resource cleanup and garbage collection

### Monitoring and Observability
- Comprehensive metrics collection using Prometheus
- Request correlation for tracing distributed operations
- Health checks for external dependencies (Ollama, database)
- Performance monitoring with automatic alerts

**Section sources**
- [metrics.py:1-76](file://app/backend/services/metrics.py#L1-L76)
- [main.py:332-339](file://app/backend/main.py#L332-L339)

## Troubleshooting Guide

Common issues and their resolutions in the Screening Analytics system:

### Analytics Data Issues
**Problem**: Missing or incomplete analytics data
**Causes**: 
- Database connectivity issues
- Insufficient screening results for the selected period
- Tenant isolation problems
- Data processing delays

**Solutions**:
- Verify database connectivity and permissions
- Check tenant membership and access rights
- Review analytics processing logs for errors
- Validate time period selections and filters

### Performance Degradation
**Problem**: Slow analytics response times
**Causes**:
- Database query performance issues
- Insufficient indexing on analytical queries
- High concurrent analytics requests
- External dependency timeouts

**Solutions**:
- Optimize database queries and add appropriate indexes
- Implement query result caching for frequently accessed periods
- Scale database resources or implement read replicas
- Monitor and tune external dependency performance

### Multi-Model Analysis Failures
**Problem**: Consensus analyzer failures or inconsistent results
**Causes**:
- LLM service unavailability
- Model loading issues
- Network connectivity problems
- Resource exhaustion

**Solutions**:
- Verify LLM service health and model availability
- Check network connectivity to external services
- Monitor resource usage and scale accordingly
- Implement fallback mechanisms for critical failures

### Frontend Rendering Issues
**Problem**: Charts not displaying or data not loading
**Causes**:
- API endpoint failures
- Network connectivity issues
- JavaScript errors in chart rendering
- Browser compatibility problems

**Solutions**:
- Verify API endpoint accessibility and response formats
- Check browser console for JavaScript errors
- Validate chart data structures and formats
- Test across different browsers and devices

**Section sources**
- [dashboard.py:240-382](file://app/backend/routes/dashboard.py#L240-L382)
- [consensus_analyzer.py:66-131](file://app/backend/services/consensus_analyzer.py#L66-L131)

## Conclusion

The Screening Analytics system represents a comprehensive solution for modern recruitment analytics, combining advanced machine learning capabilities with intuitive visualization tools. The system's multi-model consensus approach ensures reliable and unbiased candidate evaluation, while the comprehensive analytics dashboard provides actionable insights for recruitment teams.

Key strengths of the system include:
- **Robust Multi-Model Analysis**: Reduces bias and improves accuracy through statistical aggregation
- **Real-Time Analytics**: Provides immediate insights into screening performance and trends
- **Scalable Architecture**: Designed to handle large volumes of screening data efficiently
- **Comprehensive Visualization**: Offers multiple perspectives on screening analytics through interactive charts
- **Multi-Tenant Support**: Enables isolated analytics for different organizations within shared infrastructure

The system's modular architecture facilitates easy maintenance and extension, while comprehensive monitoring and error handling ensure reliable operation in production environments. Future enhancements could include advanced predictive analytics, automated trend identification, and integration with external HRIS systems for enriched candidate insights.