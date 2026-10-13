"""
JSON Knowledge Base Ingestion Service
--------------------------------------
Dynamically discovers, parses, and indexes all JSON knowledge base files 
in the `knowledge_base/` directory into ChromaDB (`json_question_bank` collection).

Supports:
  - rag_knowledge_base_30_qa.json (RAG Q&As)
  - python_interview_rag_qa.json (Python Q&As)
  - Any future concept-wise JSON file added to knowledge_base/*.json
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

JSON_KB_COLLECTION = "json_question_bank"


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


def _index_entries(entries: list[dict[str, Any]], persist_dir: str) -> int:
    if not entries:
        return 0
    client = _get_chroma_client(persist_dir)
    if client is None:
        return 0
    try:
        collection = client.get_or_create_collection(
            name=JSON_KB_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        docs, metas, ids = [], [], []
        for entry in entries:
            entry_id = hashlib.md5(f"{entry['domain']}::{entry['question']}".encode()).hexdigest()
            docs.append(entry["doc_text"])
            metadata = {
                "question": entry["question"],
                "answer": entry["answer"][:500],
                "topic": entry["topic"],
                "domain": entry["domain"],
                "difficulty": entry["difficulty"],
            }
            if entry["evaluation_points"]:
                metadata["evaluation_points"] = entry["evaluation_points"]
            metas.append(metadata)
            ids.append(entry_id)
        batch = 500
        for start in range(0, len(docs), batch):
            collection.upsert(
                documents=docs[start: start + batch],
                metadatas=metas[start: start + batch],
                ids=ids[start: start + batch],
            )
        logger.info("json_kb: indexed %d entries into '%s'", len(docs), JSON_KB_COLLECTION)
        return len(docs)
    except Exception as exc:
        logger.error("json_kb: indexing failed -- %s", exc)
        return 0


def ingest_json_knowledge_base(knowledge_base_dir: str, persist_dir: str) -> dict[str, Any]:
    """Dynamically scan all JSON files in knowledge_base_dir, parse, and index into ChromaDB."""
    kb_path = Path(knowledge_base_dir)
    summary: dict[str, int] = {}
    all_entries: list[dict] = []

    if not kb_path.exists():
        logger.warning("json_kb: directory not found -- %s", kb_path)
        return {"total_indexed": 0}

    json_files = sorted(list(kb_path.glob("*.json")))
    if not json_files:
        logger.info("json_kb: no .json files found in %s", kb_path)
        return {"total_indexed": 0}

    for filepath in json_files:
        entries = _parse_generic_json_kb(filepath)
        if entries:
            file_domain = entries[0]["domain"]
            summary[filepath.name] = len(entries)
            all_entries.extend(entries)
            logger.info("json_kb: parsed %d entries from %s (domain: %s)", len(entries), filepath.name, file_domain)

    total = _index_entries(all_entries, persist_dir)
    summary["total_indexed"] = total
    return summary


def retrieve_json_questions(
    concept: str,
    difficulty: str,
    persist_dir: str,
    exclude_questions: list[str] | None = None,
    n: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve concept-level questions from json_question_bank via semantic vector search."""
    client = _get_chroma_client(persist_dir)
    if client is None:
        return []
    try:
        collection = client.get_collection(JSON_KB_COLLECTION)
    except Exception:
        logger.warning("json_kb: collection not found -- not ingested yet")
        return []
    exclude = set(exclude_questions or [])
    total = collection.count()
    if total == 0:
        return []

    try:
        # Try semantic search matching concept and difficulty first
        search_term = concept.replace("_", " ")
        domain = "machine_learning" if concept == "ml" else concept
        results = collection.query(
            query_texts=[search_term],
            n_results=min(n + len(exclude) + 10, total),
            include=["documents", "metadatas"],
            where={"domain": domain},
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        questions: list[dict[str, Any]] = []
        for _, meta in zip(docs, metas):
            q_text = meta.get("question", "")
            if q_text and q_text not in exclude:
                questions.append({
                    "question": q_text,
                    "answer": meta.get("answer", ""),
                    "topic": meta.get("topic", concept),
                    "domain": meta.get("domain", concept),
                    "difficulty": meta.get("difficulty", difficulty),
                    "evaluation_points": meta.get("evaluation_points", []),
                })
            if len(questions) >= n:
                break

        return questions
    except Exception as exc:
        logger.error("json_kb: retrieval failed -- %s", exc)
        return []


def get_json_kb_stats(persist_dir: str) -> dict[str, Any]:
    """Return stats about the json_question_bank collection."""
    client = _get_chroma_client(persist_dir)
    if client is None:
        return {"available": False, "total": 0}
    try:
        collection = client.get_collection(JSON_KB_COLLECTION)
        return {"available": True, "total": collection.count(), "collection": JSON_KB_COLLECTION}
    except Exception:
        return {"available": False, "total": 0}


def is_json_kb_ready(persist_dir: str) -> bool:
    """Return True if the JSON knowledge base has been indexed."""
    stats = get_json_kb_stats(persist_dir)
    return stats.get("available", False) and stats.get("total", 0) > 0
