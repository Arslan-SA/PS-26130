"""
System health, liveness, and readiness probe endpoints.
Critical for Kubernetes, Docker container orchestration, and uptime monitoring.
"""

from datetime import datetime, timezone
import os
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("", summary="General Health Status")
async def health_check() -> Dict[str, Any]:
    """Returns general service health information."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/live", summary="Kubernetes/Container Liveness Probe")
async def liveness_probe() -> Dict[str, str]:
    """
    Liveness probe: verifies that the web service loop is alive.
    Always returns 200 if the process can serve HTTP requests.
    """
    return {"status": "alive"}


@router.get("/ready", summary="Kubernetes/Container Readiness Probe")
async def readiness_probe(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Readiness probe: verifies connectivity to backend dependencies (Database, Storage).
    Returns 200 when ready to accept traffic, or 503 if a critical dependency is down.
    """
    checks: Dict[str, str] = {}
    is_ready = True

    # 1. Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        is_ready = False

    # 2. Local storage directory accessibility check
    try:
        os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
        checks["storage"] = "healthy"
    except Exception as e:
        checks["storage"] = f"unhealthy: {str(e)}"
        is_ready = False

    # 3. AI provider configuration status
    checks["ai_engine"] = f"configured ({settings.AI_PROVIDER})"
    checks["ocr_engine"] = f"configured ({settings.OCR_ENGINE})"

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
