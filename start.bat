@echo off
echo Starting QuantRun...
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.

start "QuantRun API" cmd /c "cd /d %~dp0 && python -m uvicorn server:app --reload --port 8000"
start "QuantRun UI" cmd /c "cd /d %~dp0\frontend && npm run dev"

echo Both servers started. Close this window or press Ctrl+C to stop.
pause
