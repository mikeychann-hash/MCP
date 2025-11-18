@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM MCP Runtime v3.0 - Development Mode Script
REM ============================================================================
REM Runs the server in development mode with hot-reload and debugging
REM ============================================================================

echo.
echo ========================================
echo MCP Runtime v3.0 - Development Mode
echo ========================================
echo.

REM ----------------------------------------------------------------------------
REM Check Prerequisites
REM ----------------------------------------------------------------------------
echo [1/3] Checking prerequisites...

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed
    echo [ERROR] Please run install.bat first
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

if not exist "src\index.ts" (
    echo [ERROR] Source code not found in src\
    pause
    exit /b 1
)
echo [OK] Source code found

echo.

REM ----------------------------------------------------------------------------
REM Check Redis/Memurai
REM ----------------------------------------------------------------------------
echo [2/3] Checking Redis/Memurai...

sc query Memurai >nul 2>&1
if errorlevel 1 (
    sc query Redis >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Redis/Memurai not running
        echo [INFO] Memory features will be disabled
        echo [INFO] Install Memurai from https://www.memurai.com/
    ) else (
        sc query Redis | find "RUNNING" >nul
        if errorlevel 1 (
            echo [INFO] Redis service found but not running
            echo [INFO] Attempting to start Redis...
            net start Redis >nul 2>&1
            if errorlevel 1 (
                echo [WARN] Could not start Redis
            ) else (
                echo [OK] Redis started
            )
        ) else (
            echo [OK] Redis is running
        )
    )
) else (
    sc query Memurai | find "RUNNING" >nul
    if errorlevel 1 (
        echo [INFO] Memurai service found but not running
        echo [INFO] Attempting to start Memurai...
        net start Memurai >nul 2>&1
        if errorlevel 1 (
            echo [WARN] Could not start Memurai
        ) else (
            echo [OK] Memurai started
        )
    ) else (
        echo [OK] Memurai is running
    )
)

echo.

REM ----------------------------------------------------------------------------
REM Start Development Server
REM ----------------------------------------------------------------------------
echo [3/3] Starting development server...
echo.
echo ========================================
echo Development Mode Active
echo ========================================
echo.
echo Features:
echo   - Auto-reload on file changes
echo   - TypeScript compilation on-the-fly
echo   - Source maps enabled
echo   - Detailed error messages
echo.
echo Press Ctrl+C to stop
echo.
echo ========================================
echo.

REM Set development environment variables
set NODE_ENV=development
set NODE_OPTIONS=--enable-source-maps
set DEBUG=true

REM Start development server with tsx watch
npm run dev

REM Capture exit code
set EXIT_CODE=%errorlevel%

echo.
echo ========================================
if %EXIT_CODE% EQU 0 (
    echo Development server stopped
) else (
    echo Development server exited with error: %EXIT_CODE%
)
echo ========================================
echo.

endlocal
exit /b %EXIT_CODE%
