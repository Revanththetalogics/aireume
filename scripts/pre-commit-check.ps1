# Pre-commit validation script for Resume AI
# Run this before committing to ensure code quality

param(
    [switch]$SkipMigrations,
    [switch]$SkipTests,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$startTime = Get-Date

$exitCode = 0

function Write-Header($message) {
    Write-Host ""
    Write-Host "========================================"
    Write-Host $message
    Write-Host "========================================"
}

Write-Host ""
Write-Host "ARIA Resume AI - Pre-Commit Validation"
Write-Host "======================================"
Write-Host ""

# Step 1: Python Syntax
Write-Header "STEP 1: Python Syntax Validation"

$files = @(
    "app\backend\routes\subscription.py",
    "app\backend\routes\analyze.py", 
    "app\backend\models\db_models.py",
    "app\backend\models\schemas.py",
    "app\backend\main.py"
)

foreach ($file in $files) {
    Write-Host "Checking $file ..."
    python -m py_compile $file 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Valid syntax" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Syntax error" -ForegroundColor Red
        $exitCode = 1
    }
}

# Step 2: Test Files
Write-Header "STEP 2: Test File Validation"

$testFiles = @(
    "app\backend\tests\test_subscription.py",
    "app\backend\tests\test_usage_enforcement.py"
)

foreach ($file in $testFiles) {
    if (Test-Path $file) {
        Write-Host "Found $file" -ForegroundColor Green
        python -m py_compile $file 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Valid syntax" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Syntax error" -ForegroundColor Red
            $exitCode = 1
        }
    } else {
        Write-Host "[WARN] $file not found" -ForegroundColor Yellow
    }
}

# Step 3: Migrations
Write-Header "STEP 3: Migration Files"

$migrations = Get-ChildItem -Path "alembic\versions" -Filter "*.py" 2>&1
if ($migrations) {
    Write-Host "[OK] Found $($migrations.Count) migration files" -ForegroundColor Green
    foreach ($m in $migrations | Select-Object -Last 3) {
        Write-Host "  - $($m.Name)"
    }
} else {
    Write-Host "[WARN] No migrations found" -ForegroundColor Yellow
}

if (Test-Path "alembic\versions\003_subscription_system.py") {
    Write-Host "[OK] Migration 003 exists" -ForegroundColor Green
} else {
    Write-Host "[WARN] Migration 003 not found" -ForegroundColor Yellow
}

# Step 4: Frontend Files
Write-Header "STEP 4: Frontend Files"

$frontendFiles = @(
    "app\frontend\src\hooks\useSubscription.jsx",
    "app\frontend\src\pages\SettingsPage.jsx",
    "app\frontend\src\pages\BatchPage.jsx",
    "app\frontend\src\pages\Dashboard.jsx",
    "app\frontend\src\lib\api.js",
    "app\frontend\src\App.jsx"
)

$frontendOk = $true
foreach ($file in $frontendFiles) {
    if (Test-Path $file) {
        Write-Host "[OK] $file" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Missing: $file" -ForegroundColor Red
        $frontendOk = $false
        $exitCode = 1
    }
}

# Step 5: Check Integration
Write-Header "STEP 5: Integration Checks"

$mainPy = Get-Content "app\backend\main.py" -Raw
if ($mainPy -match "subscription") {
    Write-Host "[OK] Subscription imported in main.py" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Subscription not in main.py" -ForegroundColor Red
    $exitCode = 1
}

$analyzePy = Get-Content "app\backend\routes\analyze.py" -Raw
if ($analyzePy -match "_check_and_increment_usage") {
    Write-Host "[OK] Usage checking in analyze.py" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Usage checking missing" -ForegroundColor Red
    $exitCode = 1
}

$appJsx = Get-Content "app\frontend\src\App.jsx" -Raw
if ($appJsx -match "SubscriptionProvider") {
    Write-Host "[OK] SubscriptionProvider in App.jsx" -ForegroundColor Green
} else {
    Write-Host "[FAIL] SubscriptionProvider missing" -ForegroundColor Red
    $exitCode = 1
}

# Step 6: Model Checks
Write-Header "STEP 6: Database Models"

$dbModels = Get-Content "app\backend\models\db_models.py" -Raw

$checks = @(
    @{ Pattern = "class UsageLog"; Desc = "UsageLog class" }
    @{ Pattern = "class SubscriptionPlan"; Desc = "SubscriptionPlan class" }
    @{ Pattern = "analyses_count_this_month"; Desc = "Usage counter in Tenant" }
    @{ Pattern = "price_monthly"; Desc = "Pricing in SubscriptionPlan" }
    @{ Pattern = "features"; Desc = "Features in SubscriptionPlan" }
)

foreach ($check in $checks) {
    if ($dbModels -match $check.Pattern) {
        Write-Host "[OK] $($check.Desc)" -ForegroundColor Green
    } else {
        Write-Host "[WARN] $($check.Desc) not found" -ForegroundColor Yellow
    }
}

# Step 7: Summary
Write-Header "SUMMARY"

$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host "Duration: $([math]::Round($duration.TotalSeconds, 2)) seconds"
Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "     ALL CHECKS PASSED" -ForegroundColor Green
    Write-Host "     Ready to commit!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "     SOME CHECKS FAILED" -ForegroundColor Red
    Write-Host "     Fix errors before committing" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
}

exit $exitCode
