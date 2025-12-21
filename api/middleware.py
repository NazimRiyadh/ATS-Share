"""
FastAPI middleware for logging, CORS, and error handling.
"""

import time
import logging
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from api.models import ErrorResponse, ErrorDetail
from src.logging_config import get_logger

logger = get_logger(__name__)


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(f"➡️ {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"⬅️ {request.method} {request.url.path} "
                f"- {response.status_code} ({process_time:.2f}s)"
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"❌ {request.method} {request.url.path} "
                f"- Error: {e} ({process_time:.2f}s)"
            )
            raise


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {"path": request.url.path}
                }
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(exc)
                }
            }
        )
