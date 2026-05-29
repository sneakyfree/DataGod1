"""DataGod API production entrypoint.

Wraps the api_v2 application with root + health endpoints and mounts it under
/api/v2. Importable both as ``main`` (CWD=api/src, e.g. local/Docker) and as
``api.src.main`` (repo root on path, e.g. pytest with PYTHONPATH=.:api/src).
Exposes ``app`` (alias of ``main_app``) for ``uvicorn api.src.main:app``.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:  # CWD=api/src or api/src on PYTHONPATH
    from api_v2 import app as api_v2_app
    from config import settings

    from db import init_db
except ImportError:  # imported as api.src.main from repo root
    from api.src.api_v2 import app as api_v2_app
    from api.src.config import settings
    from api.src.db import init_db

# Ensure tables exist (idempotent; api_v2 also inits on startup).
try:
    init_db()
except Exception:  # pragma: no cover - DB may be unavailable at import time
    pass

main_app = FastAPI(
    title="DataGod API",
    version="2.0.0",
    description="API for DataGod - Public Records Data Aggregation Platform",
)

main_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v2 sub-application
main_app.mount("/api/v2", api_v2_app)


@main_app.get("/")
async def root():
    return {
        "message": "DataGod API is running",
        "version": "2.0.0",
        "documentation": "/docs",
        "api_v2": "/api/v2",
    }


@main_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "api_version": "2.0.0",
        "message": "DataGod API v2 is operational",
    }


# uvicorn entrypoint alias (api.src.main:app / main:app)
app = main_app
