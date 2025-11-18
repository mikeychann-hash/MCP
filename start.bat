@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM MCP Runtime v3.0 - Production Startup Script
REM ============================================================================
REM This script performs comprehensive checks and starts the MCP server
REM with proper error handling and logging.
REM ============================================================================

echo.
echo ========================================
echo MCP Runtime v3.0 - Server Startup
echo ========================================
echo.

REM ----------------------------------------------------------------------------
REM 1. Check Node.js Installation
REM ----------------------------------------------------------------------------
echo [1/7] Checking Node.js installation...
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo.
    echo Please install Node.js 20 or higher from:
    echo https://nodejs.org/
    echo.
    pause
    exit /b 1
)

REM Check Node.js version
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js version: %NODE_VERSION%

REM Extract major version number (remove 'v' prefix)
set NODE_VERSION_NUM=%NODE_VERSION:~1%
for /f "tokens=1 delims=." %%a in ("%NODE_VERSION_NUM%") do set NODE_MAJOR=%%a

if %NODE_MAJOR% LSS 20 (
    echo [ERROR] Node.js version must be 20 or higher
    echo [ERROR] Current version: %NODE_VERSION%
    echo.
    echo Please upgrade Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM ----------------------------------------------------------------------------
REM 2. Check Project Structure
REM ----------------------------------------------------------------------------
echo [2/7] Checking project structure...

if not exist "package.json" (
    echo [ERROR] package.json not found in current directory
    echo [ERROR] Please run this script from the project root
    pause
    exit /b 1
)
echo [OK] package.json found

if not exist "tsconfig.json" (
    echo [ERROR] tsconfig.json not found
    echo [ERROR] Project may not be properly initialized
    pause
    exit /b 1
)
echo [OK] tsconfig.json found

REM ----------------------------------------------------------------------------
REM 3. Check Node Modules
REM ----------------------------------------------------------------------------
echo [3/7] Checking dependencies...

if not exist "node_modules" (
    echo [WARN] node_modules not found - running installation...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
) else (
    echo [OK] node_modules found
)

REM ----------------------------------------------------------------------------
REM 4. Check Build Output
REM ----------------------------------------------------------------------------
echo [4/7] Checking build output...

if not exist "dist\index.js" (
    echo [WARN] Build output not found - running build...
    call npm run build
    if errorlevel 1 (
        echo [ERROR] Build failed
        echo.
        echo Please fix TypeScript errors and try again
        pause
        exit /b 1
    )
) else (
    echo [OK] Build output found
)

REM ----------------------------------------------------------------------------
REM 5. Load Environment Variables
REM ----------------------------------------------------------------------------
echo [5/7] Loading environment configuration...

if exist ".env" (
    echo [OK] .env file found
) else (
    if exist ".env.example" (
        echo [WARN] .env not found - copying from .env.example...
        copy ".env.example" ".env" >nul
        echo [INFO] Please review and customize .env file
    ) else (
        echo [WARN] No .env file found - using defaults
    )
)

REM ----------------------------------------------------------------------------
REM 6. Check Redis/Memurai Service
REM ----------------------------------------------------------------------------
echo [6/7] Checking Redis/Memurai service...

REM Check if Memurai service exists (Windows Redis alternative)
sc query Memurai >nul 2>&1
if errorlevel 1 (
    echo [WARN] Memurai service not found
    echo [INFO] Attempting to check for Redis service...

    REM Check for standard Redis service
    sc query Redis >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Redis/Memurai not installed as Windows service
        echo [INFO] Server will start with Redis features disabled
        echo [INFO] To enable Redis features:
        echo [INFO]   1. Install Memurai from https://www.memurai.com/
        echo [INFO]   2. Or install Redis and start it manually
        echo.
    ) else (
        REM Check if Redis service is running
        sc query Redis | find "RUNNING" >nul
        if errorlevel 1 (
            echo [INFO] Starting Redis service...
            net start Redis >nul 2>&1
            if errorlevel 1 (
                echo [WARN] Failed to start Redis service
                echo [INFO] Server will continue with Redis features disabled
            ) else (
                echo [OK] Redis service started
            )
        ) else (
            echo [OK] Redis service is running
        )
    )
) else (
    REM Check if Memurai is running
    sc query Memurai | find "RUNNING" >nul
    if errorlevel 1 (
        echo [INFO] Starting Memurai service...
        net start Memurai >nul 2>&1
        if errorlevel 1 (
            echo [WARN] Failed to start Memurai service
            echo [INFO] You may need administrator privileges
            echo [INFO] Server will continue with Redis features disabled
        ) else (
            echo [OK] Memurai service started
        )
    ) else (
        echo [OK] Memurai service is running
    )
)

REM ----------------------------------------------------------------------------
REM 7. Start MCP Server
REM ----------------------------------------------------------------------------
echo [7/7] Starting MCP server...
echo.
echo ========================================
echo Server Starting - Press Ctrl+C to stop
echo ========================================
echo.

REM Set Node.js options for better error messages
set NODE_OPTIONS=--enable-source-maps

REM Start the server
node dist/index.js

REM Capture exit code
set EXIT_CODE=%errorlevel%

echo.
echo ========================================
if %EXIT_CODE% EQU 0 (
    echo Server stopped gracefully
) else (
    echo Server exited with error code: %EXIT_CODE%
)
echo ========================================
echo.

endlocal
exit /b %EXIT_CODE%
