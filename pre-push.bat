@echo off
REM Pre-push test script - run this manually before pushing
REM Or use: git config core.hooksPath .githooks

echo ========================================
echo   Running Pre-Push Tests
echo ========================================

powershell -ExecutionPolicy Bypass -File test-locally.ps1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo TESTS FAILED - Push aborted
    echo Fix the errors above, then try again
    exit /b 1
)

echo.
echo ========================================
echo   ALL TESTS PASSED - Ready to push!
echo ========================================
exit /b 0
