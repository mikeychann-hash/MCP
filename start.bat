@echo off
setlocal

rem Ensure the Memurai (Redis-compatible) service is running before starting the MCP server
sc query Memurai | find "RUNNING" >nul
if errorlevel 1 (
    echo Starting Memurai service...
    net start Memurai >nul
) else (
    echo Memurai service already running.
)

set "PYTHON=C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe"
set "SCRIPT=C:\Users\Admin\Documents\mcp_runtime_v3\server.py"

if not exist "%PYTHON%" (
    echo Python interpreter not found: %PYTHON%
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo Server script not found: %SCRIPT%
    exit /b 1
)

pushd C:\Users\Admin\Documents\mcp_runtime_v3
echo Launching MCP server...
"%PYTHON%" "%SCRIPT%"
popd

endlocal
