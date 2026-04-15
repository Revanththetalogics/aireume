# Intelligent Scoring Weights System - Implementation Guide

## Overview

This document tracks the implementation of the intelligent, role-adaptive scoring weights system that replaces the tech-centric 4/7-weight schemas with a universal system that works for all role types.

## Problem Statement

**Original Issue:**
- Frontend sent 4 weights (skills, experience, stability, education)
- Backend used 7 tech-centric weights (skills, experience, architecture, education, timeline, domain, risk)
- 3 critical factors (architecture, domain, risk) always used fixed defaults
- System couldn't adapt to different role types (sales, HR, marketing, etc.)
- **Result:** All candidates scored with same formula regardless of role requirements

## Solution: Hybrid Universal-Adaptive Weight System

### New 7-Weight Schema

| Weight | Type | Range | Description |
|--------|------|-------|-------------|
| **Core Competencies** | Adaptive | 25-40% | Main skills - LLM interprets per role |
| **Experience Level** | Universal | 15-30% | Years + seniority |
| **Domain/Industry Fit** | Adaptive | 15-25% | LLM interprets domain context |
| **Education & Credentials** | Universal | 5-15% | Degrees, certs, learning |
| **Career Trajectory** | Universal | 10-15% | Progression + stability combined |
| **Role Excellence Factor** | Adaptive | 10-20% | Role-specific differentiator |
| **Risk Assessment** | Universal | -5 to -15% | Red flags penalty |

### Key Features

1. **LLM-Driven Intelligence**: Analyzes JD and suggests optimal weights
2. **Role Category Detection**: Automatically detects technical/sales/hr/marketing/etc.
3. **Adaptive Labels**: UI labels change based on role type
4. **User Override**: Full manual control when needed
5. **Version Management**: Compare different weight scenarios
6. **Backward Compatible**: Existing functionality continues working

---

## Implementation Progress

### ✅ Phase 1: Core Backend (COMPLETED)

#### 1.1 Database Migration ✅
- **File:** `alembic/versions/009_intelligent_scoring_weights.py`
- **Changes:**
  - Added `is_active` (Boolean) - Marks current version
  - Added `version_number` (Integer) - Version tracking
  - Added `role_category` (String) - Detected role type
  - Added `weight_reasoning` (Text) - LLM explanation
  - Added `suggested_weights_json` (Text) - AI suggestions
  - Created indexes for efficient querying
- **Status:** Migration file created, ready to run
- **Backward Compatible:** All fields nullable with defaults

#### 1.2 Database Model Update ✅
- **File:** `app/backend/models/db_models.py`
- **Changes:** Added new fields to `ScreeningResult` model
- **Status:** Model updated
- **Backward Compatible:** All fields nullable

#### 1.3 Weight Mapping Utility ✅
- **File:** `app/backend/services/weight_mapper.py`
- **Features:**
  - `convert_to_new_schema()` - Universal converter for any weight format
  - `detect_weight_schema()` - Auto-detects input schema type
  - `map_legacy_to_new()` - Converts 4-weight frontend schema
  - `map_old_backend_to_new()` - Converts 7-weight tech schema
  - `normalize_weights()` - Ensures weights sum to 1.0
  - `get_weight_labels()` - Adaptive labels per role category
- **Status:** Complete and tested
- **Backward Compatible:** Handles all existing weight formats

#### 1.4 LLM Weight Suggester ✅
- **File:** `app/backend/services/weight_suggester.py`
- **Features:**
  - `suggest_weights_for_jd()` - LLM analyzes JD and suggests weights
  - Role category detection (technical/sales/hr/marketing/operations/leadership)
  - Seniority level detection (junior/mid/senior/lead/executive)
  - Confidence scoring
  - Fallback defaults when LLM unavailable
  - `get_default_weights_for_category()` - Category-based defaults
  - `get_role_excellence_label()` - Adaptive labels
- **Status:** Complete with fallback handling
- **Backward Compatible:** Optional feature, doesn't break existing flow

