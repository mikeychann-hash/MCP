@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM MCP Runtime v3.0 - One-Time Installation Script
REM ============================================================================
REM This script performs initial setup and installation of all dependencies
REM ============================================================================

echo.
echo ========================================
echo MCP Runtime v3.0 - Installation
echo ========================================
echo.

REM ----------------------------------------------------------------------------
REM 1. Check Prerequisites
REM ----------------------------------------------------------------------------
echo [1/6] Checking prerequisites...

REM Check Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed
    echo.
    echo Please install Node.js 20 or higher from:
    echo https://nodejs.org/
    echo.
    echo After installation, restart this script.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js %NODE_VERSION% detected

REM Check npm
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not installed
    echo [ERROR] npm should come with Node.js
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo [OK] npm %NPM_VERSION% detected

REM Check Git (optional but recommended)
where git >nul 2>&1
if errorlevel 1 (
    echo [WARN] Git is not installed (optional)
    echo [INFO] Git is recommended for version control
    echo [INFO] Download from: https://git-scm.com/
) else (
    for /f "tokens=*" %%i in ('git --version') do echo [OK] %%i
)

echo.

REM ----------------------------------------------------------------------------
REM 2. Clean Previous Installation
REM ----------------------------------------------------------------------------
echo [2/6] Cleaning previous installation...

if exist "node_modules" (
    echo [INFO] Removing old node_modules...
    rmdir /s /q "node_modules" 2>nul
    if exist "node_modules" (
        echo [WARN] Could not remove node_modules completely
        echo [WARN] Some files may be in use - please close all applications
    ) else (
        echo [OK] Old node_modules removed
    )
) else (
    echo [OK] No previous installation found
)

if exist "package-lock.json" (
    echo [INFO] Removing package-lock.json...
    del /q "package-lock.json" 2>nul
    echo [OK] package-lock.json removed
)

if exist "dist" (
    echo [INFO] Removing old build output...
    rmdir /s /q "dist" 2>nul
    echo [OK] Old build output removed
)

echo.

REM ----------------------------------------------------------------------------
REM 3. Install Dependencies
REM ----------------------------------------------------------------------------
echo [3/6] Installing Node.js dependencies...
echo [INFO] This may take several minutes on first install...
echo.

npm install
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies
    echo [ERROR] Please check your internet connection and try again
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Dependencies installed successfully
echo.

REM ----------------------------------------------------------------------------
REM 4. Setup Environment Configuration
REM ----------------------------------------------------------------------------
echo [4/6] Setting up environment configuration...

if exist ".env" (
    echo [WARN] .env file already exists
    echo [INFO] Skipping .env creation to preserve existing configuration
    echo [INFO] Review .env.example for new configuration options
) else (
    if exist ".env.example" (
        echo [INFO] Creating .env from template...
        copy ".env.example" ".env" >nul
        if errorlevel 1 (
            echo [ERROR] Failed to create .env file
        ) else (
            echo [OK] .env file created
            echo [INFO] Please review and customize .env file for your environment
        )
    ) else (
        echo [WARN] .env.example not found
        echo [WARN] You may need to create .env manually
    )
)

echo.

REM ----------------------------------------------------------------------------
REM 5. Build TypeScript
REM ----------------------------------------------------------------------------
echo [5/6] Building TypeScript project...
echo.

npm run build
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed
    echo [ERROR] Please check TypeScript errors above
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Build completed successfully
echo.

REM ----------------------------------------------------------------------------
REM 6. Check Optional Services
REM ----------------------------------------------------------------------------
echo [6/6] Checking optional services...

REM Check for Memurai (Windows Redis alternative)
sc query Memurai >nul 2>&1
if errorlevel 1 (
    echo [INFO] Memurai is not installed
    echo.
    echo [OPTIONAL] For full functionality, install Memurai (Redis for Windows):
    echo   1. Download from: https://www.memurai.com/
    echo   2. Install and start the Memurai service
    echo   3. Server will work without it, but memory features will be disabled
    echo.
) else (
    echo [OK] Memurai is installed

    REM Check if service is running
    sc query Memurai | find "RUNNING" >nul
    if errorlevel 1 (
        echo [INFO] Memurai service is not running
        echo [INFO] Attempting to start Memurai service...
        net start Memurai >nul 2>&1
        if errorlevel 1 (
            echo [WARN] Could not start Memurai service
            echo [WARN] You may need to run this script as Administrator
        ) else (
            echo [OK] Memurai service started
        )
    ) else (
        echo [OK] Memurai service is running
    )
)

echo.

REM ----------------------------------------------------------------------------
REM Installation Complete
REM ----------------------------------------------------------------------------
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Review and customize .env file
echo   2. Run 'start.bat' to start the MCP server
echo   3. Run 'dev.bat' for development mode with auto-reload
echo   4. Run 'test.bat' to run tests
echo.
echo For Claude Desktop integration:
echo   1. Review claude-desktop-config-example.json
echo   2. Update your Claude Desktop configuration
echo.
echo For Claude CLI integration:
echo   1. Review claude-cli-config-example.json
echo   2. Update your Claude CLI configuration
echo.
echo Documentation: See README-SETUP.md for detailed instructions
echo.

pause
endlocal
exit /b 0
