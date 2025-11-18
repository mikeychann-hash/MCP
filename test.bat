@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM MCP Runtime v3.0 - Test Runner Script
REM ============================================================================
REM Runs unit tests with Vitest
REM ============================================================================

echo.
echo ========================================
echo MCP Runtime v3.0 - Test Runner
echo ========================================
echo.

REM ----------------------------------------------------------------------------
REM Check Prerequisites
REM ----------------------------------------------------------------------------
echo [1/2] Checking prerequisites...

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed
    pause
    exit /b 1
)
echo [OK] Node.js found

if not exist "node_modules" (
    echo [ERROR] Dependencies not installed
    echo [ERROR] Please run install.bat first
    pause
    exit /b 1
)
echo [OK] Dependencies installed

echo.

REM ----------------------------------------------------------------------------
REM Run Tests
REM ----------------------------------------------------------------------------
echo [2/2] Running tests...
echo.

REM Check if user wants coverage
set RUN_COVERAGE=0
if "%1"=="--coverage" set RUN_COVERAGE=1
if "%1"=="-c" set RUN_COVERAGE=1

if %RUN_COVERAGE%==1 (
    echo [INFO] Running tests with coverage...
    echo.
    npm run test:coverage
) else (
    echo [INFO] Running tests...
    echo [INFO] Use 'test.bat --coverage' to generate coverage report
    echo.
    npm run test:run
)

set EXIT_CODE=%errorlevel%

echo.

REM ----------------------------------------------------------------------------
REM Test Summary
REM ----------------------------------------------------------------------------
if %EXIT_CODE% EQU 0 (
    echo ========================================
    echo All Tests Passed!
    echo ========================================
    echo.

    if %RUN_COVERAGE%==1 (
        echo Coverage report generated in: coverage\
        echo Open coverage\index.html in your browser to view detailed report
        echo.
    )
) else (
    echo ========================================
    echo Tests Failed
    echo ========================================
    echo.
    echo Please review the errors above and fix failing tests
    echo.
)

REM Offer to open coverage report
if %RUN_COVERAGE%==1 (
    if exist "coverage\index.html" (
        set /p OPEN_COVERAGE="Open coverage report in browser? (y/N): "
        if /i "!OPEN_COVERAGE!"=="y" (
            start "" "coverage\index.html"
        )
    )
)

endlocal
exit /b %EXIT_CODE%
