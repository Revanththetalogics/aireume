# Skills Registry Extension

<cite>
**Referenced Files in This Document**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)
- [main.py](file://app/backend/main.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)
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
This document provides comprehensive guidance for extending the skills registry system in Resume AI. It covers adding new skills categories, implementing custom skill alias mappings, extending domain keyword recognition, and maintaining the skills database. It also explains dynamic skill loading, hot-reloading capabilities, and advanced features such as skill frequency tracking and integration with external skill databases. Practical examples demonstrate how to extend the MASTER_SKILLS list, implement custom normalization rules, and create domain-specific skill hierarchies. Performance considerations and optimization techniques for large skills registries are included.

## Project Structure
The skills registry is implemented in the backend service layer and backed by a database model. The key files are:
- Skills registry and matching logic: [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- Database model for skills: [db_models.py](file://app/backend/models/db_models.py)
- Resume parsing integration: [parser_service.py](file://app/backend/services/parser_service.py)
- Database migration for skills table: [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)
- Application initialization and skills registry bootstrap: [main.py](file://app/backend/main.py)
- Tests covering skills normalization and matching: [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)

```mermaid
graph TB
subgraph "Backend Services"
HP["hybrid_pipeline.py<br/>SkillsRegistry, matching, normalization"]
PS["parser_service.py<br/>Resume parsing + skills extraction"]
MAIN["main.py<br/>App bootstrap + skills seed/load"]
end
subgraph "Database"
DBM["db_models.py<br/>Skill model"]
MIG["001_enrich_candidates_add_caches.py<br/>Alembic migration"]
end
subgraph "Tests"
TST["test_hybrid_pipeline.py<br/>Skills normalization & matching tests"]
end
HP --> DBM
PS --> HP
MAIN --> HP
DBM --> MIG
TST --> HP
```

**Diagram sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)
- [main.py](file://app/backend/main.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)
- [main.py](file://app/backend/main.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)

## Core Components
- SkillsRegistry: In-memory flashtext-based keyword processor with hot-reload capability. Loads skills from the database or falls back to MASTER_SKILLS.
- MASTER_SKILLS: Hardcoded list of canonical skills used as the baseline.
- SKILL_ALIASES: Dictionary mapping canonical skills to their aliases for normalization and matching.
- DOMAIN_KEYWORDS: Domain keyword map used to seed skill domains during initial population.
- Skill model: Database-backed model supporting active status, source, domain, and frequency tracking.
- Parser integration: Resume parser leverages the skills registry for extraction and fallback scanning.

Key responsibilities:
- Dynamic loading and rebuilding of skills registry
- Canonical skill normalization and alias expansion
- Domain mapping for skills
- Frequency tracking for skills
- Hot-reloading without application restart

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [parser_service.py](file://app/backend/services/parser_service.py)

## Architecture Overview
The skills registry architecture integrates database-backed persistence with in-memory fast text processing. The system seeds skills from MASTER_SKILLS and SKILL_ALIASES, stores them in the database, and loads them into a flashtext processor for efficient matching. The parser uses the registry for both structured extraction and full-text scanning.

```mermaid
sequenceDiagram
participant APP as "Application Startup"
participant MAIN as "main.py"
participant SR as "SkillsRegistry"
participant DB as "Database"
participant REG as "flashtext Processor"
APP->>MAIN : Initialize app
MAIN->>SR : seed_if_empty(db)
SR->>DB : Upsert skills from MASTER_SKILLS + SKILL_ALIASES
MAIN->>SR : load(db)
SR->>DB : Query active skills
SR->>REG : Build KeywordProcessor with skills + aliases
SR-->>APP : Skills registry ready
```

**Diagram sources**
- [main.py](file://app/backend/main.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)

**Section sources**
- [main.py](file://app/backend/main.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)

## Detailed Component Analysis

### SkillsRegistry Class
The SkillsRegistry encapsulates:
- Lazy loading of skills from the database
- Building a flashtext KeywordProcessor with canonical skills and aliases
- Hot-reloading via rebuild()
- Access to all loaded skills and the processor

Implementation highlights:
- seed_if_empty(): Upserts MASTER_SKILLS into the database using PostgreSQL ON CONFLICT DO NOTHING to avoid duplicates and safely add new skills.
- load(): Queries active skills, merges aliases, and builds the processor. Falls back to MASTER_SKILLS if DB query fails.
- rebuild(): Marks registry as unloaded and reloads on next access.
- get_processor()/get_all_skills(): Provides access to the processor and the loaded skill list.

```mermaid
classDiagram
class SkillsRegistry {
- _processor
- _skills : str[]
- _loaded : bool
+ __init__()
+ seed_if_empty(db)
+ load(db)
+ rebuild(db)
+ get_processor()
+ get_all_skills() str[]
}
class Skill {
+ id : int
+ name : str
+ aliases : str
+ domain : str
+ status : str
+ source : str
+ frequency : int
+ created_at : datetime
}
SkillsRegistry --> Skill : "loads from"
```

**Diagram sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [db_models.py](file://app/backend/models/db_models.py)

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [db_models.py](file://app/backend/models/db_models.py)

### Database Schema for Skills Management
The Skill model defines the schema for storing skills in the database:
- id: Primary key
- name: Unique canonical skill name
- aliases: Comma-separated list of aliases
- domain: Primary domain (e.g., backend, frontend, data_science)
- status: Active/pending/rejected
- source: Seed/manual/discovered
- frequency: Count of occurrences in JDs/resumes
- created_at: Timestamp

Migration details:
- Creates the skills table with appropriate indexes
- Ensures id and name uniqueness
- Adds indexes for performance

```mermaid
erDiagram
SKILL {
int id PK
string name UK
text aliases
string domain
string status
string source
int frequency
timestamp created_at
}
```

**Diagram sources**
- [db_models.py](file://app/backend/models/db_models.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)

**Section sources**
- [db_models.py](file://app/backend/models/db_models.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)

### Skill Normalization and Matching
Normalization and matching logic:
- _normalize_skill(): Lowercases and normalizes special characters while preserving specific cases (e.g., C++, C#).
- _expand_skill(): Returns the canonical skill plus all normalized aliases.
- match_skills_rules(): Performs exact/alias substring matching, with a fuzzy fallback using rapidfuzz for approximate matching.

```mermaid
flowchart TD
Start(["Start Matching"]) --> Normalize["Normalize candidate skill"]
Normalize --> Expand["Expand to canonical + aliases"]
Expand --> Exact{"Exact/alias match?"}
Exact --> |Yes| Found["Mark as matched"]
Exact --> |No| Substring{"Substring match?"}
Substring --> |Yes| Found
Substring --> |No| Fuzzy{"Fuzzy match (top 200 candidates)?"}
Fuzzy --> |Yes| Found
Fuzzy --> |No| Missing["Mark as missing"]
Found --> End(["End"])
Missing --> End
```

**Diagram sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)

### Extending the MASTER_SKILLS List
To add new skills categories:
1. Append new canonical skills to the MASTER_SKILLS list in [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py).
2. Run application startup to seed the database via seed_if_empty().
3. The migration ensures new skills are inserted without conflicts.

Guidelines:
- Keep entries lowercase and normalized
- Prefer concise canonical forms
- Group related technologies by category (languages, frameworks, databases, etc.)

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)

### Implementing Custom Skill Alias Mappings
To implement custom alias mappings:
1. Extend SKILL_ALIASES in [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py) with canonical -> [aliases] mappings.
2. On next seed/load, aliases are persisted and added to the flashtext processor.

Best practices:
- Include common abbreviations and alternate names
- Avoid ambiguous mappings that could cause false positives
- Keep alias lists concise and relevant

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)

### Extending Domain Keyword Recognition
To extend domain keyword recognition:
1. Add domain-specific keywords to DOMAIN_KEYWORDS in [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py).
2. During seeding, a domain map is built from keywords to domains and stored with skills.

Recommendations:
- Use representative terms that clearly identify the domain
- Avoid overly generic terms that might misclassify skills
- Align keywords with existing MASTER_SKILLS categories

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)

### Dynamic Skill Loading and Hot-Reloading
Dynamic loading and hot-reloading:
- Skills are loaded lazily on first access.
- rebuild() marks the registry as unloaded, triggering reload on next access.
- seed_if_empty() safely seeds the database on every startup.

Operational notes:
- Use rebuild() to refresh skills after database changes without restarting the app.
- The system gracefully falls back to MASTER_SKILLS if the database is unavailable.

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [main.py](file://app/backend/main.py)

### Skills Database Maintenance Procedures
Maintenance tasks:
- Seed new skills: Call seed_if_empty() to upsert new entries from MASTER_SKILLS.
- Update aliases: Modify SKILL_ALIASES and call rebuild() to refresh the processor.
- Adjust domains: Update DOMAIN_KEYWORDS and re-seed to repopulate domain mappings.
- Monitor frequency: Use the frequency column to track skill popularity and adjust categories accordingly.

Integration points:
- Resume parser uses skills registry for extraction and fallback scanning.
- The registry is initialized during app startup and made available to all pipeline components.

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [main.py](file://app/backend/main.py)

### Advanced Features
- Skill frequency tracking: The frequency column increments based on usage patterns to help prioritize skills.
- Custom validation rules: Implement additional preprocessing in _normalize_skill() or _expand_skill() to enforce stricter normalization.
- External skill database integration: Seed skills from external sources by extending the seed process to pull from external APIs or files, then persist via the same upsert mechanism.

**Section sources**
- [db_models.py](file://app/backend/models/db_models.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)

## Dependency Analysis
The skills registry depends on:
- Database model for persistence
- Alembic migration for schema creation
- Parser service for integration
- Application bootstrap for initialization

```mermaid
graph TB
HP["hybrid_pipeline.py"] --> DBM["db_models.py"]
HP --> PS["parser_service.py"]
MAIN["main.py"] --> HP
DBM --> MIG["001_enrich_candidates_add_caches.py"]
TST["test_hybrid_pipeline.py"] --> HP
```

**Diagram sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)
- [main.py](file://app/backend/main.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)
- [main.py](file://app/backend/main.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)

## Performance Considerations
- Use flashtext for O(k) keyword matching where k is the number of keywords.
- Limit fuzzy matching candidates to a small subset (e.g., top 200) to maintain performance.
- Indexes on skills table improve query performance for active skills retrieval.
- Normalize skills consistently to reduce ambiguity and improve matching accuracy.
- Cache the processor in memory and use hot-reload sparingly to minimize downtime.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Skills not recognized: Verify that the skill exists in MASTER_SKILLS or is seeded in the database. Check that aliases are properly mapped in SKILL_ALIASES.
- Matching inconsistencies: Review _normalize_skill() and _expand_skill() logic for special cases like C++ and C#.
- Database connectivity failures: The system falls back to MASTER_SKILLS; check logs for warnings and ensure the database is reachable.
- Hot-reload not taking effect: Confirm rebuild() is called and the registry is marked as unloaded.

**Section sources**
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [test_hybrid_pipeline.py](file://app/backend/tests/test_hybrid_pipeline.py)

## Conclusion
The skills registry system in Resume AI provides a robust, extensible foundation for managing skills dynamically. By leveraging database-backed persistence, in-memory flashtext processing, and hot-reload capabilities, it supports continuous evolution of skill categories, alias mappings, and domain recognition. Following the extension guidelines and maintenance procedures outlined here will enable seamless integration of new skills and improved matching performance at scale.