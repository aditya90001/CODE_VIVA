"""
JSON Knowledge Base Ingestion Service
--------------------------------------
Dynamically discovers, parses, and indexes all JSON knowledge base files 
in the `knowledge_base/` directory into an in-memory SQLite FTS5 index.

Supports:
  - rag_knowledge_base_30_qa.json (RAG Q&As)
  - python_interview_rag_qa.json (Python Q&As)
  - Any future concept-wise JSON file added to knowledge_base/*.json
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_fts_connection: sqlite3.Connection | None = None
_fts_lock = Lock()


def _get_fts_connection() -> sqlite3.Connection:
    global _fts_connection
    if _fts_connection is None:
        with _fts_lock:
            if _fts_connection is None:
                connection = sqlite3.connect(":memory:", check_same_thread=False)
                try:
                    connection.execute(
                        """
                        CREATE VIRTUAL TABLE json_question_bank USING fts5(
                            question,
                            answer,
                            topic,
                            domain UNINDEXED,
                            difficulty UNINDEXED,
                            evaluation_points UNINDEXED
                        )
                        """
                    )
                except sqlite3.OperationalError as exc:
                    connection.close()
                    raise RuntimeError(
                        "SQLite FTS5 is required for the JSON question bank"
                    ) from exc
                _fts_connection = connection
    return _fts_connection


def _infer_difficulty_rag(topic: str) -> str:
    easy = {"RAG Fundamentals"}
    medium = {"Chunking Strategies", "Embeddings & Vector Databases", "Retrieval Strategies"}
    if topic in easy:
        return "easy"
    if topic in medium:
        return "medium"
    return "hard"


def _infer_difficulty_python(question_id: int) -> str:
    if question_id <= 15:
        return "easy"
    if question_id <= 35:
        return "medium"
    return "hard"


def _parse_generic_json_kb(filepath: Path) -> list[dict[str, Any]]:
    """Parse any JSON file in knowledge_base directory into unified entry schema."""
    try:
        with open(filepath, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as exc:
        logger.error("json_kb: failed to read %s -- %s", filepath.name, exc)
        return []

    if isinstance(raw, dict):
        items = raw.get("items")
        dataset_name = raw.get("dataset_name")
    else:
        items = raw
        dataset_name = None

    if not isinstance(items, list):
        logger.warning("json_kb: expected a list or an object containing items in %s", filepath.name)
        return []

    fname = filepath.name.lower()
    domain_source = str(dataset_name or filepath.stem).lower()
    default_domain = re.sub(r"[^a-z0-9]+", "_", domain_source).strip("_")
    default_domain = re.sub(r"_(interview_)?(knowledge_base|qa)$", "", default_domain)

    entries = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        question = (item.get("question") or item.get("q") or "").strip()
        answer = (item.get("expected_answer") or item.get("answer") or item.get("a") or "").strip()
        topic = (item.get("topic") or item.get("concept") or item.get("category") or default_domain).strip()
        eval_points = item.get("evaluation_points") or item.get("eval_points") or item.get("key_points") or []
        interview_tip = (item.get("interview_tip") or "").strip()
        example = (item.get("example") or "").strip()
        explicit_diff = (item.get("difficulty") or "").strip().lower()

        if not question:
            continue

        # Infer domain
        if "rag" in fname:
            domain = "rag"
        elif "python" in fname:
            domain = "python"
        elif "machine_learning" in default_domain or default_domain == "ml":
            domain = "machine_learning"
        else:
            domain = default_domain

        # Infer difficulty
        if explicit_diff in ("easy", "medium", "hard"):
            difficulty = explicit_diff
        elif domain == "rag":
            difficulty = _infer_difficulty_rag(topic)
        elif domain == "python":
            item_id = item.get("id", idx)
            difficulty = _infer_difficulty_python(item_id if isinstance(item_id, int) else idx)
        else:
            if idx % 3 == 1:
                difficulty = "easy"
            elif idx % 3 == 2:
                difficulty = "medium"
            else:
                difficulty = "hard"

        doc_text = f"Q: {question}\nA: {answer}"
        if eval_points:
            doc_text += f"\nKey points: {', '.join(eval_points)}"
        if example:
            doc_text += f"\nExample: {example}"
        if interview_tip:
            doc_text += f"\nTip: {interview_tip}"

        entries.append({
            "question": question,
            "answer": answer,
            "topic": topic,
            "domain": domain,
            "difficulty": difficulty,
            "doc_text": doc_text,
            "evaluation_points": eval_points if isinstance(eval_points, list) else [],
        })
    return entries


def _index_entries(entries: list[dict[str, Any]]) -> int:
    connection = _get_fts_connection()
    with _fts_lock:
        with connection:
            connection.execute("DELETE FROM json_question_bank")
            connection.executemany(
                """
                INSERT INTO json_question_bank
                    (question, answer, topic, domain, difficulty, evaluation_points)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        entry["question"],
                        entry["answer"][:500],
                        entry["topic"],
                        entry["domain"],
                        entry["difficulty"],
                        json.dumps(entry["evaluation_points"]),
                    )
                    for entry in entries
                ],
            )
    logger.info("json_kb: indexed %d entries into SQLite FTS5", len(entries))
    return len(entries)


