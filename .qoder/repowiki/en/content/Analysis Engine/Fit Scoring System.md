# Fit Scoring System

<cite>
**Referenced Files in This Document**
- [fit_scorer.py](file://app/backend/services/fit_scorer.py)
- [weight_mapper.py](file://app/backend/services/weight_mapper.py)
- [weight_suggester.py](file://app/backend/services/weight_suggester.py)
- [constants.py](file://app/backend/services/constants.py)
- [risk_calculator.py](file://app/backend/services/risk_calculator.py)
- [eligibility_service.py](file://app/backend/services/eligibility_service.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [test_fit_scorer.py](file://app/backend/tests/test_fit_scorer.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [analyze.py](file://app/backend/routes/analyze.py)
- [WeightSuggestionPanel.jsx](file://app/frontend/src/components/WeightSuggestionPanel.jsx)
- [interview_kit.py](file://app/backend/routes/interview_kit.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [InterviewScorecard.jsx](file://app/frontend/src/components/InterviewScorecard.jsx)
- [test_interview_kit.py](file://app/backend/tests/test_interview_kit.py)
- [017_interview_kit_enhancement.py](file://alembic/versions/017_interview_kit_enhancement.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced with new evaluation framework integration for structured interview evaluations
- Updated scoring algorithms to support competency assessments across technical, behavioral, and culture-fit dimensions
- Integrated multi-dimensional evaluation criteria alongside existing fit scoring capabilities
- Added comprehensive interview evaluation and scoring card functionality
- Implemented tenant isolation for evaluation data and overall assessments
- Enhanced hybrid pipeline integration with evaluation framework

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Enhanced Weight Management System](#enhanced-weight-management-system)
5. [Scoring Algorithms](#scoring-algorithms)
6. [Risk Assessment](#risk-assessment)
7. [Eligibility Engine](#eligibility-engine)
8. [Interview Evaluation Framework](#interview-evaluation-framework)
9. [Multi-Dimensional Evaluation System](#multi-dimensional-evaluation-system)
10. [Tenant Customization and Dynamic Weights](#tenant-customization-and-dynamic-weights)
11. [Integration Points](#integration-points)
12. [Testing Framework](#testing-framework)
13. [Performance Considerations](#performance-considerations)
14. [Troubleshooting Guide](#troubleshooting-guide)
15. [Conclusion](#conclusion)

## Introduction

The Fit Scoring System is a comprehensive candidate evaluation framework designed to provide standardized, transparent, and adaptable scoring mechanisms for resume analysis. Built as part of the Resume AI platform by ThetaLogics, this system combines deterministic scoring with machine learning capabilities to deliver consistent and explainable hiring decisions.

The system operates on a hybrid approach, utilizing Python-based deterministic calculations for core scoring alongside LLM-powered narrative generation for qualitative insights. It supports multiple weight schemas, adaptive scoring based on role categories, comprehensive risk assessment, tenant customization capabilities, and now includes a robust interview evaluation framework for structured competency assessments across multiple evaluation dimensions.

## System Architecture

The Fit Scoring System follows a layered architecture with clear separation of concerns and enhanced tenant customization capabilities, now including comprehensive interview evaluation infrastructure:

```mermaid
graph TB
subgraph "Client Layer"
UI[Frontend Interface]
API[REST API Endpoints]
WeightPanel[Weight Suggestion Panel]
CustomWeights[Tenant Custom Weights]
InterviewScorecard[Interview Scorecard]
EvalForm[Structured Evaluation Form]
end
subgraph "Application Layer"
HP[Hybrid Pipeline]
FS[Fit Scorer]
WM[Weight Manager]
ES[Eligibility Service]
RS[Risk Calculator]
WS[Weight Suggester]
IE[Interview Evaluator]
IS[Scorecard Generator]
end
subgraph "Data Layer"
DB[(Database)]
CACHE[(Cache)]
EVAL_TABLES[Interview Evaluation Tables]
end
subgraph "External Services"
LLM[LLM Provider]
OLLAMA[Ollama Service]
end
UI --> API
API --> WeightPanel
API --> CustomWeights
API --> InterviewScorecard
API --> EvalForm
WeightPanel --> WS
CustomWeights --> HP
InterviewScorecard --> IS
EvalForm --> IE
API --> HP
HP --> FS
HP --> ES
FS --> WM
FS --> RS
ES --> DB
WM --> DB
RS --> DB
WS --> WM
IE --> EVAL_TABLES
IS --> EVAL_TABLES
HP --> LLM
LLM --> OLLAMA
FS --> CACHE
ES --> CACHE
```

**Diagram sources**
- [hybrid_pipeline.py:1-200](file://app/backend/services/hybrid_pipeline.py#L1-L200)
- [fit_scorer.py:1-231](file://app/backend/services/fit_scorer.py#L1-L231)
- [weight_mapper.py:1-345](file://app/backend/services/weight_mapper.py#L1-L345)
- [WeightSuggestionPanel.jsx:1-258](file://app/frontend/src/components/WeightSuggestionPanel.jsx#L1-L258)
- [interview_kit.py:1-221](file://app/backend/routes/interview_kit.py#L1-L221)
- [db_models.py:219-257](file://app/backend/models/db_models.py#L219-L257)

## Core Components

### Enhanced Fit Scorer Service

The Fit Scorer Service serves as the central component for computing standardized candidate scores with tenant customization capabilities. It provides three primary scoring mechanisms with enhanced flexibility:

#### Customizable Fit Score Calculation
The main `compute_fit_score` function now supports tenant customization through the `scoring_weights` parameter:

```mermaid
flowchart TD
Start([Input Scores + Custom Weights]) --> Extract["Extract Individual Scores<br/>- Skill Score<br/>- Experience Score<br/>- Architecture Score<br/>- Education Score<br/>- Timeline Score<br/>- Domain Score"]
Extract --> WeightSelection{"Custom Weights Provided?"}
WeightSelection --> |Yes| UseCustom["Use Custom Scoring Weights<br/>- Tenant-specific weights<br/>- Role-based customization<br/>- Dynamic weight application"]
WeightSelection --> |No| UseDefault["Use Default Weights<br/>- DEFAULT_WEIGHTS from constants.py<br/>- Standard universal schema"]
UseCustom --> RiskSignals["Generate Risk Signals<br/>- Employment Gaps<br/>- Skill Gaps<br/>- Domain Mismatch<br/>- Stability Issues<br/>- Overqualification"]
UseDefault --> RiskSignals
RiskSignals --> RiskPenalty["Calculate Risk Penalty<br/>- Sum Severity Penalties<br/>- Apply Risk Weight"]
RiskPenalty --> WeightedSum["Apply Weighted Formula<br/>Σ(Score × Weight)"]
WeightedSum --> Clamp["Clamp to 0-100 Range"]
Clamp --> Decision["Generate Recommendation<br/>- Shortlist (≥72)<br/>- Consider (≥45)<br/>- Reject (<45)"]
Decision --> Output([Final Score & Recommendation])
```

**Diagram sources**
- [fit_scorer.py:12-114](file://app/backend/services/fit_scorer.py#L12-L114)

#### Deterministic Score Engine with Custom Weights
The `compute_deterministic_score` function now supports tenant-specific weight distribution:

- **Custom Weight Distribution**: When weights parameter is provided, allows tenant customization of feature importance
- **Hard Caps**: Maximum score limitations based on eligibility criteria and custom weight allocations
- **Domain Cap**: Maximum 35% when domain match is below 30%, adjusted by custom weight distribution
- **Core Skill Cap**: Maximum 40% when core skill match is below 30%, adjusted by custom weight distribution

#### Decision Explanation Generator
The `explain_decision` function creates structured explanations with:
- Clear decision rationale
- Feature summary with percentages
- Applied caps documentation
- Actionable recommendations

**Section sources**
- [fit_scorer.py:12-231](file://app/backend/services/fit_scorer.py#L12-L231)

## Enhanced Weight Management System

### Schema Compatibility with Tenant Customization

The system supports three weight schemas with automatic conversion and tenant customization:

#### Legacy 4-Weight Schema
- **skills**: 0.40
- **experience**: 0.35  
- **stability**: 0.15
- **education**: 0.10

#### Old Backend 7-Weight Schema
- **skills**: 0.30
- **experience**: 0.20
- **architecture**: 0.15
- **education**: 0.10
- **timeline**: 0.10
- **domain**: 0.10
- **risk**: 0.15

#### New Universal 7-Weight Schema
- **core_competencies**: 0.30
- **experience**: 0.20
- **domain_fit**: 0.20
- **education**: 0.10
- **career_trajectory**: 0.10
- **role_excellence**: 0.10
- **risk**: -0.10

### Intelligent Weight Suggestions with Application

The LLM-based weight suggester now actively applies suggested weights rather than being informational only:

```mermaid
sequenceDiagram
participant Client as "Client"
participant Suggester as "WeightSuggester"
participant LLM as "LLM Model"
participant Mapper as "WeightMapper"
participant Pipeline as "Hybrid Pipeline"
Client->>Suggester : suggest_weights_for_jd(jd_text)
Suggester->>Suggester : Validate JD text
Suggester->>LLM : Analyze job description
LLM-->>Suggester : Role category & suggested weights
Suggester->>Mapper : normalize_weights()
Mapper-->>Suggester : Normalized weights
Suggester-->>Client : Weight suggestions with reasoning
Client->>Pipeline : Apply suggested weights to scoring
Pipeline-->>Client : Final analysis with custom weights
Note over Suggester,LLM : Fallback to default weights if LLM fails
```

**Diagram sources**
- [weight_suggester.py:86-178](file://app/backend/services/weight_suggester.py#L86-L178)
- [weight_mapper.py:36-72](file://app/backend/services/weight_mapper.py#L36-L72)

**Section sources**
- [weight_suggester.py:1-307](file://app/backend/services/weight_suggester.py#L1-L307)
- [weight_mapper.py:1-345](file://app/backend/services/weight_mapper.py#L1-L345)

## Scoring Algorithms

### Multi-Dimensional Scoring Formula with Tenant Customization

The system employs a comprehensive scoring formula that evaluates candidates across seven key dimensions with tenant customization support:

| Dimension | Default Weight | Tenant Customizable | Description | Typical Range |
|-----------|----------------|-------------------|-------------|---------------|
| Core Competencies | 0.30 | ✅ Yes | Technical skill alignment | 0-100 |
| Experience | 0.20 | ✅ Yes | Years of relevant experience | 0-100 |
| Domain Fit | 0.20 | ✅ Yes | Industry/domain expertise | 0-100 |
| Education | 0.10 | ✅ Yes | Educational credentials | 0-100 |
| Career Trajectory | 0.10 | ✅ Yes | Job stability and progression | 0-100 |
| Role Excellence | 0.10 | ✅ Yes | Specialized achievements | 0-100 |
| Risk | -0.10 | ❌ No | Penalty factor | -∞ to 0 |

### Recommendation Thresholds

The system uses standardized thresholds for automated decision-making with tenant customization:

```mermaid
flowchart LR
subgraph "Score Ranges"
A[0-44] --> Reject["Reject"]
B[45-71] --> Consider["Consider"]
C[72-100] --> Shortlist["Shortlist"]
end
subgraph "Risk Levels"
HighRisk["High Risk"] --> Reject
MediumRisk["Medium Risk"] --> Consider
LowRisk["Low Risk"] --> Shortlist
end
```

**Diagram sources**
- [constants.py:9-14](file://app/backend/services/constants.py#L9-L14)

**Section sources**
- [fit_scorer.py:12-114](file://app/backend/services/fit_scorer.py#L12-L114)
- [constants.py:9-14](file://app/backend/services/constants.py#L9-L14)

## Risk Assessment

### Risk Signal Detection

The system automatically identifies potential red flags in candidate profiles:

| Risk Type | Severity | Detection Criteria | Penalty |
|-----------|----------|-------------------|---------|
| Critical Employment Gap | High | 12+ months gap | +20 points |
| Significant Skill Gap | High | Missing ≥50% required skills | +20 points |
| Moderate Skill Gap | Medium | Missing 30-49% required skills | +10 points |
| Domain Mismatch | Medium | Candidate domain ≠ JD domain | +10 points |
| Job Hopping | Medium | ≥3 short stints (<6 months) | +10 points |
| Frequent Job Changes | Low | 2 short stints | +4 points |
| Overqualification | Low | Experience > 2× required | +4 points |

### Risk Penalty Calculation

```mermaid
flowchart TD
Start([Risk Signals]) --> Check{"Signal Severity?"}
Check --> |High| HighRisk["+20 Penalty"]
Check --> |Medium| MedRisk["+10 Penalty"]
Check --> |Low| LowRisk["+4 Penalty"]
HighRisk --> Sum["Sum All Penalties"]
MedRisk --> Sum
LowRisk --> Sum
Sum --> Apply["Apply Risk Weight<br/>× 0.15"]
Apply --> Result([Total Risk Penalty])
```

**Diagram sources**
- [risk_calculator.py:6-15](file://app/backend/services/risk_calculator.py#L6-L15)

**Section sources**
- [risk_calculator.py:1-16](file://app/backend/services/risk_calculator.py#L1-L16)
- [fit_scorer.py:39-70](file://app/backend/services/fit_scorer.py#L39-L70)

## Eligibility Engine

### Deterministic Hard Gates

The eligibility service enforces mandatory criteria before scoring:

```mermaid
flowchart TD
Start([Candidate Evaluation]) --> DomainCheck{"Domain Match?"}
DomainCheck --> |Mismatch & Both Confident| Reject1["Reject: Domain Mismatch"]
DomainCheck --> |Pass| SkillCheck{"Core Skill ≥ 30%?"}
SkillCheck --> |No| Reject2["Reject: Low Core Skills"]
SkillCheck --> |Yes| ExpCheck{"Has Relevant Experience?"}
ExpCheck --> |No| Reject3["Reject: No Relevant Experience"]
ExpCheck --> |Yes| Eligible["Eligible for Scoring"]
Reject1 --> End([Final Decision])
Reject2 --> End
Reject3 --> End
Eligible --> Continue["Proceed to Scoring"]
Continue --> End
```

### Hard Cap Application

Eligibility violations trigger maximum score reductions:
- **Domain Mismatch**: Maximum 35% regardless of other scores
- **Low Core Skills (<30%)**: Maximum 40% regardless of other scores
- **No Relevant Experience**: Maximum 35% regardless of other scores

**Section sources**
- [eligibility_service.py:1-80](file://app/backend/services/eligibility_service.py#L1-L80)
- [fit_scorer.py:158-170](file://app/backend/services/fit_scorer.py#L158-L170)

## Interview Evaluation Framework

### Structured Interview Evaluation System

The system now includes a comprehensive interview evaluation framework that captures structured competency assessments across multiple evaluation dimensions:

#### Evaluation Data Model
The InterviewEvaluation model provides granular tracking of individual question assessments:

```mermaid
classDiagram
class InterviewEvaluation {
+id : Integer
+result_id : Integer
+user_id : Integer
+question_category : String
+question_index : Integer
+rating : String
+notes : Text
+created_at : DateTime
+updated_at : DateTime
}
class OverallAssessment {
+id : Integer
+result_id : Integer
+user_id : Integer
+overall_assessment : Text
+recruiter_recommendation : String
+created_at : DateTime
+updated_at : DateTime
}
InterviewEvaluation --> ScreeningResult : belongs_to
OverallAssessment --> ScreeningResult : belongs_to
```

**Diagram sources**
- [db_models.py:219-257](file://app/backend/models/db_models.py#L219-L257)

#### Evaluation Categories and Ratings
The system supports three primary evaluation categories with standardized rating scales:

| Category | Questions | Purpose | Rating Scale |
|----------|-----------|---------|--------------|
| Technical | Technical competency questions | Assess hard skills and domain expertise | Strong, Adequate, Weak |
| Behavioral | Situational and behavioral questions | Evaluate soft skills and cultural fit | Strong, Adequate, Weak |
| Culture Fit | Organizational alignment questions | Measure cultural and values alignment | Strong, Adequate, Weak |

#### Tenant Isolation and Security
All evaluation data is strictly isolated by tenant boundaries:
- Access control enforced at database level
- Unique constraints prevent cross-tenant data leakage
- Comprehensive validation for category and rating fields
- Real-time tenant verification for all operations

**Section sources**
- [interview_kit.py:1-221](file://app/backend/routes/interview_kit.py#L1-L221)
- [db_models.py:219-257](file://app/backend/models/db_models.py#L219-L257)
- [017_interview_kit_enhancement.py:1-61](file://alembic/versions/017_interview_kit_enhancement.py#L1-L61)

## Multi-Dimensional Evaluation System

### Comprehensive Scorecard Generation

The system generates detailed evaluation scorecards that aggregate interview assessments across multiple dimensions:

#### Dimension Summary Structure
Each evaluation dimension provides comprehensive statistical summaries:

```mermaid
classDiagram
class ScorecardDimension {
+category : String
+total_questions : Integer
+evaluated_count : Integer
+strong_count : Integer
+adequate_count : Integer
+weak_count : Integer
+key_notes : String[]
}
class ScorecardOut {
+candidate_name : String
+role_title : String
+fit_score : Integer
+recommendation : String
+evaluator_email : String
+evaluated_at : DateTime
+technical_summary : ScorecardDimension
+behavioral_summary : ScorecardDimension
+culture_fit_summary : ScorecardDimension
+overall_assessment : String
+recruiter_recommendation : String
+strengths_confirmed : String[]
+concerns_identified : String[]
}
```

**Diagram sources**
- [schemas.py:490-515](file://app/backend/models/schemas.py#L490-L515)

#### Evaluation Aggregation Logic
The scorecard generation process aggregates evaluation data with intelligent filtering:

```mermaid
flowchart TD
Start([Interview Evaluations]) --> Load["Load All Evaluations<br/>for Current User & Result"]
Load --> Count["Count Total Questions<br/>- Technical: N questions<br/>- Behavioral: M questions<br/>- Culture Fit: K questions"]
Count --> Aggregate["Aggregate by Category<br/>- Sum Strong/Adequate/Weak ratings<br/>- Collect Key Notes<br/>- Track Evaluation Progress"]
Aggregate --> Extract["Extract Strengths & Concerns<br/>- Strong ratings → Strengths<br/>- Weak ratings → Concerns"]
Extract --> Overall["Load Overall Assessment<br/>if exists"]
Overall --> Timestamp["Find Latest Evaluation Timestamp"]
Timestamp --> Build["Build ScorecardOut Object<br/>with All Aggregated Data"]
```

**Diagram sources**
- [interview_kit.py:140-221](file://app/backend/routes/interview_kit.py#L140-L221)

#### Frontend Integration and Visualization
The InterviewScorecard component provides comprehensive visualization and export capabilities:

- **Dimension Cards**: Color-coded summaries for each evaluation category
- **Progress Tracking**: Visual indicators for evaluation completion
- **Export Functionality**: PDF generation for sharing with hiring managers
- **Editable Assessments**: Structured overall assessment with recommendation options

**Section sources**
- [InterviewScorecard.jsx:1-231](file://app/frontend/src/components/InterviewScorecard.jsx#L1-L231)
- [interview_kit.py:140-221](file://app/backend/routes/interview_kit.py#L140-L221)
- [schemas.py:490-515](file://app/backend/models/schemas.py#L490-L515)

## Tenant Customization and Dynamic Weights

### Custom Scoring Weights Parameter

The enhanced system now supports tenant-specific weight customization through the `scoring_weights` parameter:

#### API Integration
The `/analyze` endpoint now accepts custom scoring weights:

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "Analyze Endpoint"
participant Pipeline as "Hybrid Pipeline"
participant Scorer as "Fit Scorer"
Client->>API : POST /analyze (scoring_weights JSON)
API->>API : Parse and validate weights
API->>Pipeline : Pass weights to pipeline
Pipeline->>Scorer : compute_fit_score(scores, weights)
Scorer->>Scorer : Apply custom weights
Scorer-->>Pipeline : Customized fit score
Pipeline-->>Client : Analysis results with custom weights
```

**Diagram sources**
- [analyze.py:570-821](file://app/backend/routes/analyze.py#L570-L821)

#### Frontend Integration
The Weight Suggestion Panel enables dynamic weight application:

- **AI-Powered Suggestions**: Role-based weight recommendations
- **Manual Customization**: Direct weight adjustment interface
- **Real-time Preview**: Immediate score impact visualization
- **Fallback Mechanisms**: Graceful handling of AI unavailability

### Interview Evaluation Tenant Isolation

The interview evaluation system maintains strict tenant boundaries:

```mermaid
sequenceDiagram
participant Recruiter as "Recruiter User"
participant API as "Interview Kit API"
participant DB as "Database"
Recruiter->>API : Access Evaluation Data
API->>DB : Verify Tenant Ownership
DB-->>API : Tenant Verification Result
API->>API : Proceed if Authorized
API-->>Recruiter : Evaluation Data
Note over Recruiter,DB : Cross-tenant access prevented
```

**Diagram sources**
- [interview_kit.py:28-36](file://app/backend/routes/interview_kit.py#L28-L36)

**Section sources**
- [analyze.py:470-493](file://app/backend/routes/analyze.py#L470-L493)
- [WeightSuggestionPanel.jsx:1-258](file://app/frontend/src/components/WeightSuggestionPanel.jsx#L1-L258)
- [interview_kit.py:28-36](file://app/backend/routes/interview_kit.py#L28-L36)

## Integration Points

### Hybrid Pipeline Integration

The Fit Scoring System integrates seamlessly with the hybrid analysis pipeline with enhanced weight customization and evaluation framework:

```mermaid
sequenceDiagram
participant Client as "Client Request"
participant Pipeline as "Hybrid Pipeline"
participant Scorer as "Fit Scorer"
participant Eligibility as "Eligibility Service"
participant Risk as "Risk Calculator"
participant WeightManager as "Weight Manager"
participant InterviewEvaluator as "Interview Evaluator"
Client->>Pipeline : Analyze Candidate (with custom weights)
Pipeline->>WeightManager : convert_to_new_schema(weights)
WeightManager-->>Pipeline : Normalized weights
Pipeline->>Eligibility : check_eligibility()
Eligibility-->>Pipeline : EligibilityResult
Pipeline->>Scorer : compute_deterministic_score()
Scorer-->>Pipeline : Deterministic Score
Pipeline->>Scorer : compute_fit_score(custom_weights)
Scorer->>Risk : compute_risk_penalty()
Risk-->>Scorer : Risk Penalty
Scorer-->>Pipeline : Final Fit Score with Custom Weights
Pipeline->>InterviewEvaluator : integrate_evaluation_data()
InterviewEvaluator-->>Pipeline : Evaluation-enhanced results
Pipeline-->>Client : Complete Analysis Results
```

**Diagram sources**
- [hybrid_pipeline.py:39-45](file://app/backend/services/hybrid_pipeline.py#L39-L45)
- [fit_scorer.py:117-118](file://app/backend/services/fit_scorer.py#L117-L118)
- [interview_kit.py:140-221](file://app/backend/routes/interview_kit.py#L140-L221)

### API Schema Integration

The system's output conforms to standardized schemas with tenant customization support:

| Field | Type | Description |
|-------|------|-------------|
| fit_score | Integer (0-100) | Final standardized score with custom weights |
| final_recommendation | String | "Shortlist", "Consider", or "Reject" |
| risk_level | String | "Low", "Medium", or "High" |
| score_breakdown | ScoreBreakdown | Individual dimension scores with custom weights |
| risk_signals | List | Identified risk factors |
| decision_explanation | Dict | Structured reasoning with weight impact |
| custom_weights_used | Dict | Tenant-specific weights applied |
| weight_impact_analysis | Dict | How custom weights affected scoring |
| interview_evaluations | List | Structured competency assessments |
| overall_assessment | String | Hiring manager's final recommendation |

**Section sources**
- [schemas.py:43-131](file://app/backend/models/schemas.py#L43-L131)
- [hybrid_pipeline.py:39-45](file://app/backend/services/hybrid_pipeline.py#L39-L45)
- [schemas.py:490-515](file://app/backend/models/schemas.py#L490-L515)

## Testing Framework

### Comprehensive Test Coverage

The system includes extensive testing for reliability, accuracy, tenant customization, and evaluation framework functionality:

#### Deterministic Score Tests
- Perfect features with eligible status: 100% score
- Zero features: 0% score  
- Ineligible candidates: capped at 35%
- Domain mismatch: capped at 35%
- Low core skills: capped at 40%

#### Custom Weight Application Tests
- Tenant-specific weight validation
- Weight schema conversion compatibility
- Custom weight impact on final scores
- Default weight fallback mechanisms

#### Decision Explanation Tests
- Shortlist candidates without caps: "Strong match" rationale
- Reject candidates: documented cap applications
- Domain mismatch: specific domain comparison details
- Low core skills: percentage-based explanations

#### Fit Score Calculation Tests
- Basic weighted calculation verification
- Risk signals impact on final score
- Score clamping to valid ranges
- Empty risk signals handling

#### Interview Evaluation Tests
- CRUD operations for evaluation records
- Tenant isolation validation
- Category and rating validation
- Scorecard aggregation accuracy
- Overall assessment creation and updates

#### Multi-Dimensional Evaluation Tests
- Dimension summary calculations
- Strengths and concerns extraction
- Key notes filtering and truncation
- Evaluation progress tracking
- Cross-tenant data protection

**Section sources**
- [test_fit_scorer.py:1-246](file://app/backend/tests/test_fit_scorer.py#L1-L246)
- [test_interview_kit.py:1-400](file://app/backend/tests/test_interview_kit.py#L1-L400)

## Performance Considerations

### Optimization Strategies

The system implements several performance optimizations with tenant customization and evaluation framework enhancements:

#### Memory Management
- **Weight Normalization**: Automatic weight scaling prevents overflow
- **Input Sanitization**: Prevents memory leaks from malicious inputs
- **Background Task Management**: Proper cleanup of LLM processing tasks
- **Custom Weight Caching**: Tenant-specific weights cached for reuse
- **Evaluation Data Caching**: Frequently accessed evaluation summaries cached

#### Computational Efficiency
- **Early Termination**: Eligibility checks prevent unnecessary processing
- **Cached Calculations**: Risk penalties computed once per evaluation
- **Parallel Processing**: LLM and Python calculations run concurrently
- **Weight Conversion Optimization**: Efficient schema detection and conversion
- **Database Query Optimization**: Indexed lookups for evaluation data

#### Scalability Features
- **Rate Limiting**: Middleware controls concurrent requests
- **Timeout Management**: Configurable LLM timeouts prevent resource exhaustion
- **Graceful Degradation**: Fallback mechanisms ensure system stability
- **Tenant Isolation**: Custom weights isolated per tenant for security
- **Evaluation Data Partitioning**: Large-scale evaluation data organized efficiently

### Monitoring and Metrics

The system tracks key performance indicators:
- **Analysis Duration**: End-to-end processing time
- **LLM Response Times**: Model inference latency
- **Success Rates**: Percentage of completed analyses
- **Error Rates**: Frequency of processing failures
- **Tenant Weight Usage**: Custom weight adoption rates
- **Weight Conversion Performance**: Schema conversion efficiency
- **Evaluation Processing Time**: Interview evaluation aggregation
- **Scorecard Generation Time**: Multi-dimensional evaluation summarization

## Troubleshooting Guide

### Common Issues and Solutions

#### Low Scores Despite Strong Qualifications
**Symptoms**: High individual scores but low final fit score
**Causes**: 
- Risk penalty from employment gaps
- Domain mismatch penalties
- Hard caps from eligibility violations
- Custom weight misalignment with tenant needs

**Solutions**:
- Review risk signals in score breakdown
- Adjust weight schema for role requirements
- Verify eligibility criteria alignment
- Customize weights to match organizational priorities

#### Inconsistent Weight Behavior
**Symptoms**: Unexpected score variations
**Causes**:
- Weight schema conversion errors
- Missing weight normalization
- Incorrect risk penalty application
- Tenant weight conflicts

**Solutions**:
- Validate weight schema detection
- Check weight normalization process
- Review risk signal severity assignments
- Verify tenant weight application order

#### Interview Evaluation Issues
**Symptoms**: Evaluation data not persisting or displaying incorrectly
**Causes**:
- Tenant isolation violations
- Invalid category or rating values
- Database constraint violations
- Missing evaluation data in analysis results

**Solutions**:
- Verify tenant ownership for evaluation operations
- Check evaluation category validation rules
- Review database constraint configurations
- Ensure interview questions included in analysis data

#### LLM Integration Problems
**Symptoms**: Timeout errors or empty responses
**Causes**:
- Ollama service connectivity issues
- Model loading problems
- Resource exhaustion
- Tenant-specific weight processing delays

**Solutions**:
- Verify Ollama service availability
- Check model pull status
- Monitor system resource usage
- Implement weight suggestion caching

### Debugging Tools

#### Logging Configuration
The system provides comprehensive logging:
- **Request Correlation**: Unique identifiers for traceability
- **Performance Metrics**: Timing and resource usage tracking
- **Error Details**: Structured error reporting with context
- **Tenant Weight Tracking**: Custom weight application logs
- **Evaluation Data Logs**: Interview evaluation operation tracking

#### Validation Points
Key validation checkpoints:
- Input parameter validation
- Weight schema compatibility
- Risk signal calculation accuracy
- Final score range verification
- Tenant weight application verification
- Evaluation data integrity checks
- Cross-tenant access prevention

**Section sources**
- [main.py:48-56](file://app/backend/main.py#L48-L56)
- [hybrid_pipeline.py:84-101](file://app/backend/services/hybrid_pipeline.py#L84-L101)
- [interview_kit.py:28-36](file://app/backend/routes/interview_kit.py#L28-L36)

## Conclusion

The Fit Scoring System represents a sophisticated approach to automated candidate evaluation, combining deterministic scoring principles with machine learning capabilities and tenant customization. Its modular architecture ensures maintainability while providing powerful customization options through the enhanced weight management system and comprehensive interview evaluation framework.

Key strengths of the system include:
- **Transparency**: Clear scoring formulas and decision explanations
- **Adaptability**: Support for multiple weight schemas and role categories with tenant customization
- **Robustness**: Comprehensive risk assessment and eligibility enforcement
- **Comprehensive Evaluation**: Multi-dimensional interview assessment across technical, behavioral, and culture-fit domains
- **Tenant-Centric Design**: Strict isolation and security for evaluation data
- **Performance**: Optimized processing with fallback mechanisms and evaluation data caching
- **Extensibility**: Modular design supporting future enhancements and tenant-specific features
- **Structured Assessments**: Professional-grade interview evaluation and scoring card generation

The system successfully balances automation with human oversight, providing recruiters with reliable, consistent, and explainable candidate evaluations that support informed hiring decisions while accommodating diverse organizational scoring preferences, requirements, and structured interview assessment needs.

**Updated** Enhanced with comprehensive interview evaluation framework integration, multi-dimensional competency assessment capabilities, structured evaluation data management with tenant isolation, and advanced scorecard generation for hiring manager review. The system now supports detailed technical, behavioral, and culture-fit evaluations alongside traditional fit scoring, providing a complete evaluation solution for modern hiring processes.