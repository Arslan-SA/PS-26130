#!/usr/bin/env bash
set -e

echo "=== Running Local CI Quality Checks ==="

echo "1. Checking environment template..."
python3 scripts/verify_env.py

echo "2. Running Backend Pytest Test Suite..."
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests

echo "3. Testing Frontend Next.js Build..."
(cd frontend && npm run build)

echo "=== All CI Checks Passed Successfully! ==="
