#!/usr/bin/env bash
set -e

echo "=== Starting UdyamSetu AI Development Services ==="

# Check Python environment
if [ -d "backend/.venv" ]; then
    echo "Activating virtualenv..."
    source backend/.venv/bin/activate
fi

# Run backend in background or info
echo "1. Backend: FastAPI running on http://127.0.0.1:8000"
echo "2. Frontend: Next.js running on http://127.0.0.1:3000"
echo "Run 'cd backend && uvicorn app.main:app --reload' and 'cd frontend && npm run dev'"
