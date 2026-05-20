#!/bin/bash

# 1. Detect OS and configure pathing/port sweep
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
  PYTHON_BIN=".venv/Scripts/python"
  NPM_BIN="npm.cmd"
  echo "cleaning up ports 8000, 8001, 5173..."
  for port in 8000 8001 5173; do
    PID=$(netstat -aon | grep -i "listening" | grep ":$port" | awk '{print $5}')
    if [ -n "$PID" ]; then
      taskkill -F -PID $PID 2>/dev/null || true
    fi
  done
else
  PYTHON_BIN=".venv/bin/python"
  NPM_BIN="npm"
  echo "cleaning up ports 8000, 8001, 5173..."
  kill -9 $(lsof -t -i:8000) 2>/dev/null || true
  kill -9 $(lsof -t -i:8001) 2>/dev/null || true
  kill -9 $(lsof -t -i:5173) 2>/dev/null || true
fi

# 2. Start services concurrently
echo "starting quantrun"
$PYTHON_BIN quantrun/manage.py runserver 8000 &
$PYTHON_BIN -m uvicorn paper.main:app --port 8001 --reload &
$NPM_BIN --prefix frontend run dev &

wait
