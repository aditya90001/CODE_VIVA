import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import router as api_router
from backend.app.config import settings
from backend.app.db import Base, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the lightweight SQLite FTS5 question index from JSON files."""
    from backend.app.services.json_kb_ingestion_service import (
        ingest_json_knowledge_base,
    )

    summary = ingest_json_knowledge_base(
        knowledge_base_dir="./knowledge_base",
    )
    logger.info("startup: SQLite FTS5 JSON KB indexing done — %s", summary)

    yield  # server runs here


Base.metadata.create_all(bind=engine)

allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app = FastAPI(title="Adaptive AI GitHub Project Evaluator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
