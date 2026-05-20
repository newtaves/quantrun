@echo off
setlocal enabledelayedexpansion

REM 1. Configure paths
set PYTHON_BIN=.venv\Scripts\python.exe
set NPM_BIN=npm.cmd

echo Cleaning up ports 8000, 8001, 5173...

REM Kill processes using required ports
for %%P in (8000 8001 5173) do (
    for /f "tokens=5" %%A in ('netstat -aon ^| findstr :%%P ^| findstr LISTENING') do (
        taskkill /F /PID %%A >nul 2>&1
    )
)

REM 2. Start services concurrently
echo Starting quantrun...

start "Django" cmd /k "%PYTHON_BIN% quantrun/manage.py runserver 8000"

start "FastAPI" cmd /k "%PYTHON_BIN% -m uvicorn paper.main:app --port 8001 --reload"

start "Frontend" cmd /k "%NPM_BIN% --prefix frontend run dev"

echo All services started.