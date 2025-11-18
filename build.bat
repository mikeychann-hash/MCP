@echo off
setlocal EnableDelayedExpansion

REM ============================================================================
REM MCP Runtime v3.0 - TypeScript Build Script
REM ============================================================================
REM Compiles TypeScript source code to JavaScript
REM ============================================================================

echo.
echo ========================================
echo MCP Runtime v3.0 - Build
echo ========================================
echo.

REM ----------------------------------------------------------------------------
REM Check Prerequisites
REM ----------------------------------------------------------------------------
echo [1/4] Checking prerequisites...

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

if not exist "tsconfig.json" (
    echo [ERROR] tsconfig.json not found
    pause
    exit /b 1
)
echo [OK] TypeScript configuration found

echo.

REM ----------------------------------------------------------------------------
REM Clean Previous Build
REM ----------------------------------------------------------------------------
echo [2/4] Cleaning previous build...

if exist "dist" (
    echo [INFO] Removing old build output...
    rmdir /s /q "dist" 2>nul
    if exist "dist" (
        echo [WARN] Could not remove dist folder completely
        echo [WARN] Some files may be in use
    ) else (
        echo [OK] Old build removed
    )
) else (
    echo [OK] No previous build found
)

echo.

REM ----------------------------------------------------------------------------
REM Type Check
REM ----------------------------------------------------------------------------
echo [3/4] Running TypeScript type checking...
echo.

npm run typecheck
if errorlevel 1 (
    echo.
    echo [ERROR] Type checking failed
    echo [ERROR] Please fix TypeScript errors above
    echo.

    set /p CONTINUE="Continue with build anyway? (y/N): "
    if /i not "!CONTINUE!"=="y" (
        echo [INFO] Build cancelled
        pause
        exit /b 1
    )
)

echo.
echo [OK] Type checking passed
echo.

REM ----------------------------------------------------------------------------
REM Compile TypeScript
REM ----------------------------------------------------------------------------
echo [4/4] Compiling TypeScript...
echo.

npm run build
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed
    echo [ERROR] Please check errors above
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Build completed successfully
echo.

REM ----------------------------------------------------------------------------
REM Build Summary
REM ----------------------------------------------------------------------------
echo ========================================
echo Build Summary
echo ========================================
echo.

if exist "dist\index.js" (
    echo [OK] Main entry point: dist\index.js
) else (
    echo [WARN] Main entry point not found
)

REM Count generated files
set FILE_COUNT=0
for /r "dist" %%f in (*.js) do set /a FILE_COUNT+=1
echo [INFO] Generated files: %FILE_COUNT% JavaScript files

REM Check for declaration files
if exist "dist\index.d.ts" (
    echo [OK] Type declarations generated
) else (
    echo [WARN] Type declarations not found
)

REM Check for source maps
if exist "dist\index.js.map" (
    echo [OK] Source maps generated
) else (
    echo [WARN] Source maps not found
)

echo.
echo Build output directory: dist\
echo.
echo Next steps:
echo   - Run 'start.bat' to start the server
echo   - Run 'npm start' to start without checks
echo   - Run 'dev.bat' for development mode
echo.

endlocal
exit /b 0
