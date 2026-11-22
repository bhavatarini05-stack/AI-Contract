@echo off
REM Starts the AI Contract Analyzer frontend (Vite prints the URL to open)
cd /d "%~dp0frontend"
if not exist "node_modules" (
  echo Installing frontend dependencies...
  call npm install || goto :error
)
call npm run dev
goto :eof

:error
echo Setup failed. Make sure Node.js 18+ is installed and on PATH.
pause
