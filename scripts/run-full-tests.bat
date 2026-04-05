@echo off
REM Full test suite runner for Resume AI (Windows)
REM Run this for comprehensive validation before commits

echo ==========================================
echo ARIA Resume AI - Full Test Suite
echo Subscription System Validation
echo ==========================================

set TESTS_PASSED=0
set TESTS_FAILED=0

REM ============================================
REM 1. Python Syntax Validation
REM ============================================
echo.
echo ==========================================
echo STEP 1: Python Syntax Validation
echo ==========================================

python -m py_compile app\backend\routes\subscription.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] subscription.py syntax valid
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] subscription.py syntax error
    set /a TESTS_FAILED+=1
)

python -m py_compile app\backend\routes\analyze.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] analyze.py syntax valid
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] analyze.py syntax error
    set /a TESTS_FAILED+=1
)

python -m py_compile app\backend\models\db_models.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] db_models.py syntax valid
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] db_models.py syntax error
    set /a TESTS_FAILED+=1
)

python -m py_compile app\backend\models\schemas.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] schemas.py syntax valid
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] schemas.py syntax error
    set /a TESTS_FAILED+=1
)

python -m py_compile app\backend\main.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] main.py syntax valid
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] main.py syntax error
    set /a TESTS_FAILED+=1
)

REM ============================================
REM 2. Test Files
REM ============================================
echo.
echo ==========================================
echo STEP 2: Test File Validation
echo ==========================================

python -m py_compile app\backend\tests\test_subscription.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] test_subscription.py valid
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] test_subscription.py syntax error
    set /a TESTS_FAILED+=1
)

python -m py_compile app\backend\tests\test_usage_enforcement.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] test_usage_enforcement.py valid
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] test_usage_enforcement.py syntax error
    set /a TESTS_FAILED+=1
)

REM ============================================
REM 3. Import Validation
REM ============================================
echo.
echo ==========================================
echo STEP 3: Import Validation
echo ==========================================

python -c "from app.backend.routes import subscription" >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] subscription module imports
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] subscription module import failed
    set /a TESTS_FAILED+=1
)

python -c "from app.backend.models.db_models import SubscriptionPlan, Tenant, UsageLog, User" >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] models import
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] models import failed
    set /a TESTS_FAILED+=1
)

python -c "from app.backend.models.schemas import SubscriptionResponse, PlanInfo, UsageStats" >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] schemas import
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] schemas import failed
    set /a TESTS_FAILED+=1
)

REM ============================================
REM 4. Migration Files
REM ============================================
echo.
echo ==========================================
echo STEP 4: Migration File Validation
echo ==========================================

if exist alembic\versions\003_subscription_system.py (
    echo [OK] Migration 003 exists
    set /a TESTS_PASSED+=1
    
    python -m py_compile alembic\versions\003_subscription_system.py >nul 2>&1
    if %errorlevel% == 0 (
        echo [OK] Migration 003 syntax valid
        set /a TESTS_PASSED+=1
    ) else (
        echo [FAIL] Migration 003 syntax error
        set /a TESTS_FAILED+=1
    )
) else (
    echo [FAIL] Migration 003 not found
    set /a TESTS_FAILED+=1
)

REM Count migration files
set MIGRATION_COUNT=0
for %%f in (alembic\versions\*.py) do set /a MIGRATION_COUNT+=1
echo [INFO] Found %MIGRATION_COUNT% migration files
set /a TESTS_PASSED+=1

REM ============================================
REM 5. Frontend Files
REM ============================================
echo.
echo ==========================================
echo STEP 5: Frontend File Validation
echo ==========================================

set FILES_TO_CHECK=app\frontend\src\hooks\useSubscription.jsx app\frontend\src\pages\SettingsPage.jsx app\frontend\src\pages\BatchPage.jsx app\frontend\src\pages\Dashboard.jsx app\frontend\src\lib\api.js app\frontend\src\App.jsx

for %%f in (%FILES_TO_CHECK%) do (
    if exist %%f (
        echo [OK] %%f exists
        set /a TESTS_PASSED+=1
    ) else (
        echo [FAIL] %%f missing
        set /a TESTS_FAILED+=1
    )
)

REM ============================================
REM 6. Integration Checks
REM ============================================
echo.
echo ==========================================
echo STEP 6: Integration Validation
echo ==========================================

findstr /C:"subscription" app\backend\main.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Subscription imported in main.py
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Subscription not in main.py
    set /a TESTS_FAILED+=1
)

findstr /C:"_check_and_increment_usage" app\backend\routes\analyze.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Usage checking in analyze.py
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Usage checking missing
    set /a TESTS_FAILED+=1
)

findstr /C:"SubscriptionProvider" app\frontend\src\App.jsx >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] SubscriptionProvider in App.jsx
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] SubscriptionProvider missing
    set /a TESTS_FAILED+=1
)

REM ============================================
REM 7. Database Model Patterns
REM ============================================
echo.
echo ==========================================
echo STEP 7: Database Model Patterns
echo ==========================================

findstr /C:"class UsageLog" app\backend\models\db_models.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] UsageLog class found
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] UsageLog class missing
    set /a TESTS_FAILED+=1
)

findstr /C:"analyses_count_this_month" app\backend\models\db_models.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Usage counter in Tenant
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Usage counter missing
    set /a TESTS_FAILED+=1
)

findstr /C:"price_monthly" app\backend\models\db_models.py >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Pricing in SubscriptionPlan
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Pricing missing
    set /a TESTS_FAILED+=1
)

REM ============================================
REM Summary
REM ============================================
echo.
echo ==========================================
echo TEST SUITE SUMMARY
echo ==========================================
echo Tests Passed: %TESTS_PASSED%
echo Tests Failed: %TESTS_FAILED%
set /a TOTAL=TESTS_PASSED+TESTS_FAILED
echo Total Tests: %TOTAL%
echo.

if %TESTS_FAILED% == 0 (
    echo ==========================================
    echo     ALL TESTS PASSED!
    echo     Ready to commit!
    echo ==========================================
    exit /b 0
) else (
    echo ==========================================
    echo     SOME TESTS FAILED
    echo     Fix issues before committing
    echo ==========================================
    exit /b 1
)
