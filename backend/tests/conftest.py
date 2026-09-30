"""
Pytest global configuration and fixtures.
Ensures the test suite runs with an isolated in-memory SQLite database,
preventing network latency and destructive drops against production/staging databases.
"""

import os

# Guarantee isolated in-memory SQLite database for all test runs
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
