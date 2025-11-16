@echo off
setlocal enableextensions enabledelayedexpansion

rem === CONFIG ===
set "PYTHON=C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe"
set "SERVER=C:\Users\Admin\Documents\mcp_runtime_v3\server.py"
set "WORKDIR=C:\Users\Admin\Documents\mcp_runtime_v3"
set "LOGDIR=%WORKDIR%\logs"
set "PIDFILE=%WORKDIR%\server.pid"

rem --- Environment used by the server ---
set "PYTHONUNBUFFERED=1"
set "MCP_RUNTIME_ALLOW_SHELL=false"
set "MCP_MEMORY_REDIS_HOST=localhost"
set "MCP_MEMORY_REDIS_PORT=6379"
set "MCP_MEMORY_REDIS_DB=5"
set "MCP_RUNTIME_PROJECT_ROOT=%WORKDIR%"

if not exist "%PYTHON%" (
  echo [ERROR] Python not found: %PYTHON%
  exit /b 1
)
if not exist "%SERVER%" (
  echo [ERROR] Server script not found: %SERVER%
  exit /b 1
)

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

rem === Check if already running (python.exe with our server path) ===
for /f "tokens=2 delims=," %%P in ('powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process ^| Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match [regex]::Escape('%SERVER%') } ^| Select-Object -ExpandProperty ProcessId ^| ForEach-Object { $_ } ^| Write-Output"') do (
  set "FOUND_PID=%%P"
)

if defined FOUND_PID (
  echo [INFO] MCP server already running (PID !FOUND_PID!).
  exit /b 0
)

rem === Rotate log filename by timestamp ===
for /f "tokens=1-5 delims=/:. " %%a in ("%date% %time%") do (
  set "STAMP=%%c%%a%%b_%%d%%e"
)
set "LOGFILE=%LOGDIR%\server_%STAMP%.log"

echo [INFO] Launching MCP Runtime v3...
echo [INFO]   PYTHON: %PYTHON%
echo [INFO]   SERVER: %SERVER%
echo [INFO]   LOG:    %LOGFILE%

pushd "%WORKDIR%"

rem === Start via PowerShell to capture PID and restart once on crash ===
powershell -NoProfile -Command ^
  "$env:PYTHONUNBUFFERED=$env:PYTHONUNBUFFERED; ^
   $env:MCP_RUNTIME_ALLOW_SHELL=$env:MCP_RUNTIME_ALLOW_SHELL; ^
   $env:MCP_MEMORY_REDIS_HOST=$env:MCP_MEMORY_REDIS_HOST; ^
   $env:MCP_MEMORY_REDIS_PORT=$env:MCP_MEMORY_REDIS_PORT; ^
   $env:MCP_MEMORY_REDIS_DB=$env:MCP_MEMORY_REDIS_DB; ^
   $env:MCP_RUNTIME_PROJECT_ROOT=$env:MCP_RUNTIME_PROJECT_ROOT; ^
   $py = '%PYTHON%'; $srv = '%SERVER%'; $log = '%LOGFILE%'; ^
   function Start-Once { ^
     $p = Start-Process -FilePath $py -ArgumentList @($srv) -WorkingDirectory '%WORKDIR%' -RedirectStandardOutput $log -RedirectStandardError $log -PassThru; ^
     Set-Content -Path '%PIDFILE%' -Value $p.Id; ^
     $p.WaitForExit(); ^
     return $p.ExitCode ^
   } ^
   $code = Start-Once; ^
   if ($code -ne 0) { ^
      Write-Host '[WARN] Server exited with code ' $code ', retrying once in 3s...'; ^
      Start-Sleep -Seconds 3; ^
      $code = Start-Once; ^
   } ^
   exit $code"

set "RC=%ERRORLEVEL%"
if exist "%PIDFILE%" del "%PIDFILE%" >nul 2>&1

popd

if "%RC%"=="0" (
  echo [INFO] Server process finished normally.
) else (
  echo [ERROR] Server process exited with %RC%.
)

exit /b %RC%
