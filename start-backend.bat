@echo off
REM Starts the AI Contract Analyzer backend on http://localhost:8000
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment and installing dependencies...
  python -m venv .venv || goto :error
  ".venv\Scripts\python.exe" -m pip install -e ".[dev]" || goto :error
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
goto :eof

:error
echo Setup failed. Make sure Python 3.11+ is installed and on PATH.
pause
