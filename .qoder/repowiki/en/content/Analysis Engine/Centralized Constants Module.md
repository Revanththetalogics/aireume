# Centralized Constants Module

<cite>
**Referenced Files in This Document**
- [constants.py](file://app/backend/services/constants.py)
- [weight_mapper.py](file://app/backend/services/weight_mapper.py)
- [weight_suggester.py](file://app/backend/services/weight_suggester.py)
- [fit_scorer.py](file://app/backend/services/fit_scorer.py)
- [agent_pipeline.py](file://app/backend/services/agent_pipeline.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [risk_calculator.py](file://app/backend/services/risk_calculator.py)
- [domain_service.py](file://app/backend/services/domain_service.py)
- [skill_matcher.py](file://app/backend/services/skill_matcher.py)
- [main.py](file://app/backend/main.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced weight schema definitions with new universal weights system
- Improved LEGACY_WEIGHTS and OLD_BACKEND_WEIGHTS constants with comprehensive coverage
- Added NEW_DEFAULT_WEIGHTS for the new universal schema with core_competencies, domain_fit, career_trajectory, and role_excellence factors
- Comprehensive weight schema management support with intelligent conversion capabilities
- Updated weight mapping and normalization logic for backward compatibility

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
The Centralized Constants Module serves as the single source of truth for all scoring constants, thresholds, domain configurations, and weight schemas within the Resume AI platform. This module ensures consistency across the entire system by providing standardized values for recommendation thresholds, seniority ranges, degree scoring, domain keywords, risk penalties, and various weight schemas used throughout the intelligent screening pipeline.

The module has been enhanced with a comprehensive weight schema management system that supports both legacy and modern weight schemas while maintaining backward compatibility and enabling seamless transitions between different scoring methodologies. It now provides intelligent conversion between different weight schemas and supports the new universal weight system with enhanced domain coverage.

## Project Structure
The centralized constants module is organized within the backend services directory and is imported by multiple service components throughout the application. The module follows a structured approach with clearly defined categories for different types of constants, including the new comprehensive weight schema definitions.

```mermaid
graph TB
subgraph "Enhanced Constants Module Structure"
A[constants.py] --> B[Recommendation Thresholds]
A --> C[Seniority Ranges]
A --> D[Default Scoring Weights]
A --> E[Domain Keywords]
A --> F[Degree Scores]
A --> G[Field Relevance]
A --> H[Risk Severity Penalties]
A --> I[Enhanced Weight Schema Definitions]
end
subgraph "Service Components"
J[agent_pipeline.py]
K[hybrid_pipeline.py]
L[fit_scorer.py]
M[risk_calculator.py]
N[domain_service.py]
O[weight_mapper.py]
P[skill_matcher.py]
Q[weight_suggester.py]
end
B --> J
B --> K
B --> L
C --> J
C --> K
D --> J
D --> K
E --> N
E --> P
F --> K
G --> K
H --> M
I --> O
I --> Q
```

**Diagram sources**
- [constants.py:1-158](file://app/backend/services/constants.py#L1-L158)
- [weight_mapper.py:17-21](file://app/backend/services/weight_mapper.py#L17-L21)
- [weight_suggester.py:17](file://app/backend/services/weight_suggester.py#L17)

**Section sources**
- [constants.py:1-158](file://app/backend/services/constants.py#L1-L158)

## Core Components

### Recommendation Thresholds
The recommendation thresholds define the scoring boundaries for candidate evaluation across three categories: shortlist, consider, and reject. These thresholds are used consistently throughout the scoring pipeline to determine candidate recommendations based on their calculated fit scores.

**Section sources**
- [constants.py:10-14](file://app/backend/services/constants.py#L10-L14)
- [fit_scorer.py:88-96](file://app/backend/services/fit_scorer.py#L88-L96)

### Seniority Ranges
Seniority ranges establish standardized experience level classifications with inclusive minimum years and exclusive maximum years for each position level. This structure enables consistent experience evaluation across different candidate profiles and job requirements.

**Section sources**
- [constants.py:19-29](file://app/backend/services/constants.py#L19-L29)

### Default Scoring Weights
The default scoring weights represent the standard allocation of importance across different evaluation criteria. These weights are applied when custom weights are not provided, ensuring consistent scoring methodology across the platform.

**Section sources**
- [constants.py:34-42](file://app/backend/services/constants.py#L34-L42)

### Domain Keywords
Domain keywords provide comprehensive keyword mappings for identifying professional domains across nine distinct technology areas. This includes backend development, frontend development, data science, machine learning, DevOps, embedded systems, mobile development, and management roles.

**Section sources**
- [constants.py:46-78](file://app/backend/services/constants.py#L46-L78)

### Degree Scores
The degree scoring system assigns numerical values to various educational qualifications, ranging from PhD-level degrees (100 points) to certificate courses (30 points). This standardized scoring facilitates automated evaluation of educational backgrounds.

**Section sources**
- [constants.py:82-92](file://app/backend/services/constants.py#L82-L92)

### Field Relevance
Field relevance mappings connect professional domains to academic disciplines, enabling assessment of educational alignment with target positions. This helps identify candidates whose educational background aligns with the required technical domain.

**Section sources**
- [constants.py:96-117](file://app/backend/services/constants.py#L96-L117)

### Risk Severity Penalties
Risk severity penalties define the impact levels for different types of risk signals detected during candidate evaluation. These penalties are applied to adjust final scores based on potential risks identified in candidate profiles.

**Section sources**
- [constants.py:121-125](file://app/backend/services/constants.py#L121-L125)

### Enhanced Weight Schema Definitions
The module now defines four distinct weight schemas to support different scoring approaches and maintain comprehensive backward compatibility:

1. **Legacy Weights**: Four-weight schema (skills, experience, stability, education) for backward compatibility
2. **New Default Weights**: Seven-weight universal schema with enhanced domain coverage including core_competencies, domain_fit, career_trajectory, and role_excellence factors
3. **Old Backend Weights**: Seven-weight tech-centric schema for specialized backend roles
4. **Weight Mapper Integration**: Comprehensive conversion system supporting automatic schema detection and transformation

**Updated** Enhanced with NEW_DEFAULT_WEIGHTS for universal schema and improved LEGACY_WEIGHTS and OLD_BACKEND_WEIGHTS constants

**Section sources**
- [constants.py:128-157](file://app/backend/services/constants.py#L128-L157)
- [weight_mapper.py:17-21](file://app/backend/services/weight_mapper.py#L17-L21)

## Architecture Overview
The centralized constants module operates as a foundational layer that supports the entire intelligent screening architecture. Multiple service components depend on these standardized values to ensure consistent behavior across the platform, with enhanced weight schema management capabilities.

```mermaid
graph TB
subgraph "Enhanced Centralized Constants Layer"
A[constants.py]
B[NEW_DEFAULT_WEIGHTS]
C[LEGACY_WEIGHTS]
D[OLD_BACKEND_WEIGHTS]
end
subgraph "Advanced Scoring Services"
E[fit_scorer.py]
F[risk_calculator.py]
G[weight_mapper.py]
H[weight_suggester.py]
end
subgraph "Pipeline Components"
I[agent_pipeline.py]
J[hybrid_pipeline.py]
end
subgraph "Domain Services"
K[domain_service.py]
L[skill_matcher.py]
end
A --> E
A --> F
A --> G
A --> H
A --> I
A --> J
A --> K
A --> L
B --> G
C --> G
D --> G
E --> M[Final Recommendations]
F --> E
G --> I
G --> J
H --> G
K --> J
L --> J
```

**Diagram sources**
- [constants.py:128-157](file://app/backend/services/constants.py#L128-L157)
- [weight_mapper.py:197-230](file://app/backend/services/weight_mapper.py#L197-L230)
- [weight_suggester.py:17](file://app/backend/services/weight_suggester.py#L17)

## Detailed Component Analysis

### Enhanced Recommendation Thresholds Implementation
The recommendation thresholds serve as the cornerstone for automated candidate evaluation. The system uses a tiered approach where scores above 72 qualify for shortlisting, scores between 45-71 warrant consideration, and scores below 45 result in rejection.

```mermaid
flowchart TD
A[Calculate Candidate Score] --> B{Score ≥ 72?}
B --> |Yes| C[Shortlist Recommendation]
B --> |No| D{Score ≥ 45?}
D --> |Yes| E[Consider Recommendation]
D --> |No| F[Reject Recommendation]
G[Risk Assessment] --> H{High Risk Signals?}
H --> |Yes| I[Upgrade Risk Level]
H --> |No| J[Maintain Current Risk Level]
E --> K[Risk Level Medium/Low]
C --> L[Risk Level Low]
F --> M[Risk Level High/Medium]
```

**Diagram sources**
- [constants.py:10-14](file://app/backend/services/constants.py#L10-L14)
- [fit_scorer.py:88-96](file://app/backend/services/fit_scorer.py#L88-L96)

**Section sources**
- [constants.py:10-14](file://app/backend/services/constants.py#L10-L14)
- [fit_scorer.py:88-96](file://app/backend/services/fit_scorer.py#L88-L96)

### Advanced Domain Keyword Processing
The domain keyword system enables sophisticated domain detection through keyword matching algorithms. Each domain category contains 15-25 relevant keywords that help identify technical specialties within job descriptions and candidate profiles.

```mermaid
sequenceDiagram
participant JD as Job Description Text
participant DS as Domain Service
participant CK as Keyword Processor
participant KW as Keyword Database
JD->>DS : Raw job description text
DS->>CK : Process with domain keywords
CK->>KW : Search for keyword matches
KW-->>CK : Match counts per domain
CK-->>DS : Domain scores and confidence
DS-->>JD : Best matching domain with confidence
```

**Diagram sources**
- [domain_service.py:9-41](file://app/backend/services/domain_service.py#L9-L41)
- [constants.py:46-78](file://app/backend/services/constants.py#L46-L78)

**Section sources**
- [domain_service.py:9-41](file://app/backend/services/domain_service.py#L9-L41)
- [constants.py:46-78](file://app/backend/services/constants.py#L46-L78)

### Comprehensive Weight Schema Management
The enhanced weight mapper provides intelligent conversion between different scoring schemas, ensuring backward compatibility while supporting modern scoring methodologies. The system now supports four distinct weight schemas with comprehensive coverage.

```mermaid
flowchart LR
A[Legacy Schema<br/>4 weights: skills, experience, stability, education] --> B[Weight Mapper]
C[Old Backend Schema<br/>7 weights: skills, experience, architecture, education, timeline, domain, risk] --> B
D[New Default Schema<br/>7 weights: core_competencies, experience, domain_fit, education, career_trajectory, role_excellence, risk] --> B
B --> E[Universal Schema<br/>core_competencies, domain_fit, career_trajectory, role_excellence]
E --> F[Normalized Weights<br/>Sum = 1.0]
F --> G[Apply to Scoring<br/>Calculation]
H[Schema Detection] --> B
B --> I[Automatic Migration]
J[Weight Suggestion] --> B
```

**Updated** Enhanced with NEW_DEFAULT_WEIGHTS and improved conversion logic

**Diagram sources**
- [weight_mapper.py:75-161](file://app/backend/services/weight_mapper.py#L75-L161)
- [constants.py:128-157](file://app/backend/services/constants.py#L128-L157)
- [weight_suggester.py:180-247](file://app/backend/services/weight_suggester.py#L180-L247)

**Section sources**
- [weight_mapper.py:75-161](file://app/backend/services/weight_mapper.py#L75-L161)
- [constants.py:128-157](file://app/backend/services/constants.py#L128-L157)
- [weight_suggester.py:180-247](file://app/backend/services/weight_suggester.py#L180-L247)

### Enhanced Risk Penalty Calculation
The risk penalty system applies standardized penalties based on detected risk signals, with severity levels determining the impact magnitude. The new universal schema includes risk as a negative weight (-0.10) to penalize red flags and inconsistencies.

**Section sources**
- [risk_calculator.py:6-15](file://app/backend/services/risk_calculator.py#L6-L15)
- [constants.py:121-125](file://app/backend/services/constants.py#L121-L125)

## Dependency Analysis
The centralized constants module creates dependencies across multiple service components, establishing a unidirectional dependency flow from the constants module to consuming services. The enhanced weight schema system now requires integration with the weight mapper and weight suggester services.

```mermaid
graph TB
subgraph "Enhanced Constants Module"
A[constants.py]
B[NEW_DEFAULT_WEIGHTS]
C[LEGACY_WEIGHTS]
D[OLD_BACKEND_WEIGHTS]
end
subgraph "Direct Dependencies"
E[fit_scorer.py]
F[risk_calculator.py]
G[domain_service.py]
H[weight_mapper.py]
I[agent_pipeline.py]
J[hybrid_pipeline.py]
K[skill_matcher.py]
L[weight_suggester.py]
end
subgraph "Indirect Dependencies"
M[guardrail_service.py]
N[eligibility_service.py]
O[consensus_analyzer.py]
P[test_weight_system.py]
end
A --> E
A --> F
A --> G
A --> H
A --> I
A --> J
A --> K
A --> L
B --> H
C --> H
D --> H
E --> M
I --> M
J --> M
K --> N
E --> O
J --> O
H --> P
L --> P
```

**Updated** Added weight_suggester.py and enhanced weight mapper integration

**Diagram sources**
- [constants.py:1-158](file://app/backend/services/constants.py#L1-L158)
- [weight_mapper.py:17-21](file://app/backend/services/weight_mapper.py#L17-L21)
- [weight_suggester.py:17](file://app/backend/services/weight_suggester.py#L17)

**Section sources**
- [constants.py:1-158](file://app/backend/services/constants.py#L1-L158)

## Performance Considerations
The centralized constants module contributes to system performance through several mechanisms:

### Memory Efficiency
- Single module loading reduces memory footprint compared to multiple local constant definitions
- Shared references across all service instances minimize redundant memory usage
- Enhanced weight schema caching reduces repeated conversion calculations

### Computational Optimization
- Pre-computed keyword lists enable efficient string matching operations
- Standardized thresholds eliminate repeated calculations during scoring
- Intelligent schema detection minimizes unnecessary conversions

### Scalability Benefits
- Centralized updates eliminate the need for distributed constant synchronization
- Consistent behavior across microservices reduces operational complexity
- Comprehensive weight schema support enables flexible scaling

## Troubleshooting Guide

### Common Issues and Solutions

**Issue: Inconsistent Scoring Results**
- Verify that all services import constants from the centralized module
- Check for local constant overrides that may conflict with centralized values
- Ensure weight schema conversion is properly applied when migrating between schemas

**Issue: Domain Detection Failures**
- Review domain keyword completeness for specific technical domains
- Validate keyword case sensitivity and special character handling

**Issue: Weight Schema Conflicts**
- Use the enhanced weight mapper for automatic schema conversion
- Verify weight normalization when implementing custom scoring
- Check for proper integration with NEW_DEFAULT_WEIGHTS

**Issue: New Schema Migration Problems**
- Ensure LEGACY_WEIGHTS and OLD_BACKEND_WEIGHTS are properly configured
- Verify convert_to_new_schema function is being called correctly
- Check that weight labels are properly adapted for role categories

**Updated** Added troubleshooting guidance for new weight schema system

**Section sources**
- [weight_mapper.py:197-230](file://app/backend/services/weight_mapper.py#L197-L230)
- [weight_suggester.py:180-247](file://app/backend/services/weight_suggester.py#L180-L247)

### Debugging Strategies
- Monitor service imports to ensure proper constant module references
- Validate constant values against expected ranges and distributions
- Test threshold boundaries to confirm correct recommendation categorization
- Verify weight schema detection and conversion logic
- Check weight normalization and summation constraints

## Conclusion
The Centralized Constants Module represents a critical architectural component that ensures consistency, reliability, and maintainability across the Resume AI platform's intelligent screening capabilities. The enhanced weight schema system provides comprehensive backward compatibility while supporting modern scoring methodologies through intelligent conversion and normalization capabilities.

By providing a single source of truth for all scoring parameters, thresholds, and configuration values, the module enables seamless operation of the automated candidate evaluation system while supporting future enhancements and schema migrations. The addition of NEW_DEFAULT_WEIGHTS for the universal schema, along with improved LEGACY_WEIGHTS and OLD_BACKEND_WEIGHTS constants, ensures comprehensive coverage of different weight schemas and their intelligent conversion pathways.

The modular design facilitates easy maintenance and updates, while the comprehensive coverage of different weight schemas ensures backward compatibility and smooth transitions to modern scoring methodologies. This foundation supports the platform's goal of delivering accurate, consistent, and scalable automated resume screening capabilities with enhanced flexibility and adaptability.