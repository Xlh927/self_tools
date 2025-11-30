#!/bin/bash

# Kill existing processes on ports 5000 and 8080 if any
lsof -ti:5000 | xargs kill -9 2>/dev/null
lsof -ti:8080 | xargs kill -9 2>/dev/null

# Start Flask backend
echo "Starting Backend..."
python3 backend/app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start Frontend dev server
echo "Starting Frontend..."
python3 dev_server.py 8080 &
FRONTEND_PID=$!

echo "✅ Servers started!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "👉 Open http://localhost:8080 to view the app"

# Wait for user to press Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
