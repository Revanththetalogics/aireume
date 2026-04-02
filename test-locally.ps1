# Local Pre-Push Test Script
# Run this before pushing to catch CI/CD errors early

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Local Pre-Push Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$success = $true

# Test 1: Check Python imports work
Write-Host "`n[1/5] Checking Python imports..." -ForegroundColor Yellow
try {
    $env:PYTHONPATH = "."
    python -c "from app.backend.main import app; print('✓ Backend imports OK')" 2>&1 | ForEach-Object { Write-Host $_ }
} catch {
    Write-Host "✗ Backend imports failed: $_" -ForegroundColor Red
    $success = $false
}

# Test 2: Run backend tests
Write-Host "`n[2/5] Running backend tests..." -ForegroundColor Yellow
try {
    $env:PYTHONPATH = "."
    pytest app/backend/tests/ -v 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "Backend tests failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "✗ Backend tests failed: $_" -ForegroundColor Red
    $success = $false
}

# Test 3: Check frontend dependencies install
Write-Host "`n[3/5] Checking frontend dependencies..." -ForegroundColor Yellow
try {
    Set-Location app/frontend
    npm ci --silent 2>&1 | ForEach-Object { Write-Host $_ }
    Set-Location ../..
    Write-Host "✓ Frontend dependencies OK" -ForegroundColor Green
} catch {
    Write-Host "✗ Frontend dependencies failed: $_" -ForegroundColor Red
    $success = $false
}

# Test 4: Run frontend tests
Write-Host "`n[4/5] Running frontend tests..." -ForegroundColor Yellow
try {
    Set-Location app/frontend
    npm test 2>&1 | ForEach-Object { Write-Host $_ }
    Set-Location ../..
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend tests failed"
    }
} catch {
    Write-Host "✗ Frontend tests failed: $_" -ForegroundColor Red
    $success = $false
}

# Test 5: Build frontend
Write-Host "`n[5/5] Building frontend..." -ForegroundColor Yellow
try {
    Set-Location app/frontend
    npm run build 2>&1 | ForEach-Object { Write-Host $_ }
    Set-Location ../..
    Write-Host "✓ Frontend build OK" -ForegroundColor Green
} catch {
    Write-Host "✗ Frontend build failed: $_" -ForegroundColor Red
    $success = $false
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
if ($success) {
    Write-Host "  ✓ ALL TESTS PASSED!" -ForegroundColor Green
    Write-Host "  Safe to push to GitHub" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "  ✗ SOME TESTS FAILED" -ForegroundColor Red
    Write-Host "  Fix errors before pushing" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    exit 1
}
