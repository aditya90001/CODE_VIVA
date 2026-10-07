"""
PDF Ingestion Service — reads topic-wise question PDFs from the knowledge_base/
folder, extracts questions, and indexes them into ChromaDB.

Each PDF becomes a searchable question bank entry. When a student's concepts
are detected, we query this bank to find matching concept-level questions.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Difficulty markers the interviewer can embed in PDFs
_DIFFICULTY_MARKERS = {
    "easy": ["[easy]", "[beginner]", "[basic]", "[level 1]", "easy:", "beginner:"],
    "medium": ["[medium]", "[intermediate]", "[level 2]", "medium:", "intermediate:"],
    "hard": ["[hard]", "[advanced]", "[expert]", "[level 3]", "hard:", "advanced:"],
}

# Supported question indicator patterns
_QUESTION_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:\d+[\.\)]\s+|Q\d*[\.\):\s]+|[-•]\s+)(.+?)(?=\n\s*(?:\d+[\.\)]|Q\d*[\.\):\s]|[-•]|\Z))",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------
def _extract_pdf_text(pdf_path: Path) -> str:
    """Extract all text from a PDF file using pypdf."""
    try:
        import pypdf  # type: ignore

        reader = pypdf.PdfReader(str(pdf_path))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
        return "\n".join(pages_text)
    except ImportError:
        logger.error("pypdf not installed. Run: pip install pypdf")
        return ""
    except Exception as exc:
        logger.error("Failed to read PDF %s: %s", pdf_path, exc)
        return ""


# ---------------------------------------------------------------------------
# Question extraction from raw text
# ---------------------------------------------------------------------------
def _detect_difficulty(text: str, current_block_difficulty: str) -> str:
    """Check if a line sets a new difficulty level."""
    lower = text.lower().strip()
    for level, markers in _DIFFICULTY_MARKERS.items():
        if any(lower.startswith(m) or lower == m for m in markers):
            return level
    return current_block_difficulty


def _extract_questions(text: str, topic: str) -> list[dict[str, Any]]:
    """
    Parse the PDF text and extract individual questions with difficulty.

    Supports formats:
      [Easy]
      1. What is a decorator?
      2. How does @staticmethod work?

      [Medium]
      3. Write a decorator that logs execution time.
    """
    questions: list[dict[str, Any]] = []
    current_difficulty = "easy"
    lines = text.split("\n")

    current_question_lines: list[str] = []
    question_number = 0

    def _flush():
        nonlocal current_question_lines, question_number
        q_text = " ".join(current_question_lines).strip()
        q_text = re.sub(r"\s+", " ", q_text)
        if len(q_text) > 15:  # skip tiny fragments
            question_number += 1
            questions.append(
                {
                    "topic": topic,
                    "difficulty": current_difficulty,
                    "question": q_text,
                    "question_number": question_number,
                }
            )
        current_question_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for difficulty marker line
        new_diff = _detect_difficulty(stripped, current_difficulty)
        if new_diff != current_difficulty:
            _flush()
            current_difficulty = new_diff
            continue

        # Check if this line starts a new numbered question
        is_new_question = bool(
            re.match(r"^\d+[\.\)]\s+", stripped)
            or re.match(r"^Q\d*[\.\):\s]", stripped, re.IGNORECASE)
            or re.match(r"^[-•]\s+.{10,}", stripped)
        )

        if is_new_question and current_question_lines:
            _flush()

        # Clean the question prefix (remove "1. " or "Q1. " or "- ")
        clean = re.sub(r"^\d+[\.\)]\s+", "", stripped)
        clean = re.sub(r"^Q\d*[\.\):\s]+", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"^[-•]\s+", "", clean)

        if clean:
            current_question_lines.append(clean)

    _flush()  # flush last question
    return questions


# ---------------------------------------------------------------------------
# ChromaDB indexing
# ---------------------------------------------------------------------------
def _get_chroma_client(persist_dir: str) -> Any:
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        return chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    except ImportError:
        logger.error("chromadb not installed")
        return None


QUESTION_BANK_COLLECTION = "question_bank"


def _index_questions(questions: list[dict[str, Any]], persist_dir: str) -> int:
    """Add questions to the question_bank ChromaDB collection. Returns count indexed."""
    if not questions:
        return 0

    client = _get_chroma_client(persist_dir)
    if client is None:
        return 0

    try:
        collection = client.get_or_create_collection(
            name=QUESTION_BANK_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

        docs, metas, ids = [], [], []
        for q in questions:
            q_id = hashlib.md5(
                f"{q['topic']}::{q['question']}".encode()
            ).hexdigest()
            # Avoid duplicates
            docs.append(q["question"])
            metas.append(
                {
                    "topic": q["topic"],
                    "difficulty": q["difficulty"],
                    "question_number": str(q.get("question_number", 0)),
                }
            )
            ids.append(q_id)

        # Upsert in batches of 500
        batch = 500
        for start in range(0, len(docs), batch):
            collection.upsert(
                documents=docs[start : start + batch],
                metadatas=metas[start : start + batch],
                ids=ids[start : start + batch],
            )

        logger.info("Indexed %d questions from question bank", len(docs))
        return len(docs)
    except Exception as exc:
        logger.error("Failed to index questions: %s", exc)
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ingest_knowledge_base(knowledge_base_dir: str, persist_dir: str) -> dict[str, Any]:
    """
    Scan *knowledge_base_dir* for PDF files, extract questions,
    and index them into ChromaDB.

    Returns a summary dict: {topic: question_count}
    """
    kb_path = Path(knowledge_base_dir)
    if not kb_path.exists():
        logger.warning("knowledge_base directory not found: %s", knowledge_base_dir)
        return {}

    pdf_files = list(kb_path.glob("*.pdf"))
    if not pdf_files:
        logger.info("No PDF files found in %s", knowledge_base_dir)
        return {}

    summary: dict[str, int] = {}
    all_questions: list[dict] = []

    for pdf_path in pdf_files:
        # Derive topic from filename: "python_decorators.pdf" → "python_decorators"
        topic = pdf_path.stem.lower().replace(" ", "_").replace("-", "_")
        logger.info("Ingesting PDF: %s → topic: %s", pdf_path.name, topic)

        text = _extract_pdf_text(pdf_path)
        if not text.strip():
            logger.warning("Empty text extracted from %s", pdf_path.name)
            continue

        questions = _extract_questions(text, topic)
        logger.info("  Extracted %d questions from %s", len(questions), pdf_path.name)
        summary[topic] = len(questions)
        all_questions.extend(questions)

    total = _index_questions(all_questions, persist_dir)
    logger.info("Total indexed into question_bank: %d questions", total)
    return summary


def retrieve_questions_for_concept(
    concept: str,
    difficulty: str,
    persist_dir: str,
    exclude_questions: list[str] | None = None,
    n: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve questions from the question_bank for a given concept + difficulty.

    *concept* should match a topic key (e.g., "python_decorators").
    Returns a list of question dicts: [{question, topic, difficulty}, ...]
    """
    client = _get_chroma_client(persist_dir)
    if client is None:
        return []

    try:
        collection = client.get_collection(QUESTION_BANK_COLLECTION)
    except Exception:
        logger.warning("question_bank collection not found — PDFs not ingested yet")
        return []

    exclude = set(exclude_questions or [])

    # Strategy: query by topic as the search text, filter by difficulty
    try:
        results = collection.query(
            query_texts=[concept.replace("_", " ")],
            n_results=min(n + len(exclude) + 5, max(collection.count(), 1)),
            where={"$and": [{"topic": {"$eq": concept}}, {"difficulty": {"$eq": difficulty}}]},
            include=["documents", "metadatas"],
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        questions = []
        for doc, meta in zip(docs, metas):
            if doc not in exclude:
                questions.append(
                    {
                        "question": doc,
                        "topic": meta.get("topic", concept),
                        "difficulty": meta.get("difficulty", difficulty),
                    }
                )
            if len(questions) >= n:
                break
        return questions
    except Exception as exc:
        logger.error("retrieve_questions_for_concept failed: %s", exc)
        return []


def get_question_bank_stats(persist_dir: str) -> dict[str, Any]:
    """Return stats about what's in the question bank collection."""
    client = _get_chroma_client(persist_dir)
    if client is None:
        return {"available": False}
    try:
        collection = client.get_collection(QUESTION_BANK_COLLECTION)
        count = collection.count()
        return {"available": True, "total_questions": count}
    except Exception:
        return {"available": False, "total_questions": 0}
