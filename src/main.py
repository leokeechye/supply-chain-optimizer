"""Supply Chain Optimizer - Main Application Entry Point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api.router import router as api_router
from src.config import get_settings
from src.data import db as data_db

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events."""
    logger.info(
        "Starting Supply Chain Optimizer",
        app_name=settings.app_name,
        environment=settings.app_env,
    )

    # SQLite schema + first-boot seed from src/data/csv/*.csv
    data_db.init_db()
    logger.info("Database ready", **data_db.status())

    yield
    
    # Cleanup
    logger.info("Shutting down Supply Chain Optimizer")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Supply Chain Optimizer",
        description=(
            "An AI-driven autonomous agentic workflow for global logistics, "
            "demand forecasting, and inventory optimization using multi-agent orchestration."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Mount static UI (rendered-markdown orchestrator view)
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/ui", StaticFiles(directory=str(static_dir)), name="ui")

        @app.get("/orchestrate", include_in_schema=False)
        async def orchestrate_ui_shortcut() -> RedirectResponse:
            return RedirectResponse(url="/ui/orchestrate.html")

    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "environment": settings.app_env,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