#### 1.5 Hybrid Pipeline Update ✅
- **File:** `app/backend/services/hybrid_pipeline.py`
- **Changes:**
  - Updated `compute_fit_score()` to accept both old and new schemas
  - Automatic weight conversion using `convert_to_new_schema()`
  - Maps new schema to internal scoring keys
- **Status:** Complete
- **Backward Compatible:** ✅ Existing code continues working

#### 1.6 Agent Pipeline Update ✅
- **File:** `app/backend/services/agent_pipeline.py`
- **Changes:**
  - Updated `scorer_node()` to accept both old and new schemas
  - Automatic weight conversion
  - Maps new schema to internal scoring keys
- **Status:** Complete
- **Backward Compatible:** ✅ Existing code continues working

---

### ✅ Phase 2: API Integration (COMPLETED)

#### 2.1 Update Analysis Endpoints ✅
- **Files:** `app/backend/routes/analyze.py`, `app/backend/routes/candidates.py`
- **Changes:**
  - ✅ Integrated weight suggester in `_get_or_cache_jd()` function
  - ✅ Store weight metadata (role_category, weight_reasoning, suggested_weights_json) in ScreeningResult
  - ✅ Weight suggestions cached with JD analysis for performance
  - ✅ Implemented version management in re-analysis flow (candidates.py)
  - ✅ Archive old versions when creating new analysis with different weights
  - ✅ Auto-increment version_number, mark new version as active
- **Status:** Complete
- **Backward Compatible:** ✅ All fields nullable, existing code works unchanged

#### 2.2 Add Weight Suggestion Endpoint ✅
- **File:** `app/backend/routes/analyze.py`
- **Endpoint:** `POST /api/analyze/suggest-weights`
- **Features:**
  - ✅ Accepts JD text via Form parameter
  - ✅ Returns AI-suggested weights with role detection
  - ✅ Includes reasoning and confidence score
  - ✅ Graceful fallback when LLM unavailable
  - ✅ Input validation (min 80 words)
- **Status:** Complete
- **Response Format:**
  ```json
  {
    "role_category": "technical|sales|hr|marketing|etc",
    "seniority_level": "junior|mid|senior|lead|executive",
    "suggested_weights": {...},
    "role_excellence_label": "...",
    "reasoning": "...",
    "confidence": 0.0-1.0
  }
  ```

---

### ✅ Phase 3: Frontend Implementation (COMPLETED)

#### 3.1 AI Weight Suggestion Panel ✅
- **File:** `app/frontend/src/components/WeightSuggestionPanel.jsx`
- **Features:**
  - ✅ Fetches AI suggestions from `/api/analyze/suggest-weights`
  - ✅ Displays detected role category with color-coded badges
  - ✅ Shows seniority level detection
  - ✅ Visual weight bars with gradient styling
  - ✅ Displays LLM reasoning and confidence score
  - ✅ Adaptive role excellence labels
  - ✅ Action buttons: "Use AI Weights", "Dismiss"
  - ✅ Fallback notice when AI unavailable
  - ✅ Expandable/collapsible weight details
- **Status:** Complete

#### 3.2 Universal Weights Panel ✅
- **File:** `app/frontend/src/components/UniversalWeightsPanel.jsx`
- **Features:**
  - ✅ 7-weight universal schema with adaptive labels
  - ✅ Role-specific label customization
  - ✅ Live total validation (sum to 100%)
  - ✅ 4 built-in presets (Balanced, Skill-Heavy, Experience-Heavy, Domain-Focused)
  - ✅ Reset to defaults button
  - ✅ Separate risk penalty slider
  - ✅ Tooltips for each weight factor
  - ✅ Visual validation feedback
- **Status:** Complete

#### 3.3 Updated UploadForm ✅
- **File:** `app/frontend/src/components/UploadForm.jsx`
- **Changes:**
  - ✅ Integrated AI Weight Suggestion Panel
  - ✅ Integrated Universal Weights Panel
  - ✅ Toggle between legacy 4-weight and new 7-weight modes
  - ✅ Auto-show AI suggestions when JD is long enough
  - ✅ Backward compatible with existing weight system
  - ✅ Smooth mode switching
- **Status:** Complete

