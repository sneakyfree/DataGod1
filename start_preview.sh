#!/bin/bash
# DataGod GOAT Preview Startup Script
# Starts backend on port 5847 to avoid conflicts

set -e

cd "$(dirname "$0")"

echo "========================================"
echo "DataGod GOAT Preview Startup"
echo "========================================"
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found at .venv"
    exit 1
fi

# Check if port is in use
PORT=5847
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️ Port $PORT is in use, killing existing process..."
    kill $(lsof -Pi :$PORT -sTCP:LISTEN -t) 2>/dev/null || true
    sleep 1
fi

# Run seed script if available
if [ -f "scripts/seed_goat_data.py" ]; then
    echo ""
    echo "Running seed script..."
    python scripts/seed_goat_data.py
fi

echo ""
echo "Starting API server on port $PORT..."
echo ""
echo "========================================"
echo "Preview URLs:"
echo "  • API:     http://localhost:$PORT"
echo "  • Docs:    http://localhost:$PORT/docs"
echo "  • Health:  http://localhost:$PORT/health"
echo "  • Metrics: http://localhost:$PORT/metrics"
echo "========================================"
echo ""

# Start the API server
cd api/src
uvicorn api_v2:app --host 0.0.0.0 --port $PORT --reload
