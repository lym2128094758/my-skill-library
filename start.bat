@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 (
    python launch.py
    goto finished
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3 launch.py
    goto finished
)
echo Python 3.10 or newer is required. Please install Python and try again.
:finished
pause
