"""Brain Tumor AI Diagnostic Platform — FastAPI application entry point."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app as prometheus_app

from backend.api.routes.scan import router as scan_router
from backend.database.db import shutdown as db_shutdown, warmup as db_warmup
from backend.middleware.logging_middleware import LoggingMiddleware
from backend.services.s3_service import warmup as s3_warmup
from backend.utils.logger import get_logger, setup_logging

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

setup_logging()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Allowed origins (comma-separated env var, with sensible defaults)
# ---------------------------------------------------------------------------

_ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")


# ---------------------------------------------------------------------------
# Lifespan — run startup / shutdown logic
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Warm up DB, S3, and AI models before serving; tear down on shutdown."""
    logger.info("app_startup_begin")

    # Database
    await db_warmup()

    # S3 (non-fatal if unavailable)
    try:
        await s3_warmup()
    except Exception:
        logger.warning("s3_warmup_failed — continuing without S3 pre-check")

    # AI models (load synchronously — they are needed before first request)
    try:
        from backend.ai_models.ensemble_model import EnsembleModel

        ensemble = EnsembleModel()
        ensemble.load_all()
        app.state.ensemble = ensemble
        logger.info("ai_models_loaded")
    except Exception:
        logger.exception("ai_model_load_failed — predictions will return 503")
        app.state.ensemble = None

    logger.info("app_startup_complete")

    yield

    logger.info("app_shutdown_begin")
    await db_shutdown()
    logger.info("app_shutdown_complete")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Brain Tumor AI Diagnostic Platform",
    version="1.0.0",
    description="AI-powered brain tumor detection and radiology report generation.",
    lifespan=lifespan,
)

# -- Middleware (order matters: outermost first) --
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

# -- Routers --
app.include_router(scan_router)

# -- Prometheus metrics endpoint --
metrics_app = prometheus_app()
app.mount("/metrics", metrics_app)


# -- Health check --
@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
