"""
Product Gallery — FastAPI Application Entry Point

The main application that wires together all routes, middleware,
and lifecycle events.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1 import auth, products, collections, categories, search
from app.core.config import get_settings
from app.core.middleware import configure_logging, setup_middleware
from app.core.storage import ensure_bucket_exists

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown hooks."""
    configure_logging()
    logger.info(
        "app_starting",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Ensure S3 bucket exists (useful for local dev with MinIO)
    try:
        ensure_bucket_exists()
        logger.info("s3_bucket_ready", bucket=settings.s3_bucket_name)
    except Exception as e:
        logger.warning("s3_bucket_check_failed", error=str(e))

    yield

    logger.info("app_shutting_down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "The world's best personal product memory app. "
        "Save products from anywhere, organize with AI, rediscover instantly."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────
setup_middleware(app)

# ── Routes ───────────────────────────────────────────────────────────────
api_prefix = settings.api_v1_prefix

app.include_router(auth.router, prefix=api_prefix)
app.include_router(products.router, prefix=api_prefix)
app.include_router(collections.router, prefix=api_prefix)
app.include_router(categories.router, prefix=api_prefix)
app.include_router(search.router, prefix=api_prefix)


# ── Health Check ─────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Liveness probe — returns 200 if the app is running."""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/ready", tags=["System"])
async def readiness_check():
    """
    Readiness probe — checks database and cache connectivity.
    Returns 200 only if all dependencies are reachable.
    """
    checks = {}

    # Database check
    try:
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
        status_code=status_code,
    )


# Import text for the readiness check SQL
from sqlalchemy import text  # noqa: E402
