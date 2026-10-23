FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MALLOC_ARENA_MAX=2 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    HF_HOME=/var/data/huggingface \
    CHROMA_PERSIST_DIR=/var/data/chroma

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /var/data/huggingface /var/data/chroma \
    && chown -R app:app /app /var/data

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir --no-compile \
    -r /app/backend/requirements.txt

COPY --chown=app:app backend /app/backend
COPY --chown=app:app knowledge_base /app/knowledge_base

USER app

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
