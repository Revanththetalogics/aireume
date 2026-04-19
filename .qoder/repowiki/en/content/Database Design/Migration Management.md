# Migration Management

<cite>
**Referenced Files in This Document**
- [alembic/versions/001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)
- [alembic/versions/002_parser_snapshot_json.py](file://alembic/versions/002_parser_snapshot_json.py)
- [alembic/versions/003_subscription_system.py](file://alembic/versions/003_subscription_system.py)
- [alembic/versions/004_narrative_json.py](file://alembic/versions/004_narrative_json.py)
- [alembic/versions/005_revoked_tokens.py](file://alembic/versions/005_revoked_tokens.py)
- [alembic/versions/006_indexes_and_jdcache_created_at.py](file://alembic/versions/006_indexes_and_jdcache_created_at.py)
- [alembic/versions/007_narrative_status.py](file://alembic/versions/007_narrative_status.py)
- [alembic/versions/008_analysis_queue_system.py](file://alembic/versions/008_analysis_queue_system.py)
- [alembic/versions/009_intelligent_scoring_weights.py](file://alembic/versions/009_intelligent_scoring_weights.py)
- [alembic/versions/010_add_jd_text_to_screening_result.py](file://alembic/versions/010_add_jd_text_to_screening_result.py)
- [alembic/versions/011_narrative_tracking_enhancement.py](file://alembic/versions/011_narrative_tracking_enhancement.py)
- [alembic/env.py](file://alembic/env.py)
- [alembic.ini](file://alembic.ini)
- [app/backend/db/database.py](file://app/backend/db/database.py)
- [app/backend/models/db_models.py](file://app/backend/models/db_models.py)
- [app/backend/routes/analyze.py](file://app/backend/routes/analyze.py)
- [app/backend/services/hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [.github/workflows/ci.yml](file://.github/workflows/ci.yml)
- [.github/workflows/cd.yml](file://.github/workflows/cd.yml)
- [docker-compose.yml](file://docker-compose.yml)
- [docker-compose.prod.yml](file://docker-compose.prod.yml)
</cite>

## Update Summary
**Changes Made**
- Updated migration chain to include versions 008 through 011 with comprehensive enhancements
- Added intelligent scoring weights system with role category detection and version management
- Enhanced ScreeningResult table with role_category, weight_reasoning, and suggested_weights_json columns
- Introduced narrative tracking enhancements with narrative_generated_at timestamp
- Added JD text storage and advanced indexing for improved performance
- Updated migration workflow to support the expanded feature set
- Enhanced service layer integration with intelligent scoring and background processing

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
This document explains the database migration system for Resume AI by ThetaLogics, powered by Alembic. It covers the complete migration version history from 001 through 011, detailing schema evolution and feature additions. The system now includes comprehensive intelligent scoring with role category detection, advanced narrative tracking with timestamps, JD text storage for RAG learning, enhanced performance indexing, and improved version management for screening results. It also documents the migration workflow (revision creation, execution, and rollback), database initialization, seed data insertion, and production deployment strategies. Best practices, testing procedures, rollback scenarios, and troubleshooting guidance are included to ensure safe and reliable migrations in development and production environments.

## Project Structure
The migration system is organized under the alembic directory with dedicated revision files for each version. The Alembic environment integrates with the application's SQLAlchemy models and database configuration. The current migration chain consists of eleven versions, each building upon previous changes. CI/CD pipelines automate testing and deployment, while Docker Compose configurations define local and production runtime environments.

```mermaid
graph TB
A["Alembic Config<br/>alembic.ini"] --> B["Environment Script<br/>alembic/env.py"]
B --> C["Models Registry<br/>app/backend/models/db_models.py"]
B --> D["Database URL Provider<br/>app/backend/db/database.py"]
E["Version 001<br/>001_enrich_candidates_add_caches.py"] --> F["Version 002<br/>002_parser_snapshot_json.py"]
F --> G["Version 003<br/>003_subscription_system.py"]
G --> H["Version 004<br/>004_narrative_json.py"]
H --> I["Version 005<br/>005_revoked_tokens.py"]
I --> J["Version 006<br/>006_indexes_and_jdcache_created_at.py"]
J --> K["Version 007<br/>007_narrative_status.py"]
K --> L["Version 008<br/>008_analysis_queue_system.py"]
L --> M["Version 009<br/>009_intelligent_scoring_weights.py"]
M --> N["Version 010<br/>010_add_jd_text_to_screening_result.py"]
N --> O["Version 011<br/>011_narrative_tracking_enhancement.py"]
P["CI Workflow<br/>.github/workflows/ci.yml"] --> Q["CD Workflow<br/>.github/workflows/cd.yml"]
R["Local Dev Compose<br/>docker-compose.yml"] --> S["Production Compose<br/>docker-compose.prod.yml"]
```

**Diagram sources**
- [alembic.ini:1-148](file://alembic.ini#L1-L148)
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [app/backend/models/db_models.py:1-269](file://app/backend/models/db_models.py#L1-L269)
- [app/backend/db/database.py:1-50](file://app/backend/db/database.py#L1-L50)
- [alembic/versions/001_enrich_candidates_add_caches.py:1-129](file://alembic/versions/001_enrich_candidates_add_caches.py#L1-L129)
- [alembic/versions/002_parser_snapshot_json.py:1-34](file://alembic/versions/002_parser_snapshot_json.py#L1-L34)
- [alembic/versions/003_subscription_system.py:1-290](file://alembic/versions/003_subscription_system.py#L1-L290)
- [alembic/versions/004_narrative_json.py:1-37](file://alembic/versions/004_narrative_json.py#L1-L37)
- [alembic/versions/005_revoked_tokens.py:1-67](file://alembic/versions/005_revoked_tokens.py#L1-L67)
- [alembic/versions/006_indexes_and_jdcache_created_at.py:1-73](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L1-L73)
- [alembic/versions/007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)
- [alembic/versions/009_intelligent_scoring_weights.py:1-93](file://alembic/versions/009_intelligent_scoring_weights.py#L1-L93)
- [alembic/versions/010_add_jd_text_to_screening_result.py:1-69](file://alembic/versions/010_add_jd_text_to_screening_result.py#L1-L69)
- [alembic/versions/011_narrative_tracking_enhancement.py:1-57](file://alembic/versions/011_narrative_tracking_enhancement.py#L1-L57)
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)
- [docker-compose.yml:1-102](file://docker-compose.yml#L1-L102)
- [docker-compose.prod.yml:1-236](file://docker-compose.prod.yml#L1-L236)

**Section sources**
- [alembic.ini:1-148](file://alembic.ini#L1-L148)
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [app/backend/db/database.py:1-50](file://app/backend/db/database.py#L1-L50)
- [app/backend/models/db_models.py:1-269](file://app/backend/models/db_models.py#L1-L269)
- [alembic/versions/001_enrich_candidates_add_caches.py:1-129](file://alembic/versions/001_enrich_candidates_add_caches.py#L1-L129)
- [alembic/versions/002_parser_snapshot_json.py:1-34](file://alembic/versions/002_parser_snapshot_json.py#L1-L34)
- [alembic/versions/003_subscription_system.py:1-290](file://alembic/versions/003_subscription_system.py#L1-L290)
- [alembic/versions/004_narrative_json.py:1-37](file://alembic/versions/004_narrative_json.py#L1-L37)
- [alembic/versions/005_revoked_tokens.py:1-67](file://alembic/versions/005_revoked_tokens.py#L1-L67)
- [alembic/versions/006_indexes_and_jdcache_created_at.py:1-73](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L1-L73)
- [alembic/versions/007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)
- [alembic/versions/009_intelligent_scoring_weights.py:1-93](file://alembic/versions/009_intelligent_scoring_weights.py#L1-L93)
- [alembic/versions/010_add_jd_text_to_screening_result.py:1-69](file://alembic/versions/010_add_jd_text_to_screening_result.py#L1-L69)
- [alembic/versions/011_narrative_tracking_enhancement.py:1-57](file://alembic/versions/011_narrative_tracking_enhancement.py#L1-L57)
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)
- [docker-compose.yml:1-102](file://docker-compose.yml#L1-L102)
- [docker-compose.prod.yml:1-236](file://docker-compose.prod.yml#L1-L236)

## Core Components
- Alembic configuration and environment:
  - alembic.ini controls script locations, logging, and database URL.
  - alembic/env.py wires Alembic to the application's Base metadata and DATABASE_URL, and sets up offline/online migration modes.
- SQLAlchemy models and database:
  - app/backend/db/database.py defines DATABASE_URL normalization and engine creation.
  - app/backend/models/db_models.py declares all database tables used by migrations, including the enhanced ScreeningResult model with intelligent scoring capabilities.
- Migration versions:
  - 001: Enrich candidates and add caches.
  - 002: Add parser snapshot JSON to candidates.
  - 003: Subscription system with usage tracking and seeding.
  - 004: Add narrative JSON column to screening results for async LLM narratives.
  - 005: Add revoked tokens table for JWT token revocation support.
  - 006: Add performance indexes and created_at timestamps.
  - 007: Add narrative_status and narrative_error columns for robust status tracking.
  - 008: Add analysis queue system for background processing.
  - 009: Intelligent scoring weights system with role category detection and version management.
  - 010: Add JD text storage and advanced indexing for RAG learning.
  - 011: Narrative tracking enhancements with generated timestamps and backfill logic.

**Section sources**
- [alembic.ini:1-148](file://alembic.ini#L1-L148)
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [app/backend/db/database.py:1-50](file://app/backend/db/database.py#L1-L50)
- [app/backend/models/db_models.py:1-269](file://app/backend/models/db_models.py#L1-L269)
- [alembic/versions/001_enrich_candidates_add_caches.py:1-129](file://alembic/versions/001_enrich_candidates_add_caches.py#L1-L129)
- [alembic/versions/002_parser_snapshot_json.py:1-34](file://alembic/versions/002_parser_snapshot_json.py#L1-L34)
- [alembic/versions/003_subscription_system.py:1-290](file://alembic/versions/003_subscription_system.py#L1-L290)
- [alembic/versions/004_narrative_json.py:1-37](file://alembic/versions/004_narrative_json.py#L1-L37)
- [alembic/versions/005_revoked_tokens.py:1-67](file://alembic/versions/005_revoked_tokens.py#L1-L67)
- [alembic/versions/006_indexes_and_jdcache_created_at.py:1-73](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L1-L73)
- [alembic/versions/007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)
- [alembic/versions/009_intelligent_scoring_weights.py:1-93](file://alembic/versions/009_intelligent_scoring_weights.py#L1-L93)
- [alembic/versions/010_add_jd_text_to_screening_result.py:1-69](file://alembic/versions/010_add_jd_text_to_screening_result.py#L1-L69)
- [alembic/versions/011_narrative_tracking_enhancement.py:1-57](file://alembic/versions/011_narrative_tracking_enhancement.py#L1-L57)

## Architecture Overview
The migration system integrates Alembic with the application's SQLAlchemy models and database configuration. Migrations are executed against the configured DATABASE_URL, and the environment script ensures Alembic targets the correct metadata and connection. The system now supports JWT token revocation, enhanced performance monitoring through strategic indexing, comprehensive status tracking for LLM narrative generation, intelligent scoring with role category detection, and advanced background processing capabilities.

```mermaid
sequenceDiagram
participant CLI as "Alembic CLI"
participant Env as "alembic/env.py"
participant DB as "DATABASE_URL"
participant Meta as "SQLAlchemy Base.metadata"
participant Models as "db_models.py"
participant Versions as "001..011"
CLI->>Env : "alembic upgrade/downgrade"
Env->>DB : "resolve connection"
Env->>Meta : "configure target_metadata"
Env->>Models : "register models"
Env->>Versions : "execute upgrade()/downgrade()"
Versions-->>CLI : "migration status"
```

**Diagram sources**
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [app/backend/db/database.py:1-50](file://app/backend/db/database.py#L1-L50)
- [app/backend/models/db_models.py:1-269](file://app/backend/models/db_models.py#L1-L269)
- [alembic/versions/001_enrich_candidates_add_caches.py:1-129](file://alembic/versions/001_enrich_candidates_add_caches.py#L1-L129)
- [alembic/versions/002_parser_snapshot_json.py:1-34](file://alembic/versions/002_parser_snapshot_json.py#L1-L34)
- [alembic/versions/003_subscription_system.py:1-290](file://alembic/versions/003_subscription_system.py#L1-L290)
- [alembic/versions/004_narrative_json.py:1-37](file://alembic/versions/004_narrative_json.py#L1-L37)
- [alembic/versions/005_revoked_tokens.py:1-67](file://alembic/versions/005_revoked_tokens.py#L1-L67)
- [alembic/versions/006_indexes_and_jdcache_created_at.py:1-73](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L1-L73)
- [alembic/versions/007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)
- [alembic/versions/009_intelligent_scoring_weights.py:1-93](file://alembic/versions/009_intelligent_scoring_weights.py#L1-L93)
- [alembic/versions/010_add_jd_text_to_screening_result.py:1-69](file://alembic/versions/010_add_jd_text_to_screening_result.py#L1-L69)
- [alembic/versions/011_narrative_tracking_enhancement.py:1-57](file://alembic/versions/011_narrative_tracking_enhancement.py#L1-L57)

## Detailed Component Analysis

### Version 001: Enrich candidates and add caches
- Purpose: Adds enriched candidate profile columns and introduces caching tables for job descriptions and skills.
- Key changes:
  - Extends candidates with profile enrichment fields and adds an index on resume hash.
  - Creates jd_cache and skills tables with indexes.
- Idempotency: Skips operations if tables/columns already exist; safe for legacy setups.
- Downgrade: Drops tables and columns in reverse order.

```mermaid
flowchart TD
Start(["Upgrade"]) --> Inspect["Inspect current schema"]
Inspect --> CandCols{"Candidates columns exist?"}
CandCols --> |No| AddCandCols["Add enrichment columns"]
CandCols --> |Yes| SkipCand["Skip column additions"]
AddCandCols --> IndexCand["Create index on resume hash"]
SkipCand --> IndexCand
IndexCand --> JDCache{"jd_cache exists?"}
JDCache --> |No| CreateJDCache["Create jd_cache table"]
JDCache --> |Yes| SkipJDCache["Skip table creation"]
CreateJDCache --> Skills{"skills exists?"}
SkipJDCache --> Skills
Skills --> |No| CreateSkills["Create skills table + indexes"]
Skills --> |Yes| EnsureIdx["Ensure indexes exist"]
CreateSkills --> End(["Done"])
EnsureIdx --> End
```

**Diagram sources**
- [alembic/versions/001_enrich_candidates_add_caches.py:42-111](file://alembic/versions/001_enrich_candidates_add_caches.py#L42-L111)

**Section sources**
- [alembic/versions/001_enrich_candidates_add_caches.py:1-129](file://alembic/versions/001_enrich_candidates_add_caches.py#L1-L129)

### Version 002: Parser snapshot JSON
- Purpose: Stores the complete parser output for auditability and re-analysis without reparsing.
- Key changes:
  - Adds parser_snapshot_json column to candidates.
- Idempotency: Skips if column already exists.
- Downgrade: Drops the column.

```mermaid
flowchart TD
Start(["Upgrade"]) --> Inspect["Inspect candidates columns"]
Inspect --> HasCol{"parser_snapshot_json exists?"}
HasCol --> |No| AddCol["Add parser_snapshot_json column"]
HasCol --> |Yes| Skip["Skip addition"]
AddCol --> End(["Done"])
Skip --> End
```

**Diagram sources**
- [alembic/versions/002_parser_snapshot_json.py:21-29](file://alembic/versions/002_parser_snapshot_json.py#L21-L29)

**Section sources**
- [alembic/versions/002_parser_snapshot_json.py:1-34](file://alembic/versions/002_parser_snapshot_json.py#L1-L34)

### Version 003: Subscription system with usage tracking and seeding
- Purpose: Introduces subscription plans, tenant usage tracking, and usage logs; seeds initial plans and links existing tenants.
- Key changes:
  - Enhances subscription_plans with pricing, descriptions, features, and sorting.
  - Adds usage tracking columns to tenants.
  - Creates usage_logs table with foreign keys and indexes.
  - Seeds initial plans (Free, Pro, Enterprise) and updates existing tenants to default Pro plan.
- Idempotency: Safe for legacy setups; inserts only missing plan records.
- Downgrade: Drops usage_logs and removes tenant and plan columns in reverse order.

```mermaid
flowchart TD
Start(["Upgrade"]) --> InspectSP["Inspect subscription_plans columns"]
InspectSP --> SPAdd["Add missing columns"]
SPAdd --> IDXSP["Ensure indexes on subscription_plans"]
IDXSP --> InspectTenants["Inspect tenants columns"]
InspectTenants --> TenantsAdd["Add usage tracking columns"]
TenantsAdd --> IDXTenants["Ensure indexes on tenants"]
IDXTenants --> InspectUL["Check usage_logs existence"]
InspectUL --> |Missing| CreateUL["Create usage_logs + indexes"]
InspectUL --> |Exists| ULIdx["Ensure indexes exist"]
CreateUL --> SeedPlans["Seed initial plans (idempotent)"]
ULIdx --> SeedPlans
SeedPlans --> LinkTenants["Link existing tenants to Pro plan"]
LinkTenants --> End(["Done"])
```

**Diagram sources**
- [alembic/versions/003_subscription_system.py:43-252](file://alembic/versions/003_subscription_system.py#L43-L252)

**Section sources**
- [alembic/versions/003_subscription_system.py:1-290](file://alembic/versions/003_subscription_system.py#L1-L290)

### Version 004: Narrative JSON for async LLM processing
- Purpose: Adds narrative_json column to screening_results to support asynchronous LLM narrative generation.
- Key changes:
  - Adds nullable narrative_json TEXT column to screening_results table.
  - Allows immediate Python scoring results while LLM narrative generates in background.
- Idempotency: Skips if column already exists.
- Downgrade: Drops the narrative_json column.

**Section sources**
- [alembic/versions/004_narrative_json.py:1-37](file://alembic/versions/004_narrative_json.py#L1-L37)

### Version 005: JWT token revocation support
- Purpose: Implements token revocation system to prevent logout refresh token reuse.
- Key changes:
  - Creates revoked_tokens table with primary key, unique JWT ID, and timestamps.
  - Adds indexes on id and jti columns for efficient lookups.
  - Supports periodic cleanup of expired tokens.
- Idempotency: Safe when table already exists; ensures indexes are present.
- Downgrade: Drops indexes and table in reverse order.

```mermaid
flowchart TD
Start(["Upgrade"]) --> Inspect["Check revoked_tokens table"]
Inspect --> Exists{"Table exists?"}
Exists --> |No| CreateTable["Create revoked_tokens table"]
Exists --> |Yes| CheckIdx["Check existing indexes"]
CreateTable --> CreateIdx["Create id and jti indexes"]
CheckIdx --> MissingIdx{"Indexes missing?"}
MissingIdx --> |Yes| AddIdx["Add missing indexes"]
MissingIdx --> |No| End(["Done"])
AddIdx --> End
```

**Diagram sources**
- [alembic/versions/005_revoked_tokens.py:41-61](file://alembic/versions/005_revoked_tokens.py#L41-L61)

**Section sources**
- [alembic/versions/005_revoked_tokens.py:1-67](file://alembic/versions/005_revoked_tokens.py#L1-L67)

### Version 006: Performance indexes and timestamp tracking
- Purpose: Enhances database performance through strategic indexing and adds timestamp tracking.
- Key changes:
  - Adds index on screening_results.candidate_id for improved query performance.
  - Adds index on screening_results.timestamp for time-based queries.
  - Adds created_at column to jd_cache table with timezone-aware timestamps.
- Idempotency: Safe when indexes/columns already exist.
- Downgrade: Drops indexes and drops created_at column.

```mermaid
flowchart TD
Start(["Upgrade"]) --> CheckSR["Check screening_results indexes"]
CheckSR --> CandIdx{"candidate_id index exists?"}
CandIdx --> |No| AddCandIdx["Create candidate_id index"]
CandIdx --> |Yes| CheckTS["Check timestamp index"]
AddCandIdx --> CheckTS
CheckTS --> TSIdx{"timestamp index exists?"}
TSIdx --> |No| AddTSIdx["Create timestamp index"]
TSIdx --> |Yes| CheckJD["Check jd_cache created_at"]
AddTSIdx --> CheckJD
CheckJD --> JDExists{"created_at column exists?"}
JDExists --> |No| AddJD["Add created_at column with default timestamp"]
JDExists --> |Yes| End(["Done"])
AddJD --> End
```

**Diagram sources**
- [alembic/versions/006_indexes_and_jdcache_created_at.py:35-63](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L35-L63)

**Section sources**
- [alembic/versions/006_indexes_and_jdcache_created_at.py:1-73](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L1-L73)

### Version 007: Comprehensive narrative status tracking
- Purpose: Adds robust status tracking for LLM narrative generation with intelligent backfill logic.
- Key changes:
  - Adds narrative_status column (String(20), default='pending') to support four-state system.
  - Adds narrative_error column (Text, nullable=True) for error details when failed.
  - Implements intelligent backfill logic: existing rows with narrative_json become 'ready'.
  - Uses existence checks to handle partial migration scenarios.
- Status states:
  - pending: Initial state when narrative generation starts
  - processing: LLM narrative is currently being generated
  - ready: LLM narrative successfully generated and stored
  - failed: LLM narrative generation encountered an error
- Idempotency: Safe when columns already exist; handles missing narrative_json gracefully.
- Downgrade: Drops both columns using batch_alter_table for SQLite compatibility.

```mermaid
flowchart TD
Start(["Upgrade"]) --> Inspect["Inspect screening_results columns"]
Inspect --> CheckStatus{"narrative_status exists?"}
CheckStatus --> |No| AddStatus["Add narrative_status column with default 'pending'"]
CheckStatus --> |Yes| CheckError["Check narrative_error"]
AddStatus --> CheckError
CheckError --> |No| AddError["Add narrative_error column"]
CheckError --> |Yes| CheckJson["Check narrative_json existence"]
AddError --> CheckJson
CheckJson --> |Exists| Backfill["Backfill existing rows: set status='ready' where narrative_json IS NOT NULL"]
CheckJson --> |Missing| End(["Done"])
Backfill --> End
```

**Diagram sources**
- [alembic/versions/007_narrative_status.py:32-57](file://alembic/versions/007_narrative_status.py#L32-L57)

**Section sources**
- [alembic/versions/007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)

### Version 008: Analysis queue system
- Purpose: Implements background processing queue for analysis tasks to improve system responsiveness.
- Key changes:
  - Creates analysis_queue table with task management and priority handling.
  - Adds indexes on status and created_at for efficient queue operations.
  - Supports task prioritization and retry mechanisms.
- Idempotency: Safe when table already exists; ensures indexes are present.
- Downgrade: Drops indexes and table in reverse order.

**Section sources**
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)

### Version 009: Intelligent scoring weights system
- Purpose: Introduces intelligent, role-adaptive scoring weights with version management and role category detection.
- Key changes:
  - Adds is_active boolean column for version management of screening results.
  - Adds version_number integer column for tracking result versions.
  - Adds role_category string column for role classification (technical, sales, hr, etc.).
  - Adds weight_reasoning text column for storing AI-generated weight explanations.
  - Adds suggested_weights_json text column for storing suggested scoring weights.
  - Creates indexes on is_active and version_number for efficient querying.
  - Applies defaults to existing records (is_active=True, version_number=1).
- Status states:
  - pending: Initial state for new screening results
  - shortlisted: Candidate selected for further consideration
  - rejected: Candidate not suitable for position
  - in-review: Under evaluation by hiring team
  - hired: Candidate successfully placed
- Idempotency: Safe when columns already exist; applies defaults to existing records.
- Downgrade: Drops all new columns and indexes in reverse order.

```mermaid
flowchart TD
Start(["Upgrade"]) --> CheckColumns["Check screening_results columns"]
CheckColumns --> IsActive{"is_active exists?"}
IsActive --> |No| AddActive["Add is_active boolean column"]
IsActive --> |Yes| VersionNum["Check version_number"]
AddActive --> VersionNum
VersionNum --> |No| AddVersion["Add version_number integer column"]
VersionNum --> |Yes| RoleCat["Check role_category"]
AddVersion --> RoleCat
RoleCat --> |No| AddRole["Add role_category string column"]
RoleCat --> |Yes| Reasoning["Check weight_reasoning"]
AddRole --> Reasoning
Reasoning --> |No| AddReason["Add weight_reasoning text column"]
Reasoning --> |Yes| Suggested["Check suggested_weights_json"]
AddReason --> Suggested
Suggested --> |No| AddSuggested["Add suggested_weights_json text column"]
Suggested --> |Yes| CreateIdx["Create indexes on is_active and version_number"]
AddSuggested --> CreateIdx
CreateIdx --> Defaults["Apply defaults to existing records"]
Defaults --> End(["Done"])
```

**Diagram sources**
- [alembic/versions/009_intelligent_scoring_weights.py:27-74](file://alembic/versions/009_intelligent_scoring_weights.py#L27-L74)

**Section sources**
- [alembic/versions/009_intelligent_scoring_weights.py:1-93](file://alembic/versions/009_intelligent_scoring_weights.py#L1-L93)

### Version 010: JD text storage and advanced indexing
- Purpose: Adds JD text storage for RAG learning and creates advanced indexes for improved performance.
- Key changes:
  - Adds jd_text column to screening_results table for similarity matching.
  - Creates index on role_category for faster calibration queries.
  - Creates composite index on (tenant_id, role_category, is_active) for calibration performance.
- Idempotency: Safe when columns/indexes already exist; handles partial migration scenarios.
- Downgrade: Drops indexes and column in reverse order.

```mermaid
flowchart TD
Start(["Upgrade"]) --> CheckSR["Check screening_results columns"]
CheckSR --> JDText{"jd_text exists?"}
JDText --> |No| AddJD["Add jd_text text column"]
JDText --> |Yes| CheckIdx["Check existing indexes"]
AddJD --> CheckIdx
CheckIdx --> RoleIdx{"role_category index exists?"}
RoleIdx --> |No| AddRoleIdx["Create index on role_category"]
RoleIdx --> |Yes| CalibIdx["Check calibration index"]
AddRoleIdx --> CalibIdx
CalibIdx --> CalibExists{"calibration index exists?"}
CalibExists --> |No| AddCalib["Create composite index (tenant_id, role_category, is_active)"]
CalibExists --> |Yes| End(["Done"])
AddCalib --> End
```

**Diagram sources**
- [alembic/versions/010_add_jd_text_to_screening_result.py:28-57](file://alembic/versions/010_add_jd_text_to_screening_result.py#L28-L57)

**Section sources**
- [alembic/versions/010_add_jd_text_to_screening_result.py:1-69](file://alembic/versions/010_add_jd_text_to_screening_result.py#L1-L69)

### Version 011: Narrative tracking enhancements
- Purpose: Adds narrative_generated_at timestamp for tracking completion time and enhances backfill logic.
- Key changes:
  - Adds narrative_generated_at DateTime column for tracking when LLM narrative completes.
  - Enhances backfill logic to properly set narrative_status for existing records.
  - Handles edge cases where narrative_status might be empty vs NULL.
- Status states:
  - pending: Initial state when narrative generation starts
  - ready: LLM narrative successfully generated and stored
- Idempotency: Safe when columns already exist; applies enhanced backfill logic.
- Downgrade: Drops narrative_generated_at column.

```mermaid
flowchart TD
Start(["Upgrade"]) --> CheckColumns["Check screening_results columns"]
CheckColumns --> GenAt{"narrative_generated_at exists?"}
GenAt --> |No| AddGen["Add narrative_generated_at timestamp column"]
GenAt --> |Yes| Backfill["Enhanced backfill logic"]
AddGen --> Backfill
Backfill --> ReadyCheck["Set status='ready' for records with narrative_json"]
ReadyCheck --> PendingCheck["Set status='pending' for records without narrative_json"]
PendingCheck --> End(["Done"])
```

**Diagram sources**
- [alembic/versions/011_narrative_tracking_enhancement.py:25-51](file://alembic/versions/011_narrative_tracking_enhancement.py#L25-L51)

**Section sources**
- [alembic/versions/011_narrative_tracking_enhancement.py:1-57](file://alembic/versions/011_narrative_tracking_enhancement.py#L1-L57)

### Environment and Configuration
- alembic/env.py:
  - Loads application models to register them with Alembic metadata.
  - Sets the database URL from the application's DATABASE_URL.
  - Supports offline and online migration modes.
- alembic.ini:
  - Defines script location, path handling, logging, and database URL placeholder.
  - Provides hooks for formatting and linting generated revisions.

```mermaid
graph LR
Env["env.py"] --> Meta["Base.metadata"]
Env --> URL["DATABASE_URL"]
Cfg["alembic.ini"] --> Env
Models["db_models.py"] --> Env
```

**Diagram sources**
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [alembic.ini:1-148](file://alembic.ini#L1-L148)
- [app/backend/models/db_models.py:1-269](file://app/backend/models/db_models.py#L1-L269)
- [app/backend/db/database.py:1-50](file://app/backend/db/database.py#L1-L50)

**Section sources**
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [alembic.ini:1-148](file://alembic.ini#L1-L148)
- [app/backend/db/database.py:1-50](file://app/backend/db/database.py#L1-L50)
- [app/backend/models/db_models.py:1-269](file://app/backend/models/db_models.py#L1-L269)

## Dependency Analysis
- Alembic depends on:
  - Application models registered in env.py.
  - DATABASE_URL from app/backend/db/database.py.
  - alembic.ini for configuration and logging.
- Migrations depend on:
  - Correct ordering (001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 010 → 011).
  - Idempotent operations to handle partial runs or legacy setups.
  - Fixed dependency chain ensuring proper migration sequencing.
- CI/CD:
  - CI workflow validates backend tests; CD workflow builds and pushes images and deploys to production.

```mermaid
graph TB
A["alembic.ini"] --> B["alembic/env.py"]
B --> C["app/backend/db/database.py"]
B --> D["app/backend/models/db_models.py"]
E["001_enrich_candidates_add_caches.py"] --> F["002_parser_snapshot_json.py"]
F --> G["003_subscription_system.py"]
G --> H["004_narrative_json.py"]
H --> I["005_revoked_tokens.py"]
I --> J["006_indexes_and_jdcache_created_at.py"]
J --> K["007_narrative_status.py"]
K --> L["008_analysis_queue_system.py"]
L --> M["009_intelligent_scoring_weights.py"]
M --> N["010_add_jd_text_to_screening_result.py"]
N --> O["011_narrative_tracking_enhancement.py"]
P[".github/workflows/ci.yml"] --> Q[".github/workflows/cd.yml"]
```

**Diagram sources**
- [alembic.ini:1-148](file://alembic.ini#L1-L148)
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [app/backend/db/database.py:1-50](file://app/backend/db/database.py#L1-L50)
- [app/backend/models/db_models.py:1-269](file://app/backend/models/db_models.py#L1-L269)
- [alembic/versions/001_enrich_candidates_add_caches.py:1-129](file://alembic/versions/001_enrich_candidates_add_caches.py#L1-L129)
- [alembic/versions/002_parser_snapshot_json.py:1-34](file://alembic/versions/002_parser_snapshot_json.py#L1-L34)
- [alembic/versions/003_subscription_system.py:1-290](file://alembic/versions/003_subscription_system.py#L1-L290)
- [alembic/versions/004_narrative_json.py:1-37](file://alembic/versions/004_narrative_json.py#L1-L37)
- [alembic/versions/005_revoked_tokens.py:1-67](file://alembic/versions/005_revoked_tokens.py#L1-L67)
- [alembic/versions/006_indexes_and_jdcache_created_at.py:1-73](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L1-L73)
- [alembic/versions/007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)
- [alembic/versions/009_intelligent_scoring_weights.py:1-93](file://alembic/versions/009_intelligent_scoring_weights.py#L1-L93)
- [alembic/versions/010_add_jd_text_to_screening_result.py:1-69](file://alembic/versions/010_add_jd_text_to_screening_result.py#L1-L69)
- [alembic/versions/011_narrative_tracking_enhancement.py:1-57](file://alembic/versions/011_narrative_tracking_enhancement.py#L1-L57)
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

**Section sources**
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [app/backend/db/database.py:1-50](file://app/backend/db/database.py#L1-L50)
- [app/backend/models/db_models.py:1-269](file://app/backend/models/db_models.py#L1-L269)
- [alembic/versions/001_enrich_candidates_add_caches.py:1-129](file://alembic/versions/001_enrich_candidates_add_caches.py#L1-L129)
- [alembic/versions/002_parser_snapshot_json.py:1-34](file://alembic/versions/002_parser_snapshot_json.py#L1-L34)
- [alembic/versions/003_subscription_system.py:1-290](file://alembic/versions/003_subscription_system.py#L1-L290)
- [alembic/versions/004_narrative_json.py:1-37](file://alembic/versions/004_narrative_json.py#L1-L37)
- [alembic/versions/005_revoked_tokens.py:1-67](file://alembic/versions/005_revoked_tokens.py#L1-L67)
- [alembic/versions/006_indexes_and_jdcache_created_at.py:1-73](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L1-L73)
- [alembic/versions/007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)
- [alembic/versions/009_intelligent_scoring_weights.py:1-93](file://alembic/versions/009_intelligent_scoring_weights.py#L1-L93)
- [alembic/versions/010_add_jd_text_to_screening_result.py:1-69](file://alembic/versions/010_add_jd_text_to_screening_result.py#L1-L69)
- [alembic/versions/011_narrative_tracking_enhancement.py:1-57](file://alembic/versions/011_narrative_tracking_enhancement.py#L1-L57)
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

## Performance Considerations
- Idempotent migrations reduce repeated work and improve reliability across environments.
- Strategic indexing improves query performance for frequently accessed columns.
- Timestamp tracking enables better audit trails and time-based analytics.
- Using batch_alter_table for dropping multiple columns minimizes transaction overhead.
- The new intelligent scoring system provides granular control over role-based weighting and version management.
- Advanced indexing on role_category and composite indexes optimize calibration and filtering queries.
- Background processing queues ensure non-blocking user experience during heavy computations.
- Narrative tracking enhancements provide precise timing and status management for LLM operations.
- Production deployments rely on Docker Compose and Watchtower for automated updates; ensure migrations are run before deploying new backend images to avoid downtime.

**Updated** Enhanced with new performance optimizations from versions 008-011, including intelligent scoring with role category detection, advanced indexing, background processing, and comprehensive narrative tracking.

## Troubleshooting Guide
Common issues and resolutions:
- Database URL mismatch:
  - Verify DATABASE_URL in env.py and application configuration.
- Migration conflicts:
  - Ensure migrations are applied in order (001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 010 → 011).
  - Use downgrade to revert problematic versions before retrying.
- Multiple heads error:
  - Verify correct down_revision chain (010 → 011).
  - Check that each migration properly references its parent revision.
- Idempotency failures:
  - Confirm that idempotent checks (existence checks) are functioning as intended.
- Intelligent scoring issues:
  - Verify that role_category, weight_reasoning, and suggested_weights_json columns exist in screening_results table.
  - Check that version management columns (is_active, version_number) are properly populated.
  - Monitor background analysis queue for proper task processing.
- Narrative tracking issues:
  - Verify that narrative_status and narrative_error columns exist in screening_results table.
  - Check that backfill logic ran correctly for existing records.
  - Monitor background LLM tasks for proper status updates and narrative_generated_at timestamps.
- Analysis queue problems:
  - Verify that analysis_queue table exists with proper indexes.
  - Check queue worker processes are running and processing tasks.
- CI/CD pipeline failures:
  - Review CI workflow logs for backend test failures.
  - For CD, confirm Docker images are built and pushed, and Watchtower is running in production.

**Updated** Added troubleshooting guidance for the expanded migration chain, intelligent scoring system, advanced indexing, background processing, and comprehensive narrative tracking enhancements.

**Section sources**
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [alembic/versions/001_enrich_candidates_add_caches.py:1-129](file://alembic/versions/001_enrich_candidates_add_caches.py#L1-L129)
- [alembic/versions/002_parser_snapshot_json.py:1-34](file://alembic/versions/002_parser_snapshot_json.py#L1-L34)
- [alembic/versions/003_subscription_system.py:1-290](file://alembic/versions/003_subscription_system.py#L1-L290)
- [alembic/versions/004_narrative_json.py:1-37](file://alembic/versions/004_narrative_json.py#L1-L37)
- [alembic/versions/005_revoked_tokens.py:1-67](file://alembic/versions/005_revoked_tokens.py#L1-L67)
- [alembic/versions/006_indexes_and_jdcache_created_at.py:1-73](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L1-L73)
- [alembic/versions/007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)
- [alembic/versions/009_intelligent_scoring_weights.py:1-93](file://alembic/versions/009_intelligent_scoring_weights.py#L1-L93)
- [alembic/versions/010_add_jd_text_to_screening_result.py:1-69](file://alembic/versions/010_add_jd_text_to_screening_result.py#L1-L69)
- [alembic/versions/011_narrative_tracking_enhancement.py:1-57](file://alembic/versions/011_narrative_tracking_enhancement.py#L1-L57)
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

## Conclusion
The Resume AI migration system uses Alembic to evolve the schema safely and predictably. Versions 001 through 011 introduce candidate enrichment, parser snapshots, subscription/usage systems, JWT token revocation, performance optimizations, comprehensive status tracking for LLM narrative generation, intelligent scoring with role category detection, advanced indexing, background processing queues, and narrative tracking enhancements. The environment and configuration integrate tightly with the application's models and database URL. Recent improvements include fixing the multiple heads error through proper dependency chaining, implementing comprehensive performance indexing, adding robust status tracking infrastructure, and introducing intelligent scoring capabilities. CI/CD pipelines support automated testing and deployment, while idempotent migrations and careful downgrade procedures help maintain safety across environments.

**Updated** Enhanced with the latest migration chain supporting JWT token revocation, intelligent scoring with role category detection, advanced indexing, background processing, and comprehensive narrative tracking enhancements.

## Appendices

### Migration Workflow
- Create a revision:
  - Use Alembic's revision command to generate a new file under alembic/versions.
  - Edit the generated file to implement upgrade() and downgrade() operations.
  - Ensure proper down_revision reference to maintain dependency chain.
- Execute migrations:
  - Upgrade: alembic upgrade head
  - Downgrade: alembic downgrade -1 or alembic downgrade <target_rev>
- Rollback procedures:
  - Use downgrade to revert to a known-good revision.
  - For production, coordinate with CI/CD to roll back images if necessary.

**Section sources**
- [alembic.ini:1-148](file://alembic.ini#L1-L148)
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)

### Database Initialization and Seed Data
- Initialization:
  - Alembic env.py loads models and DATABASE_URL; migrations target Base.metadata.
- Seed data:
  - Version 003 seeds subscription plans and links existing tenants to the Pro plan.
  - New migrations maintain idempotent seeding patterns.

**Section sources**
- [alembic/env.py:1-51](file://alembic/env.py#L1-L51)
- [alembic/versions/003_subscription_system.py:119-251](file://alembic/versions/003_subscription_system.py#L119-L251)

### Production Deployment Strategies
- Local development:
  - docker-compose.yml defines services and environment variables for local testing.
- Production:
  - docker-compose.prod.yml manages production resources, Watchtower for updates, and health checks.
- CI/CD:
  - CI workflow runs backend tests; CD workflow builds images and deploys to production.

**Section sources**
- [docker-compose.yml:1-102](file://docker-compose.yml#L1-L102)
- [docker-compose.prod.yml:1-236](file://docker-compose.prod.yml#L1-L236)
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

### Best Practices and Testing
- Idempotency:
  - Guard operations with existence checks for tables, columns, and indexes.
- Backward compatibility:
  - Use nullable columns and defaults when extending existing tables.
- Testing:
  - Run backend tests in CI to catch migration-related regressions.
- Rollback scenarios:
  - Maintain downgrade paths for all changes; test downgrades in staging.
- Performance optimization:
  - Implement strategic indexing for frequently queried columns.
  - Monitor migration performance and adjust indexing strategy as needed.
- Intelligent scoring:
  - Ensure proper role category assignment and weight reasoning storage.
  - Implement proper version management with is_active and version_number columns.
  - Test backfill logic for existing records during migration.
- Status tracking:
  - Ensure proper status state transitions in background LLM tasks.
  - Implement proper error handling and fallback mechanisms.
  - Test backfill logic for existing records during migration.
  - Monitor narrative_generated_at timestamps for accurate completion tracking.

**Section sources**
- [alembic/versions/001_enrich_candidates_add_caches.py:1-129](file://alembic/versions/001_enrich_candidates_add_caches.py#L1-L129)
- [alembic/versions/002_parser_snapshot_json.py:1-34](file://alembic/versions/002_parser_snapshot_json.py#L1-L34)
- [alembic/versions/003_subscription_system.py:1-290](file://alembic/versions/003_subscription_system.py#L1-L290)
- [alembic/versions/004_narrative_json.py:1-37](file://alembic/versions/004_narrative_json.py#L1-L37)
- [alembic/versions/005_revoked_tokens.py:1-67](file://alembic/versions/005_revoked_tokens.py#L1-L67)
- [alembic/versions/006_indexes_and_jdcache_created_at.py:1-73](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L1-L73)
- [alembic/versions/007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)
- [alembic/versions/009_intelligent_scoring_weights.py:1-93](file://alembic/versions/009_intelligent_scoring_weights.py#L1-L93)
- [alembic/versions/010_add_jd_text_to_screening_result.py:1-69](file://alembic/versions/010_add_jd_text_to_screening_result.py#L1-L69)
- [alembic/versions/011_narrative_tracking_enhancement.py:1-57](file://alembic/versions/011_narrative_tracking_enhancement.py#L1-L57)
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)

### Intelligent Scoring System Implementation Details
- Role category system:
  - Supports categories: technical, sales, hr, marketing, operations, leadership
  - Enables role-adaptive scoring weights and suggestions
  - Facilitates intelligent calibration and filtering
- Version management:
  - is_active flag for current version identification
  - version_number for tracking result evolution
  - Composite indexing for efficient version queries
- Weight reasoning:
  - Stores AI-generated explanations for scoring decisions
  - Supports transparency and auditability in decision-making
- Backfill logic:
  - Existing records automatically receive defaults (is_active=True, version_number=1)
  - Graceful handling of partial migration scenarios
  - Safe operation even when new columns don't exist

**Section sources**
- [app/backend/models/db_models.py:129-154](file://app/backend/models/db_models.py#L129-L154)
- [alembic/versions/009_intelligent_scoring_weights.py:27-74](file://alembic/versions/009_intelligent_scoring_weights.py#L27-L74)

### Advanced Indexing and Performance Optimization
- Strategic indexing:
  - role_category index for calibration queries
  - Composite index (tenant_id, role_category, is_active) for performance
  - Indexes on is_active and version_number for intelligent scoring
  - Performance indexes on candidate_id and timestamp for screening results
- Query optimization:
  - Efficient role-based filtering and calibration
  - Fast version retrieval and comparison
  - Optimized background queue operations
- Backward compatibility:
  - All new indexes are created conditionally
  - Safe operation when indexes already exist
  - Graceful handling of partial migration scenarios

**Section sources**
- [alembic/versions/009_intelligent_scoring_weights.py:59-73](file://alembic/versions/009_intelligent_scoring_weights.py#L59-L73)
- [alembic/versions/010_add_jd_text_to_screening_result.py:42-56](file://alembic/versions/010_add_jd_text_to_screening_result.py#L42-L56)
- [alembic/versions/006_indexes_and_jdcache_created_at.py:35-63](file://alembic/versions/006_indexes_and_jdcache_created_at.py#L35-L63)

### Background Processing and Queue Management
- Analysis queue system:
  - Dedicated table for background task management
  - Priority-based task scheduling and execution
  - Retry mechanisms and error handling
  - Indexes for efficient queue operations
- Integration points:
  - Seamless coordination with intelligent scoring system
  - Support for narrative generation and processing
  - Background task coordination for LLM operations
- Monitoring and maintenance:
  - Queue worker processes for continuous operation
  - Task status tracking and reporting
  - Periodic cleanup and maintenance procedures

**Section sources**
- [alembic/versions/008_analysis_queue_system.py:1-120](file://alembic/versions/008_analysis_queue_system.py#L1-L120)
- [app/backend/services/hybrid_pipeline.py:1900-2038](file://app/backend/services/hybrid_pipeline.py#L1900-L2038)
- [app/backend/routes/analyze.py:1130-1169](file://app/backend/routes/analyze.py#L1130-L1169)

### Narrative Tracking Enhancement Implementation Details
- Completion tracking:
  - narrative_generated_at timestamp for precise completion timing
  - Enhanced backfill logic for existing records
  - Improved status management for LLM operations
- Status management:
  - Four-state system: pending, processing, ready, failed
  - Enhanced error tracking and reporting
  - Backward compatibility with existing status values
- Service integration:
  - Real-time status updates in background LLM tasks
  - Routes check narrative_status for display logic
  - Error messages stored in narrative_error for debugging
- Backfill logic:
  - Existing records with narrative_json automatically marked as 'ready'
  - Graceful handling of partial migration scenarios
  - Safe operation even when narrative_json column doesn't exist

**Section sources**
- [alembic/versions/011_narrative_tracking_enhancement.py:20-51](file://alembic/versions/011_narrative_tracking_enhancement.py#L20-L51)
- [app/backend/services/hybrid_pipeline.py:1900-2038](file://app/backend/services/hybrid_pipeline.py#L1900-L2038)
- [app/backend/routes/analyze.py:1130-1169](file://app/backend/routes/analyze.py#L1130-L1169)