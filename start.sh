#!/bin/bash
echo "Starting QuantRun..."
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""

cd "$(dirname "$0")"

python -m uvicorn server:app --reload --port 8000 &
SERVER_PID=$!

cd frontend
npm run dev &
UI_PID=$!

trap "kill $SERVER_PID $UI_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
