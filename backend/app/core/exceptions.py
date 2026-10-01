"""
Centralized API Exception Hierarchy and Global Exception Handlers.
Implements standardized RFC 7807-compliant structured problem details.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("udyamsetu.exceptions")


class AppException(Exception):
    """Base class for all domain-specific application exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppException):
    def __init__(self, message: str = "Requested resource not found", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class AuthenticationError(AppException):
    def __init__(self, message: str = "Invalid credentials or token expired", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="UNAUTHENTICATED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ValidationError(AppException):
    def __init__(self, message: str = "Invalid input data", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_FAILED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict detected", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class BusinessRuleViolationError(AppException):
    def __init__(self, message: str = "Business rule constraint violated", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="BUSINESS_RULE_VIOLATION",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Optional[Any] = None,
    request_id: Optional[str] = None,
) -> JSONResponse:
    """Format standard API error payload."""
    payload: Dict[str, Any] = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "status": status_code,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    if request_id:
        payload["error"]["request_id"] = request_id

    return JSONResponse(status_code=status_code, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers onto the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning(f"[{exc.code}] {exc.message} (Path: {request.url.path})")
        return build_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.info(f"Request validation error on {request.url.path}: {exc.errors()}")
        return build_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Request body or query parameters failed validation",
            details=exc.errors(),
            request_id=request_id,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return build_error_response(
            status_code=exc.status_code,
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            request_id=request_id,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception(f"Unhandled server error on {request.url.path}: {exc}")
        return build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred. Please contact system support.",
            request_id=request_id,
        )
