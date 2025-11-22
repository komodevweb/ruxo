@echo off
REM Script to run monthly credit reset
REM This can be used with Windows Task Scheduler

REM Get the backend directory (parent of scripts directory)
cd /d %~dp0..

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set PYTHONPATH to backend directory (helps with imports)
set PYTHONPATH=%CD%

REM Run the script
python scripts/reset_monthly_credits.py

REM Keep window open if there's an error (for debugging)
if errorlevel 1 (
    echo.
    echo Script failed with error code %errorlevel%
    pause
)

