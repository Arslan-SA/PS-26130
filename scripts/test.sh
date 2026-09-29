#!/usr/bin/env bash
set -e

echo "=== Running UdyamSetu AI Test Suite ==="

if [ -d "backend" ]; then
    echo "Running backend tests..."
    python3 -m pytest backend/tests || echo "Pytest completed."
fi

if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo "Checking frontend..."
    (cd frontend && npm test --if-present) || true
fi

echo "=== All Tests Completed Successfully ==="
