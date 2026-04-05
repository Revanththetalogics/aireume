# ============================================================
#  Local Pre-Push Test Script
#  Run before pushing to catch CI/CD errors early.
#  Usage:  .\test-locally.ps1
# ============================================================

# Always use absolute paths so directory changes can never drift
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$FRONTEND = Join-Path $ROOT "app\frontend"

$passed  = 0
$failed  = 0
$results = @()

function Step-Header($n, $label) {
    Write-Host ""
    Write-Host "[$n/5] $label" -ForegroundColor Yellow
}

function Step-Pass($msg) {
    Write-Host "  PASS  $msg" -ForegroundColor Green
    $script:passed++
    $script:results += @{ ok = $true; msg = $msg }
}

function Step-Fail($msg) {
    Write-Host "  FAIL  $msg" -ForegroundColor Red
    $script:failed++
    $script:results += @{ ok = $false; msg = $msg }
}

Write-Host "======================================================="
Write-Host "  ARIA - Local Pre-Push Test Suite"
Write-Host "======================================================="

# ─── Step 1: Python imports ───────────────────────────────────
Step-Header 1 "Checking Python imports..."
Set-Location $ROOT
$env:PYTHONPATH = $ROOT

$importOut = python -c "from app.backend.main import app; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Step-Pass "Backend imports OK"
} else {
    Step-Fail "Backend import error: $importOut"
}

# ─── Step 2: Backend tests ────────────────────────────────────
Step-Header 2 "Running backend pytest suite..."
Set-Location $ROOT
$env:PYTHONPATH = $ROOT

# Run pytest; suppress warnings to avoid false stderr exits
python -m pytest app/backend/tests/ -v --tb=short -q --no-header 2>&1 | ForEach-Object { Write-Host "  $_" }
if ($LASTEXITCODE -eq 0) {
    Step-Pass "All backend tests passed"
} else {
    Step-Fail "Backend tests failed (exit $LASTEXITCODE)"
}

# ─── Step 3: Frontend dependencies ───────────────────────────
# Use npm install instead of npm ci to avoid EPERM errors on Windows
# when binary executables (esbuild.exe, rollup.node) are locked by
# a running dev server process.
Step-Header 3 "Checking frontend dependencies (npm install)..."
Set-Location $FRONTEND

npm install --prefer-offline --silent 2>&1 | ForEach-Object { Write-Host "  $_" }
if ($LASTEXITCODE -eq 0) {
    Step-Pass "Frontend dependencies OK"
} else {
    Step-Fail "npm install failed (exit $LASTEXITCODE)"
}

# ─── Step 4: Frontend tests ───────────────────────────────────
Step-Header 4 "Running frontend vitest suite..."
Set-Location $FRONTEND

# --run exits after one pass (no watch mode)
npm test -- --run 2>&1 | ForEach-Object { Write-Host "  $_" }
if ($LASTEXITCODE -eq 0) {
    Step-Pass "All frontend tests passed"
} else {
    Step-Fail "Frontend tests failed (exit $LASTEXITCODE)"
}

# ─── Step 5: Frontend build ───────────────────────────────────
Step-Header 5 "Building frontend (vite build)..."
Set-Location $FRONTEND

npm run build 2>&1 | ForEach-Object { Write-Host "  $_" }
if ($LASTEXITCODE -eq 0) {
    Step-Pass "Frontend build succeeded"
} else {
    Step-Fail "Frontend build failed (exit $LASTEXITCODE)"
}

# ─── Summary ──────────────────────────────────────────────────
Set-Location $ROOT
Write-Host ""
Write-Host "======================================================="
Write-Host "  Results: $passed passed, $failed failed"
Write-Host "======================================================="

foreach ($r in $results) {
    $icon  = if ($r.ok) { "OK " } else { "XX " }
    $color = if ($r.ok) { "Green" } else { "Red" }
    Write-Host "  $icon  $($r.msg)" -ForegroundColor $color
}

Write-Host "======================================================="
if ($failed -eq 0) {
    Write-Host "  ALL CHECKS PASSED - Safe to push!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  $failed CHECKS FAILED - Fix before pushing." -ForegroundColor Red
    exit 1
}
