@echo off
setlocal
cd /d "%~dp0"

set "PORT=4173"
set "URL=http://127.0.0.1:%PORT%/"
set "GORGON_PORT=%PORT%"
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

where py >nul 2>&1
if not errorlevel 1 goto use_py

where python >nul 2>&1
if not errorlevel 1 goto use_python

if exist "%CODEX_PY%" goto use_codex_python

echo.
echo Could not find Python.
echo Install Python from https://www.python.org/downloads/ and try again.
echo.
pause
exit /b 1

:open_site
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Milliseconds 900; Start-Process '%URL%'"
echo.
echo Gorgon Ledger is running at %URL%
echo Keep this window open. Press Ctrl+C to stop the server.
echo.
exit /b 0

:use_py
call :open_site
py server.py
goto finished

:use_python
call :open_site
python server.py
goto finished

:use_codex_python
call :open_site
"%CODEX_PY%" server.py

:finished
echo.
echo Server stopped.
pause
