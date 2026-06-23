"""
AI Agent Platform – MCP Gateway
================================
FastAPI application that:
  • Serves the REST API consumed by the HTML UI
  • Mounts the FastMCP server at /mcp  (SSE + HTTP transport)
  • Serves the static HTML/JS UI at /
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import create_tables
from .mcp_server import mcp
from .routers import agents_router, tasks_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Agent Platform Gateway…")
    await create_tables()
    logger.info("Database tables ready.")
    yield
    logger.info("Gateway shutting down.")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Agent Platform",
    description=(
        "MCP Gateway that orchestrates AI agents via Temporal workflows "
        "and persists state in PostgreSQL."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API routes
app.include_router(agents_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Mount FastMCP server at /mcp
# ---------------------------------------------------------------------------
# FastMCP 2.x+ exposes http_app() which returns a Starlette ASGI app.
# The default 'http' transport provides the streamable-HTTP MCP endpoint.
# SSE transport is also available: pass transport="sse" for /sse + /messages.
try:
    mcp_asgi = mcp.http_app(path="/")
    app.mount("/mcp", mcp_asgi)
    logger.info("FastMCP server mounted at /mcp")
except Exception as exc:  # noqa: BLE001
    logger.warning("Could not mount FastMCP ASGI app: %s", exc)

# ---------------------------------------------------------------------------
# Serve static UI
# ---------------------------------------------------------------------------
_ui_dir = Path(__file__).parent.parent / "ui"
if _ui_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_ui_dir / "static")), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_ui():
        return FileResponse(str(_ui_dir / "index.html"))

    @app.get("/{path:path}", include_in_schema=False)
    async def catch_all(path: str):
        # Resolve candidate and guard against path-traversal attacks.
        ui_root = _ui_dir.resolve()
        candidate = (ui_root / path).resolve()
        if not str(candidate).startswith(str(ui_root) + "/") and candidate != ui_root:
            # Path escapes the UI directory – serve index for SPA routing.
            return FileResponse(str(_ui_dir / "index.html"))
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_ui_dir / "index.html"))
