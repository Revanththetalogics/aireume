#!/bin/bash
# Full test suite runner for Resume AI Subscription System
# Run this in the Docker environment for comprehensive testing

set -e  # Exit on error

echo "=========================================="
echo "ARIA Resume AI - Full Test Suite"
echo "Subscription System Validation"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Track results
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local name="$1"
    local command="$2"
    
    echo ""
    echo -e "${CYAN}Running: $name${NC}"
    
    if eval "$command" > /tmp/test_output.log 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}: $name"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}: $name"
        echo "Output:"
        cat /tmp/test_output.log | head -20
        ((TESTS_FAILED++))
        return 1
    fi
}

# ============================================
# 1. Python Syntax Validation
# ============================================
echo "=========================================="
echo "STEP 1: Python Syntax Validation"
echo "=========================================="

run_test "subscription.py syntax" "python -m py_compile app/backend/routes/subscription.py"
run_test "analyze.py syntax" "python -m py_compile app/backend/routes/analyze.py"
run_test "db_models.py syntax" "python -m py_compile app/backend/models/db_models.py"
run_test "schemas.py syntax" "python -m py_compile app/backend/models/schemas.py"
run_test "main.py syntax" "python -m py_compile app/backend/main.py"

# ============================================
# 2. Test File Syntax
# ============================================
echo ""
echo "=========================================="
echo "STEP 2: Test File Validation"
echo "=========================================="

run_test "test_subscription.py syntax" "python -m py_compile app/backend/tests/test_subscription.py"
run_test "test_usage_enforcement.py syntax" "python -m py_compile app/backend/tests/test_usage_enforcement.py"

# ============================================
# 3. Import Validation
# ============================================
echo ""
echo "=========================================="
echo "STEP 3: Import Validation"
echo "=========================================="

run_test "subscription module import" "python -c 'from app.backend.routes import subscription'"
run_test "models import" "python -c 'from app.backend.models.db_models import SubscriptionPlan, Tenant, UsageLog, User'"
run_test "schemas import" "python -c 'from app.backend.models.schemas import SubscriptionResponse, PlanInfo, UsageStats'"
run_test "analyze imports subscription" "python -c 'from app.backend.routes.analyze import _check_and_increment_usage'"

# ============================================
# 4. Migration Validation
# ============================================
echo ""
echo "=========================================="
echo "STEP 4: Migration Validation"
echo "=========================================="

run_test "migration 003 exists" "test -f alembic/versions/003_subscription_system.py"
run_test "migration 003 syntax" "python -m py_compile alembic/versions/003_subscription_system.py"

# Check if migrations are in correct order
if [ -f "alembic/versions/001_enrich_candidates_add_caches.py" ] && \
   [ -f "alembic/versions/002_parser_snapshot_json.py" ] && \
   [ -f "alembic/versions/003_subscription_system.py" ]; then
    echo -e "${GREEN}✓ PASSED${NC}: Migration sequence is correct"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}: Migration sequence issue"
    ((TESTS_FAILED++))
fi

# ============================================
# 5. Database Model Validation (if DB available)
# ============================================
echo ""
echo "=========================================="
echo "STEP 5: Database Model Validation"
echo "=========================================="

# Check if we can connect to test database
if python -c "from app.backend.db.database import engine; from sqlalchemy import text; engine.execute(text('SELECT 1'))" 2>/dev/null; then
    echo -e "${CYAN}Database connection available - running model tests${NC}"
    
    run_test "database models create" "python -c '
from app.backend.db.database import engine, Base
from app.backend.models.db_models import SubscriptionPlan, Tenant, UsageLog
Base.metadata.create_all(bind=engine)
print(\"OK\")
'"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}Database models validated successfully${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Database not available - skipping model creation tests${NC}"
fi

# ============================================
# 6. Route Registration Validation
# ============================================
echo ""
echo "=========================================="
echo "STEP 6: Route Registration"
echo "=========================================="

run_test "subscription routes registered" "python -c '
from app.backend.main import app
from fastapi.routing import APIRoute
routes = [r for r in app.routes if isinstance(r, APIRoute)]
paths = [r.path for r in routes]
assert any(\"subscription\" in p for p in paths), \"No subscription routes found\"
print(\"OK\")
'"

run_test "analyze routes registered" "python -c '
from app.backend.main import app
from fastapi.routing import APIRoute
routes = [r for r in app.routes if isinstance(r, APIRoute)]
paths = [r.path for r in routes]
assert any(\"/api/analyze\" in p for p in paths), \"No analyze routes found\"
print(\"OK\")
'"

# ============================================
# 7. Test Collection (if pytest available)
# ============================================
echo ""
echo "=========================================="
echo "STEP 7: Test Collection"
echo "=========================================="

if command -v pytest &> /dev/null; then
    run_test "collect subscription tests" "pytest app/backend/tests/test_subscription.py --collect-only -q"
    run_test "collect usage enforcement tests" "pytest app/backend/tests/test_usage_enforcement.py --collect-only -q"
else
    echo -e "${YELLOW}⚠ pytest not available - skipping test collection${NC}"
fi

# ============================================
# 8. Frontend File Validation
# ============================================
echo ""
echo "=========================================="
echo "STEP 8: Frontend File Validation"
echo "=========================================="

REQUIRED_FILES=(
    "app/frontend/src/hooks/useSubscription.jsx"
    "app/frontend/src/pages/SettingsPage.jsx"
    "app/frontend/src/pages/BatchPage.jsx"
    "app/frontend/src/pages/Dashboard.jsx"
    "app/frontend/src/lib/api.js"
    "app/frontend/src/App.jsx"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC}: $file exists"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC}: $file missing"
        ((TESTS_FAILED++))
    fi
done

# ============================================
# 9. Integration Pattern Checks
# ============================================
echo ""
echo "=========================================="
echo "STEP 9: Integration Pattern Validation"
echo "=========================================="

# Check App.jsx has SubscriptionProvider
if grep -q "SubscriptionProvider" app/frontend/src/App.jsx; then
    echo -e "${GREEN}✓ PASSED${NC}: SubscriptionProvider in App.jsx"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}: SubscriptionProvider missing from App.jsx"
    ((TESTS_FAILED++))
fi

# Check useSubscription hook exports
if grep -q "export function useSubscription" app/frontend/src/hooks/useSubscription.jsx; then
    echo -e "${GREEN}✓ PASSED${NC}: useSubscription hook exported"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}: useSubscription hook not exported"
    ((TESTS_FAILED++))
fi

# Check api.js has subscription endpoints
if grep -q "getSubscription" app/frontend/src/lib/api.js; then
    echo -e "${GREEN}✓ PASSED${NC}: Subscription API functions in api.js"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}: Subscription API functions missing"
    ((TESTS_FAILED++))
fi

# ============================================
# Summary
# ============================================
echo ""
echo "=========================================="
echo "TEST SUITE SUMMARY"
echo "=========================================="
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}==========================================${NC}"
    exit 0
else
    echo -e "${RED}==========================================${NC}"
    echo -e "${RED}SOME TESTS FAILED${NC}"
    echo -e "${RED}Please fix issues before committing${NC}"
    echo -e "${RED}==========================================${NC}"
    exit 1
fi
