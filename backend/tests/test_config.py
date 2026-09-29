"""
Unit tests for configuration loading and validation.
"""

from app.core.config import Settings, get_settings


def test_settings_default_values():
    """Verify default system settings are populated and correctly typed."""
    s = get_settings()
    assert s.PROJECT_NAME == "UdyamSetu AI"
    assert s.PROBLEM_STATEMENT == "SIH26130"
    assert s.ALGORITHM == "HS256"
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES > 0
    assert len(s.BACKEND_CORS_ORIGINS) >= 1
    assert s.DATABASE_URL.startswith("sqlite") or s.DATABASE_URL.startswith("postgresql")


def test_cors_string_parsing():
    """Verify that comma-delimited CORS string is parsed into list."""
    s = Settings(BACKEND_CORS_ORIGINS="http://example.com, https://app.udyamsetu.gov.in")
    assert "http://example.com" in s.BACKEND_CORS_ORIGINS
    assert "https://app.udyamsetu.gov.in" in s.BACKEND_CORS_ORIGINS
