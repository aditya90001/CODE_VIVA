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
    """Auto-ingest JSON knowledge base on startup if not already indexed."""
    from backend.app.services.json_kb_ingestion_service import (
        ingest_json_knowledge_base,
        is_json_kb_ready,
    )

    if not is_json_kb_ready(settings.chroma_persist_dir):
        logger.info("startup: JSON KB not indexed — ingesting now...")
        summary = ingest_json_knowledge_base(
            knowledge_base_dir="./knowledge_base",
            persist_dir=settings.chroma_persist_dir,
        )
        logger.info("startup: JSON KB ingestion done — %s", summary)
    else:
        from backend.app.services.json_kb_ingestion_service import get_json_kb_stats
        stats = get_json_kb_stats(settings.chroma_persist_dir)
        logger.info("startup: JSON KB already indexed (%d entries)", stats.get("total", 0))

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

