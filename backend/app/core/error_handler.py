"""Centralized error handling middleware for FastAPI."""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all AppException subclasses uniformly."""
    logger.warning(f"AppException: {exc.status_code} - {exc.message} [{request.method} {request.url.path}]")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
