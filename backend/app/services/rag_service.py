"""
RAG Service — indexes repository content into ChromaDB and retrieves
context chunks for grounded, specific question generation.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from backend.app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ChromaDB helpers (optional import — gracefully disabled if not installed)
# ---------------------------------------------------------------------------
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    CHROMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    CHROMA_AVAILABLE = False
    logger.warning("chromadb not installed — RAG context retrieval disabled. Run: pip install chromadb")


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------
def _chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
    """Split *text* into overlapping chunks of *max_chars* characters."""
    if not text or not text.strip():
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# RAG collection ID — stable per repo
# ---------------------------------------------------------------------------
def _collection_id(repo_full_name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", repo_full_name)
    if len(safe) > 50:
        safe = safe[:50] + "_" + hashlib.md5(repo_full_name.encode()).hexdigest()[:8]
    # ChromaDB requires collection names to start with a letter
    if not safe[0].isalpha():
        safe = "r_" + safe
    return safe


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class RAGService:
    """
    Indexes repository content (README + code files) into ChromaDB
    and exposes a ``retrieve`` method to fetch the most relevant chunks
    for a given topic/question.

    When ChromaDB is not available or disabled via settings, ``retrieve``
    returns an empty list so callers fall back gracefully.
    """

    _client: Any = None  # shared ChromaDB client (lazy init)

    @classmethod
    def _get_client(cls, persist_dir: str) -> Any:
        if not settings.chroma_enabled or not CHROMA_AVAILABLE:
            return None
        if cls._client is None:
            cls._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return cls._client

    @classmethod
    def index_repository(
        cls,
        profile: dict[str, Any],
        persist_dir: str = "./.chroma",
    ) -> bool:
        """
        Index the repository's README and code files into ChromaDB.

        *profile* must contain the keys produced by ``github_analyzer``:
        - ``readme_summary``  — full README text
        - ``code_files``      — list of ``{"path": str, "content": str}``
        - ``full_name``       — owner/repo (used as collection ID)

        Returns True if indexing succeeded, False otherwise.
        """
        client = cls._get_client(persist_dir)
        if client is None:
            return False

        repo_name: str = profile.get("full_name") or profile.get("repo") or "unknown_repo"
        collection_name = _collection_id(repo_name)

        try:
            # Delete stale collection so we always re-index fresh content
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass

            collection = client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )

            documents: list[str] = []
            metadatas: list[dict] = []
            ids: list[str] = []

            # --- README ---
            readme = profile.get("readme_summary") or ""
            if readme.strip():
                for i, chunk in enumerate(_chunk_text(readme)):
                    documents.append(chunk)
                    metadatas.append({"source": "README", "path": "README.md"})
                    ids.append(f"readme_{i}")

            # --- Code files ---
            code_files: list[dict] = profile.get("code_files") or []
            for file_info in code_files:
                path: str = file_info.get("path", "unknown")
                content: str = file_info.get("content") or ""
                if not content.strip():
                    continue
                file_hash = hashlib.md5(path.encode()).hexdigest()[:6]
                for i, chunk in enumerate(_chunk_text(content)):
                    documents.append(chunk)
                    metadatas.append({"source": "code", "path": path})
                    ids.append(f"file_{file_hash}_{i}")

            if not documents:
                logger.warning("RAGService: no documents to index for %s", repo_name)
                return False

            # ChromaDB add in batches of 500
            batch_size = 500
            for start in range(0, len(documents), batch_size):
                collection.add(
                    documents=documents[start : start + batch_size],
                    metadatas=metadatas[start : start + batch_size],
                    ids=ids[start : start + batch_size],
                )

            logger.info(
                "RAGService: indexed %d chunks for %s into collection '%s'",
                len(documents),
                repo_name,
                collection_name,
            )
            return True

        except Exception as exc:
            logger.error("RAGService: indexing failed for %s — %s", repo_name, exc)
            return False

    @classmethod
    def retrieve(
        cls,
        query: str,
        repo_full_name: str,
        persist_dir: str = "./.chroma",
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the top-*n_results* most relevant chunks for *query*
        from the collection indexed for *repo_full_name*.

        Returns a list of dicts: ``[{"text": str, "source": str, "path": str}]``
        """
        client = cls._get_client(persist_dir)
        if client is None:
            return []

        collection_name = _collection_id(repo_full_name)
        try:
            collection = client.get_collection(collection_name)
        except Exception:
            logger.warning("RAGService: collection '%s' not found — skipping retrieval", collection_name)
            return []

        try:
            results = collection.query(
                query_texts=[query],
                n_results=min(n_results, collection.count()),
                include=["documents", "metadatas"],
            )
            chunks: list[dict[str, Any]] = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            for doc, meta in zip(docs, metas):
                chunks.append(
                    {
                        "text": doc,
                        "source": meta.get("source", ""),
                        "path": meta.get("path", ""),
                    }
                )
            return chunks
        except Exception as exc:
            logger.error("RAGService: retrieval failed — %s", exc)
            return []

    @classmethod
    def is_indexed(cls, repo_full_name: str, persist_dir: str = "./.chroma") -> bool:
        """Return True if the collection for *repo_full_name* already exists."""
        client = cls._get_client(persist_dir)
        if client is None:
            return False
        collection_name = _collection_id(repo_full_name)
        try:
            col = client.get_collection(collection_name)
            return col.count() > 0
        except Exception:
            return False