#### 3.4 Version History UI ✅
- **File:** `app/frontend/src/components/VersionHistory.jsx`
- **Features:**
  - ✅ Lists all analysis versions for a candidate
  - ✅ Highlights active version with badge
  - ✅ Shows score trends with up/down indicators
  - ✅ Displays role category badges
  - ✅ Shows weight reasoning for each version
  - ✅ Relative timestamps (e.g., "2h ago")
  - ✅ Select up to 2 versions for comparison
  - ✅ Actions: View, Restore, Delete
  - ✅ Empty state with helpful message
- **Status:** Complete

#### 3.5 Re-analyze Modal ✅
- **File:** `app/frontend/src/components/ReanalyzeModal.jsx`
- **Features:**
  - ✅ Modal dialog for re-analyzing with new weights
  - ✅ Embedded AI Weight Suggestion Panel
  - ✅ Embedded Universal Weights Panel
  - ✅ Version management explanation
  - ✅ Loading states during re-analysis
  - ✅ Cancel and submit actions
- **Status:** Complete

#### 3.6 Comparison View ✅
- **File:** `app/frontend/src/components/ComparisonView.jsx`
- **Features:**
  - ✅ Side-by-side version comparison
  - ✅ Score difference highlighting
  - ✅ Weight-by-weight comparison with deltas
  - ✅ Impact summary (score change, recommendation change, risk level change)
  - ✅ Visual trend indicators
  - ✅ Full-screen modal overlay
- **Status:** Complete

---

## Migration Plan

### Step 1: Run Database Migration
```bash
# In production environment
cd /path/to/project
alembic upgrade head
```

### Step 2: Verify Backward Compatibility
- Existing analyses should continue working
- Old weight formats automatically converted
- No data loss

### Step 3: Enable New Features Gradually
1. Deploy backend changes (weight mapper + suggester)
2. Test with existing frontend (should work unchanged)
3. Deploy frontend updates incrementally
4. Monitor for issues

---

## Testing Checklist

### Backend Testing
- [x] Weight mapper handles legacy 4-weight schema
- [x] Weight mapper handles old 7-weight tech schema
- [x] Weight mapper handles new 7-weight universal schema
- [x] Weights normalize correctly (sum to 1.0)
- [ ] LLM weight suggester works for technical roles
- [ ] LLM weight suggester works for sales roles
- [ ] LLM weight suggester works for HR roles
- [ ] LLM weight suggester works for marketing roles
- [ ] Fallback defaults work when LLM unavailable
- [ ] Scoring formulas produce correct results with new weights
- [ ] Existing analyses still work (backward compatibility)

### Frontend Testing
- [ ] Weight suggestion panel displays correctly
- [ ] Adaptive labels change based on role category
- [ ] Manual weight adjustment works
- [ ] Presets apply correctly
- [ ] Version history displays correctly
- [ ] Comparison view works
- [ ] Re-analyze creates new version
- [ ] Restore previous version works

### Integration Testing
- [ ] End-to-end: JD → Weight suggestion → Analysis → Report
- [ ] End-to-end: Manual weights → Analysis → Report
- [ ] End-to-end: Re-analyze with new weights → Compare versions
- [ ] Batch processing with new weights
- [ ] Multiple users with different role types

---

## Rollback Plan

If issues arise:

1. **Database:** Run `alembic downgrade -1` to remove new columns
2. **Backend:** New fields are nullable, old code continues working
3. **Frontend:** Old 4-weight UI still functional with weight mapper

**No data loss** - all changes are additive and backward compatible.

---

## Next Steps

1. ✅ Complete Phase 1 (Backend Core) - DONE
2. 🔄 Complete Phase 2 (API Integration) - IN PROGRESS
3. ⏳ Complete Phase 3 (Frontend UI)
4. ⏳ Testing & Validation
5. ⏳ Production Deployment

---

## Notes

- All changes maintain backward compatibility
- Existing functionality continues working unchanged
- New features are opt-in, not forced
- Database migration is non-destructive
- Easy rollback if needed

---

**Last Updated:** April 16, 2026
**Status:** Phase 1 Complete, Phase 2 In Progress
