"""
UdyamSetu AI — FastAPI Application Entrypoint
SIH26130: Intelligent Industrial Approval & Compliance Platform
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.industry import router as industry_router
from app.api.officer import router as officer_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware

logger = logging.getLogger("udyamsetu.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for async startup and shutdown events."""
    setup_logging()
    logger.info(f"Initializing {settings.PROJECT_NAME} [{settings.ENVIRONMENT}]...")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


def create_application() -> FastAPI:
    """Factory function to build and configure the FastAPI app."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=f"{settings.TAGLINE} ({settings.PROBLEM_STATEMENT})",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Attach request tracing & access logging middleware
    app.add_middleware(RequestContextMiddleware)

    # Register central error handling
    register_exception_handlers(app)

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API Routers
    app.include_router(health_router)
    app.include_router(auth_router, prefix=settings.API_V1_STR)
    app.include_router(industry_router, prefix=settings.API_V1_STR)
    app.include_router(officer_router, prefix=settings.API_V1_STR)

    @app.get("/", tags=["Root"])
    async def root() -> JSONResponse:
        return JSONResponse(
            content={
                "name": settings.PROJECT_NAME,
                "tagline": settings.TAGLINE,
                "problem_statement": settings.PROBLEM_STATEMENT,
                "version": "1.0.0",
                "status": "operational",
                "environment": settings.ENVIRONMENT,
                "docs": "/docs",
                "api_v1": settings.API_V1_STR,
            }
        )

    return app


app = create_application()