def ingest_json_knowledge_base(knowledge_base_dir: str, persist_dir: str = "") -> dict[str, Any]:
    """Parse JSON knowledge-base files and rebuild the in-memory SQLite FTS5 index."""
    kb_path = Path(knowledge_base_dir)
    summary: dict[str, int] = {}
    all_entries: list[dict] = []

    if not kb_path.exists():
        logger.warning("json_kb: directory not found -- %s", kb_path)
        _index_entries([])
        return {"total_indexed": 0}

    json_files = sorted(list(kb_path.glob("*.json")))
    if not json_files:
        logger.info("json_kb: no .json files found in %s", kb_path)
        _index_entries([])
        return {"total_indexed": 0}

    for filepath in json_files:
        entries = _parse_generic_json_kb(filepath)
        if entries:
            file_domain = entries[0]["domain"]
            summary[filepath.name] = len(entries)
            all_entries.extend(entries)
            logger.info("json_kb: parsed %d entries from %s (domain: %s)", len(entries), filepath.name, file_domain)

    total = _index_entries(all_entries)
    summary["total_indexed"] = total
    return summary


def retrieve_json_questions(
    concept: str,
    difficulty: str,
    persist_dir: str,
    exclude_questions: list[str] | None = None,
    n: int = 5,
    topic: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve matching questions from SQLite FTS5 for a concept and difficulty."""
    if n <= 0:
        return []

    connection = _get_fts_connection()
    exclude = set(exclude_questions or [])
    search_terms = re.findall(r"[^\W_]+", (topic or concept).replace("_", " "), flags=re.UNICODE)
    search_query = " OR ".join(f'"{term}"' for term in search_terms)
    domain = "machine_learning" if concept == "ml" else concept
    filters = ["domain = ?", "difficulty = ?"]
    parameters: list[Any] = [domain, difficulty]
    if topic:
        filters.append("topic = ?")
        parameters.append(topic)
    if search_query:
        filters.insert(0, "json_question_bank MATCH ?")
        parameters.insert(0, search_query)
    order = (
        "bm25(json_question_bank, 5.0, 1.0, 2.0, 0.0, 0.0, 0.0)"
        if search_query
        else "rowid"
    )
    parameters.append(max(n + len(exclude) + 10, 0))
    query = f"""
        SELECT question, answer, topic, domain, difficulty, evaluation_points
        FROM json_question_bank
        WHERE {" AND ".join(filters)}
        ORDER BY {order}
        LIMIT ?
    """

    with _fts_lock:
        rows = connection.execute(query, parameters).fetchall()

    questions: list[dict[str, Any]] = []
    for question, answer, result_topic, result_domain, result_difficulty, points in rows:
        if question and question not in exclude:
            questions.append(
                {
                    "question": question,
                    "answer": answer,
                    "topic": result_topic,
                    "domain": result_domain,
                    "difficulty": result_difficulty,
                    "evaluation_points": json.loads(points),
                }
            )
        if len(questions) >= n:
            break
    return questions


def get_json_kb_stats(persist_dir: str) -> dict[str, Any]:
    """Return stats about the in-memory SQLite FTS5 question index."""
    connection = _get_fts_connection()
    with _fts_lock:
        total = connection.execute(
            "SELECT COUNT(*) FROM json_question_bank"
        ).fetchone()[0]
    return {"available": total > 0, "total": total, "index": "SQLite FTS5"}


def is_json_kb_ready(persist_dir: str) -> bool:
    """Return True if the JSON knowledge base has been indexed."""
    stats = get_json_kb_stats(persist_dir)
    return stats.get("available", False) and stats.get("total", 0) > 0
