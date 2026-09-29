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

logger = logging.getLogger("udyamsetu.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for async startup and shutdown events."""
    logger.info("Initializing UdyamSetu AI API Core...")
    yield
    logger.info("Shutting down UdyamSetu AI API Core...")


def create_application() -> FastAPI:
    """Factory function to build and configure the FastAPI app."""
    app = FastAPI(
        title="UdyamSetu AI",
        description="Unified Industrial Approval, Compliance & Subsidy Management Platform (SIH26130)",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["Root"])
    async def root() -> JSONResponse:
        return JSONResponse(
            content={
                "name": "UdyamSetu AI",
                "tagline": "Intelligent Industrial Approval & Compliance Platform",
                "problem_statement": "SIH26130",
                "version": "1.0.0",
                "status": "operational",
                "docs": "/docs",
                "api_v1": "/api/v1",
            }
        )

    return app


app = create_application()
