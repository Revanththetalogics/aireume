# Platform Metrics Dashboard

<cite>
**Referenced Files in This Document**
- [metrics.py](file://app/backend/services/metrics.py)
- [admin.py](file://app/backend/routes/admin.py)
- [api.js](file://app/frontend/src/lib/api.js)
- [MetricsPage.jsx](file://app/frontend/src/pages/admin/MetricsPage.jsx)
- [Dashboard.jsx](file://app/frontend/src/pages/Dashboard.jsx)
- [DashboardNew.jsx](file://app/frontend/src/pages/DashboardNew.jsx)
- [schemas.py](file://app/backend/models/schemas.py)
- [skill_trend_service.py](file://app/backend/services/skill_trend_service.py)
- [main.py](file://app/backend/main.py)
- [test_admin_metrics.py](file://app/backend/tests/test_admin_metrics.py)
</cite>

## Update Summary
**Changes Made**
- Updated Core Components section to reflect the new comprehensive Recharts-based analytics interface
- Enhanced Detailed Component Analysis with new chart components and data visualization features
- Added new section on Interactive Data Visualization covering Recharts implementation
- Updated Frontend Dashboard Implementation with detailed chart component analysis
- Enhanced Dependency Analysis to include Recharts integration
- Updated Architecture Overview to show the new chart-based data visualization flow

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Interactive Data Visualization](#interactive-data-visualization)
7. [Dependency Analysis](#dependency-analysis)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)

## Introduction
The Platform Metrics Dashboard is a comprehensive analytics solution for the Resume AI by ThetaLogics platform. It provides real-time visibility into platform-wide operations, tenant usage patterns, and key performance indicators. The dashboard combines backend metrics collection, advanced analytics endpoints, and a modern frontend interface featuring sophisticated Recharts-based data visualization to deliver actionable insights for platform administrators and stakeholders.

The system tracks critical metrics including tenant engagement, analysis volumes, storage utilization, revenue indicators, and operational health. It leverages Prometheus metrics for infrastructure monitoring and custom analytics endpoints for business intelligence, providing both granular operational data and high-level strategic insights through interactive chart components.

## Project Structure
The Platform Metrics Dashboard follows a modular architecture with clear separation between backend services, frontend components, and supporting infrastructure:

```mermaid
graph TB
subgraph "Backend Services"
A[Metrics Collection]
B[Analytics Endpoints]
C[Admin APIs]
D[Skill Trends]
end
subgraph "Frontend Components"
E[Metrics Dashboard]
F[Usage Widgets]
G[Recharts Visualization]
H[KPI Cards]
I[Interactive Charts]
end
subgraph "Infrastructure"
J[Prometheus Metrics]
K[Database Layer]
L[API Gateway]
end
A --> J
B --> K
C --> K
D --> K
E --> F
E --> G
F --> H
G --> I
H --> J
I --> J
J --> L
K --> L
```

**Diagram sources**
- [main.py:350-358](file://app/backend/main.py#L350-L358)
- [metrics.py:1-76](file://app/backend/services/metrics.py#L1-L76)
- [admin.py:1439-1500](file://app/backend/routes/admin.py#L1439-L1500)

**Section sources**
- [main.py:343-428](file://app/backend/main.py#L343-L428)
- [metrics.py:1-76](file://app/backend/services/metrics.py#L1-L76)
- [admin.py:1439-1500](file://app/backend/routes/admin.py#L1439-L1500)

## Core Components

### Backend Metrics Infrastructure
The metrics system is built around Prometheus integration and custom metric definitions:

**Custom Metrics Categories:**
- **LLM Operations Metrics**: Track language model performance and reliability
- **Guardrail Compliance Metrics**: Monitor AI safety and quality controls
- **Resume Processing Metrics**: Measure parsing efficiency and throughput
- **Batch Operation Metrics**: Track bulk analysis performance

**Section sources**
- [metrics.py:10-76](file://app/backend/services/metrics.py#L10-L76)

### Admin Platform Metrics
Platform-wide administrative metrics provide strategic insights:

**Metrics Overview Endpoint**: `/api/admin/metrics/overview`
- Tenant distribution analysis
- Usage pattern tracking
- Revenue estimation
- Storage utilization
- Plan distribution

**Usage Trends Endpoint**: `/api/admin/metrics/usage-trends`
- Historical analysis volume tracking
- User activity patterns
- Customizable time ranges

**Section sources**
- [admin.py:1439-1516](file://app/backend/routes/admin.py#L1439-L1516)
- [admin.py:1519-1553](file://app/backend/routes/admin.py#L1519-L1553)

### Frontend Dashboard Implementation
The React-based frontend delivers interactive visualizations using Recharts:

**MetricsPage Component**: Advanced administrative dashboard with comprehensive analytics interface
- Multi-dimensional KPI cards with trend indicators
- Interactive time-series charts using Recharts
- Tenant comparison tables with sortable columns
- Real-time data refresh capabilities with loading states
- Responsive design with skeleton loaders
- Custom tooltip styling and formatting

**Dashboard Components**: Multiple dashboard implementations
- Primary user interface with usage tracking
- Advanced dashboard with pipeline visualization
- Activity feed and analytics integration

**Section sources**
- [MetricsPage.jsx:109-432](file://app/frontend/src/pages/admin/MetricsPage.jsx#L109-L432)
- [Dashboard.jsx:204-335](file://app/frontend/src/pages/Dashboard.jsx#L204-L335)
- [DashboardNew.jsx:182-740](file://app/frontend/src/pages/DashboardNew.jsx#L182-L740)

## Architecture Overview

The Platform Metrics Dashboard employs a distributed architecture with clear separation of concerns and sophisticated data visualization:

```mermaid
sequenceDiagram
participant Client as "Browser Client"
participant Frontend as "React Dashboard"
participant API as "FastAPI Backend"
participant DB as "Database Layer"
participant Metrics as "Prometheus"
Client->>Frontend : User Interaction
Frontend->>API : HTTP Request
API->>DB : Database Query
DB-->>API : Query Results
API->>Metrics : Metric Collection
Metrics-->>API : Performance Data
API-->>Frontend : JSON Response
Frontend->>Frontend : Recharts Rendering
Frontend-->>Client : Interactive Dashboard
Note over Client,Metrics : Real-time monitoring and analytics
```

**Diagram sources**
- [main.py:350-358](file://app/backend/main.py#L350-L358)
- [api.js:1-800](file://app/frontend/src/lib/api.js#L1-L800)

The architecture supports both synchronous and asynchronous data processing, with Prometheus metrics providing infrastructure-level monitoring alongside application-specific analytics. The new Recharts-based frontend adds sophisticated visualization capabilities for enhanced data interpretation.

**Section sources**
- [main.py:343-428](file://app/backend/main.py#L343-L428)
- [api.js:1-800](file://app/frontend/src/lib/api.js#L1-L800)

## Detailed Component Analysis

### Prometheus Metrics Integration
The backend integrates with Prometheus for comprehensive infrastructure monitoring:

```mermaid
classDiagram
class MetricsCollection {
+Histogram llm_call_duration_seconds
+Counter llm_fallback_total
+Counter guardrail_hallucination_total
+Counter guardrail_injection_blocked_total
+Histogram resume_parse_duration_seconds
+Histogram batch_size
}
class PrometheusInstrumentator {
+instrument(app)
+expose(endpoint)
+should_group_status_codes
+should_ignore_untemplated
}
class BackendServices {
+analyze_service
+guardrail_service
+parser_service
+queue_manager
}
MetricsCollection --> PrometheusInstrumentator : "configured by"
PrometheusInstrumentator --> BackendServices : "monitors"
```

**Diagram sources**
- [metrics.py:10-76](file://app/backend/services/metrics.py#L10-L76)
- [main.py:350-358](file://app/backend/main.py#L350-L358)

The metrics system captures critical performance indicators including LLM call durations, fallback occurrences, and parsing efficiency. These metrics inform capacity planning and performance optimization decisions.

**Section sources**
- [metrics.py:10-76](file://app/backend/services/metrics.py#L10-L76)
- [main.py:350-358](file://app/backend/main.py#L350-L358)

### Analytics Data Processing Pipeline
The analytics system processes data through multiple stages:

```mermaid
flowchart TD
A[Raw Data Collection] --> B[Data Validation]
B --> C[Statistical Aggregation]
C --> D[Pattern Recognition]
D --> E[Visualization Ready]
F[Usage Logs] --> B
G[Screening Results] --> B
H[Tenant Data] --> B
I[Storage Metrics] --> B
C --> J[Daily Snapshots]
C --> K[Weekly Reports]
C --> L[Monthly Summaries]
J --> M[Real-time Dashboards]
K --> M
L --> M
```

**Diagram sources**
- [admin.py:1439-1516](file://app/backend/routes/admin.py#L1439-L1516)
- [skill_trend_service.py:32-164](file://app/backend/services/skill_trend_service.py#L32-L164)

The pipeline handles diverse data sources including usage logs, screening results, and tenant information, transforming raw data into meaningful business insights.

**Section sources**
- [admin.py:1439-1516](file://app/backend/routes/admin.py#L1439-L1516)
- [skill_trend_service.py:32-164](file://app/backend/services/skill_trend_service.py#L32-L164)

### Frontend Dashboard Components
The React-based frontend provides interactive data visualization with sophisticated chart components:

```mermaid
classDiagram
class MetricsPage {
+useState metrics
+useState trends
+useState tenants
+useState loading
+useState error
+useState days
+useEffect fetchData
+useCallback fetchData
+SkeletonCard
+SkeletonChart
+formatNum
+formatMs
+fmtDateTick
+customTooltipStyle
}
class KPICard {
+string label
+string value
+string sub
+JSX icon
+string color
+number trend
+colorMap
}
class ChartComponents {
+LineChart
+BarChart
+AreaChart
+ResponsiveContainer
+CartesianGrid
+XAxis
+YAxis
+Tooltip
+Line
+Bar
+Area
}
class Dashboard {
+useState usage
+useState loading
+useSubscription hook
+deriveActiveStages
+handleSubmit
}
MetricsPage --> KPICard : "renders"
MetricsPage --> ChartComponents : "uses"
Dashboard --> KPICard : "displays"
```

**Diagram sources**
- [MetricsPage.jsx:109-432](file://app/frontend/src/pages/admin/MetricsPage.jsx#L109-L432)
- [Dashboard.jsx:204-335](file://app/frontend/src/pages/Dashboard.jsx#L204-L335)
- [DashboardNew.jsx:182-740](file://app/frontend/src/pages/DashboardNew.jsx#L182-L740)

The frontend components utilize React hooks for state management and Recharts for sophisticated data visualization, providing responsive and interactive user experiences with comprehensive charting capabilities.

**Section sources**
- [MetricsPage.jsx:109-432](file://app/frontend/src/pages/admin/MetricsPage.jsx#L109-L432)
- [Dashboard.jsx:204-335](file://app/frontend/src/pages/Dashboard.jsx#L204-L335)
- [DashboardNew.jsx:182-740](file://app/frontend/src/pages/DashboardNew.jsx#L182-L740)

## Interactive Data Visualization

The MetricsPage.jsx introduces a comprehensive Recharts-based analytics interface with sophisticated interactive visualizations:

### Chart Components and Data Visualization
The dashboard implements four distinct chart types for comprehensive data representation:

**Line Chart - Analyses per Day**
- Monotone line visualization for time-series analysis trends
- Responsive container with dynamic sizing
- Custom tooltip with formatted date labels
- Smooth curve interpolation for better readability

**Bar Chart - Active Users per Day**
- Vertical bar visualization for daily user activity
- Gradient styling with brand-specific colors
- Rounded bar tops for modern aesthetic
- Hover interaction with active dots

**Area Chart - Storage Usage Trend**
- Gradient-filled area chart for storage consumption
- Linear gradient definition for visual depth
- Unit labeling for gigabyte measurements
- Smooth monotone interpolation

**Table Component - Top Activity Tenants**
- Sortable table with ranking system
- Responsive design with horizontal scrolling
- Hover effects for improved user experience
- Comprehensive tenant information display

### Interactive Features
The visualization system includes advanced interactive capabilities:

**Time Range Selection**
- Configurable time ranges (7, 30, 90, 365 days)
- Dynamic data fetching based on selection
- State management for time period persistence

**Loading States and Skeleton Screens**
- Skeleton card placeholders during data loading
- Skeleton chart placeholders for complex visualizations
- Pulse animations for improved perceived performance

**Error Handling and Retry Mechanisms**
- Comprehensive error state management
- Retry button for failed data fetches
- User-friendly error messaging

**Custom Styling and Theming**
- Brand-consistent color schemes
- Custom tooltip styling with branded appearance
- Responsive design for all screen sizes
- Modern glass-morphism UI elements

**Section sources**
- [MetricsPage.jsx:139-432](file://app/frontend/src/pages/admin/MetricsPage.jsx#L139-L432)

## Dependency Analysis

The Platform Metrics Dashboard exhibits well-structured dependencies with clear separation of concerns and enhanced visualization capabilities:

```mermaid
graph TB
subgraph "External Dependencies"
A[Prometheus Client]
B[FastAPI]
C[React 18]
D[Recharts 2.12]
E[SQLAlchemy]
F[Lucide React Icons]
end
subgraph "Internal Modules"
G[metrics.py]
H[admin.py]
I[MetricsPage.jsx]
J[Dashboard.jsx]
K[DashboardNew.jsx]
L[schemas.py]
M[skill_trend_service.py]
N[api.js]
end
A --> G
B --> H
C --> I
C --> J
C --> K
D --> I
E --> H
E --> M
F --> I
G --> A
H --> N
I --> N
J --> N
K --> N
L --> H
M --> H
```

**Diagram sources**
- [metrics.py:8](file://app/backend/services/metrics.py#L8)
- [admin.py:11](file://app/backend/routes/admin.py#L11)
- [MetricsPage.jsx:1-26](file://app/frontend/src/pages/admin/MetricsPage.jsx#L1-L26)
- [Dashboard.jsx:5](file://app/frontend/src/pages/Dashboard.jsx#L5)
- [DashboardNew.jsx:1-16](file://app/frontend/src/pages/DashboardNew.jsx#L1-L16)

The dependency graph reveals a clean architecture where external libraries like Recharts and Lucide React enhance functionality without creating tight coupling. The new Recharts integration provides sophisticated visualization capabilities while maintaining the existing modular structure.

**Section sources**
- [metrics.py:8](file://app/backend/services/metrics.py#L8)
- [admin.py:11](file://app/backend/routes/admin.py#L11)

## Performance Considerations

The Platform Metrics Dashboard is designed with several performance optimization strategies, enhanced by the new Recharts-based visualization:

### Database Query Optimization
- **Efficient Filtering**: Queries use appropriate WHERE clauses and indexes
- **Aggregation Functions**: SUM and COUNT operations minimize data transfer
- **Pagination Support**: Large datasets are processed in chunks
- **Connection Pooling**: Database connections are managed efficiently

### Caching Strategies
- **Client-side Caching**: React components cache frequently accessed data
- **Server-side Aggregation**: Pre-computed metrics reduce real-time calculation overhead
- **Time-based Expiration**: Data freshness is balanced with performance needs
- **Chart Data Caching**: Visualization data is cached to prevent unnecessary re-rendering

### Scalability Features
- **Asynchronous Processing**: Long-running analytics computations use background tasks
- **Rate Limiting**: API endpoints implement request throttling
- **Resource Management**: Memory and CPU usage are monitored and controlled
- **Chart Optimization**: Recharts components are optimized for large datasets

### Visualization Performance
- **Responsive Containers**: Charts adapt to container size changes efficiently
- **Lazy Loading**: Complex charts are loaded only when needed
- **Data Chunking**: Large datasets are processed in manageable chunks
- **Animation Control**: Chart animations can be disabled for performance-critical scenarios

## Troubleshooting Guide

### Common Issues and Solutions

**Metrics Not Updating**
- Verify Prometheus service availability
- Check metric endpoint accessibility
- Review backend logging for errors

**Slow Dashboard Performance**
- Monitor database query execution times
- Check network latency between frontend and backend
- Validate chart rendering performance
- **Updated**: Check Recharts performance with large datasets
- **Updated**: Monitor memory usage during chart rendering

**Data Inconsistencies**
- Confirm data synchronization between systems
- Verify time zone handling in date calculations
- Check for concurrent modification conflicts

**Authentication Problems**
- Validate CSRF token handling
- Check session management
- Review CORS configuration

**Chart Rendering Issues**
- **New**: Verify Recharts library version compatibility
- **New**: Check browser support for SVG rendering
- **New**: Monitor chart container dimensions
- **New**: Validate data format for Recharts components

**Section sources**
- [test_admin_metrics.py:27-159](file://app/backend/tests/test_admin_metrics.py#L27-L159)

## Conclusion

The Platform Metrics Dashboard represents a sophisticated analytics solution that successfully combines real-time monitoring with comprehensive business intelligence. The recent enhancement with Recharts-based visualization significantly improves the dashboard's analytical capabilities and user experience.

Key strengths include comprehensive Prometheus integration, flexible analytics endpoints, and sophisticated interactive frontend visualizations. The dashboard effectively balances performance requirements with feature richness, making it suitable for both operational monitoring and strategic decision-making.

The new Recharts integration provides:
- **Enhanced Data Visualization**: Sophisticated chart components for better data interpretation
- **Improved User Experience**: Interactive and responsive visualizations with smooth animations
- **Better Performance**: Optimized rendering for large datasets and complex visualizations
- **Modern Design**: Contemporary UI with brand-consistent styling and responsive layouts

Future enhancements could include expanded real-time streaming capabilities, advanced predictive analytics, enhanced customization options for different user roles, and integration of additional chart types for more specialized analytics use cases.