"""
FastAPI middleware for CORS, request IDs, and structured logging.
"""

import time
import uuid

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


def setup_middleware(app: FastAPI) -> None:
    """Attach all middleware to the FastAPI app."""

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request ID + Logging ─────────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Injects a unique request ID and logs request/response metadata."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        # Bind request context for structured logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        logger.info("request_started")

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response


def configure_logging() -> None:
    """Configure structlog for JSON or console output."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.log_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    log_level_map = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            log_level_map.get(settings.log_level.lower(), 20)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
